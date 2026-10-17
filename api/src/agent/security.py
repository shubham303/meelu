import shutil
import threading

from src.agent.context import tenant_names
from src.agent.schemas import BootstrapResult
from src.agent.sql import engine, quote_ident, tenant_password
from src.settings import settings

READ_ROLE = "meelu_agent_read"
USER_ID_FUNCTION = "public.meelu_agent_user_id"
SITE_ID_FUNCTION = "public.meelu_agent_site_id"
POLICY = "meelu_agent_select"

READABLE_TABLES = frozenset(
    {
        "content_piece_issues",
        "content_pieces",
        "link_suggestions",
        "notes",
        "pillar_page_suggestions",
        "post_media",
        "profile",
        "reports",
        "seo_keyword_clusters",
        "seo_volume_history",
        "site",
        "site_audit_runs",
        "site_backlinks",
        "site_chunks",
        "site_competitors",
        "site_crawl_jobs",
        "site_issues",
        "site_page_index_status",
        "site_page_issues",
        "site_page_links",
        "site_page_llm_extraction",
        "site_page_renders",
        "site_pages",
        "site_search_daily",
        "site_search_syncs",
        "site_traffic_channels_daily",
        "site_traffic_events_daily",
        "site_traffic_geo_daily",
        "site_traffic_landing_daily",
        "site_traffic_pages_daily",
        "site_traffic_syncs",
        "site_traffic_tech_daily",
        "site_traffic_totals_daily",
        "social_listening_config",
        "social_listening_post",
        "social_listening_query",
        "social_listening_run",
        "social_post",
        "structure_jobs",
    }
)

TENANT_LIMITS = "NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"

CURRENT_TENANT = f"(SELECT {USER_ID_FUNCTION}())"
CURRENT_SITE = f"(SELECT {SITE_ID_FUNCTION}())"

SINGLE_COLUMN_FOREIGN_KEYS = """
SELECT child.relname, child_col.attname, parent.relname, parent_col.attname
  FROM pg_constraint c
  JOIN pg_class child ON child.oid = c.conrelid
  JOIN pg_class parent ON parent.oid = c.confrelid
  JOIN pg_attribute child_col ON child_col.attrelid = c.conrelid AND child_col.attnum = c.conkey[1]
  JOIN pg_attribute parent_col
    ON parent_col.attrelid = c.confrelid AND parent_col.attnum = c.confkey[1]
 WHERE c.contype = 'f'
   AND c.connamespace = 'public'::regnamespace
   AND cardinality(c.conkey) = 1
 ORDER BY 1, 2
"""

_ensured: set[str] = set()
_lock = threading.Lock()


def _role_exists(conn, role: str) -> bool:
    row = conn.exec_driver_sql("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
    return row is not None


def _ensure_read_role(conn) -> None:
    if not _role_exists(conn, READ_ROLE):
        conn.exec_driver_sql(f"CREATE ROLE {quote_ident(READ_ROLE)} NOLOGIN")


def _secure(conn, table: str, using: str) -> None:
    qt = quote_ident(table)
    conn.exec_driver_sql(f"ALTER TABLE public.{qt} ENABLE ROW LEVEL SECURITY")
    conn.exec_driver_sql(f"DROP POLICY IF EXISTS {POLICY} ON public.{qt}")
    conn.exec_driver_sql(f"CREATE POLICY {POLICY} ON public.{qt} FOR SELECT USING ({using})")


def _tables_with_column(conn, column: str) -> set[str]:
    return {
        r[0]
        for r in conn.exec_driver_sql(
            "SELECT table_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND column_name = %s",
            (column,),
        )
    }


def bootstrap() -> BootstrapResult:
    read = quote_ident(READ_ROLE)
    with engine.begin() as conn:
        _ensure_read_role(conn)
        conn.exec_driver_sql(f"GRANT USAGE ON SCHEMA public TO {read}")
        for function, column in ((USER_ID_FUNCTION, "user_id"), (SITE_ID_FUNCTION, "site_id")):
            conn.exec_driver_sql(
                f"CREATE OR REPLACE FUNCTION {function}() RETURNS text "
                "LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS "
                f"$$ SELECT {column} FROM public.agent_tenants WHERE role_name = session_user $$"
            )
            conn.exec_driver_sql(f"REVOKE ALL ON FUNCTION {function}() FROM PUBLIC")
            conn.exec_driver_sql(f"GRANT EXECUTE ON FUNCTION {function}() TO {read}")

        tables = [
            r[0]
            for r in conn.exec_driver_sql(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )
        ]
        user_scoped = _tables_with_column(conn, "user_id")
        site_scoped = _tables_with_column(conn, "site_id")
        owned_through: dict[str, list[str]] = {}
        referenced_by: dict[str, list[str]] = {}
        for child, column, parent, parent_column in conn.exec_driver_sql(
            SINGLE_COLUMN_FOREIGN_KEYS
        ):
            if child not in user_scoped and parent in user_scoped:
                owned_through.setdefault(child, []).append(
                    f"EXISTS (SELECT 1 FROM public.{quote_ident(parent)} p "
                    f"WHERE p.{quote_ident(parent_column)} = "
                    f"public.{quote_ident(child)}.{quote_ident(column)})"
                )
            if parent not in user_scoped and child in user_scoped and child in READABLE_TABLES:
                referenced_by.setdefault(parent, []).append(
                    f"EXISTS (SELECT 1 FROM public.{quote_ident(child)} c "
                    f"WHERE c.{quote_ident(column)} = "
                    f"public.{quote_ident(parent)}.{quote_ident(parent_column)})"
                )

        granted, secured = [], []
        for table in tables:
            qt = quote_ident(table)
            if table == "site":
                using = f"user_id = {CURRENT_TENANT} AND id = {CURRENT_SITE}"
            elif table in user_scoped and table in site_scoped:
                using = f"user_id = {CURRENT_TENANT} AND site_id = {CURRENT_SITE}"
            elif table in user_scoped:
                using = f"user_id = {CURRENT_TENANT}"
            elif table in owned_through:
                using = " AND ".join(owned_through[table])
            elif table in referenced_by:
                using = " OR ".join(referenced_by[table])
            else:
                using = None
            if table not in READABLE_TABLES or using is None:
                conn.exec_driver_sql(f"REVOKE ALL ON public.{qt} FROM {read}")
                continue
            conn.exec_driver_sql(f"GRANT SELECT ON public.{qt} TO {read}")
            _secure(conn, table, using)
            granted.append(table)
            secured.append(table)

    return BootstrapResult(granted=granted, rls=secured)


def ensure_tenant(user_id: str, site_id: str) -> tuple[str, str]:
    role, schema = tenant_names(user_id, site_id)
    if role in _ensured:
        return role, schema
    with _lock:
        if role in _ensured:
            return role, schema
        qr, qs = quote_ident(role), quote_ident(schema)
        login = (
            f"LOGIN PASSWORD '{tenant_password(role)}' INHERIT "
            f"CONNECTION LIMIT {settings.agent_tenant_connections * 2}"
        )
        with engine.begin() as conn:
            _ensure_read_role(conn)
            if _role_exists(conn, role):
                conn.exec_driver_sql(f"ALTER ROLE {qr} WITH {login}")
            else:
                conn.exec_driver_sql(f"CREATE ROLE {qr} WITH {login} {TENANT_LIMITS}")
            conn.exec_driver_sql(
                f"ALTER ROLE {qr} SET temp_file_limit = '{settings.agent_temp_file_limit}'"
            )
            conn.exec_driver_sql(f"GRANT {quote_ident(READ_ROLE)} TO {qr}")
            conn.exec_driver_sql(f"GRANT {qr} TO CURRENT_USER")
            conn.exec_driver_sql(f"CREATE SCHEMA IF NOT EXISTS {qs} AUTHORIZATION {qr}")
            conn.exec_driver_sql(f"ALTER SCHEMA {qs} OWNER TO {qr}")
            conn.exec_driver_sql(
                "INSERT INTO public.agent_tenants (role_name, schema_name, user_id, site_id) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (role_name) DO NOTHING",
                (role, schema, user_id, site_id),
            )
        _ensured.add(role)
    return role, schema


def _drop_role(conn, role: str, schema: str) -> None:
    qr = quote_ident(role)
    if _role_exists(conn, role):
        conn.exec_driver_sql(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE usename = %s", (role,)
        )
        conn.exec_driver_sql(f"DROP SCHEMA IF EXISTS {quote_ident(schema)} CASCADE")
        conn.exec_driver_sql(f"DROP OWNED BY {qr} CASCADE")
        conn.exec_driver_sql(f"DROP ROLE {qr}")
    conn.exec_driver_sql("DELETE FROM public.agent_tenants WHERE role_name = %s", (role,))
    _ensured.discard(role)
    shutil.rmtree(settings.agent_data_dir / "models" / schema, ignore_errors=True)


def drop_tenants(user_id: str) -> None:
    with _lock, engine.begin() as conn:
        rows = conn.exec_driver_sql(
            "SELECT role_name, schema_name FROM public.agent_tenants WHERE user_id = %s",
            (user_id,),
        ).fetchall()
        for role, schema in rows:
            _drop_role(conn, role, schema)


ORPHAN_ROLES = """
SELECT r.rolname FROM pg_roles r
  JOIN pg_auth_members m ON m.member = r.oid
  JOIN pg_roles g ON g.oid = m.roleid AND g.rolname = %s
  JOIN pg_namespace n ON n.nspname = 'ws_' || substr(r.rolname, 7)
 WHERE NOT EXISTS (SELECT 1 FROM public.agent_tenants t WHERE t.role_name = r.rolname)
"""


def drop_orphan_tenants() -> list[str]:
    with _lock, engine.begin() as conn:
        orphans = [r[0] for r in conn.exec_driver_sql(ORPHAN_ROLES, (READ_ROLE,))]
        for role in orphans:
            schema = "ws_" + role.removeprefix("agent_")
            _drop_role(conn, role, schema)
    return orphans
