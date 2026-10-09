import threading

from src.agent.context import tenant_names
from src.agent.schemas import BootstrapResult
from src.agent.sql import engine, quote_ident, tenant_password
from src.settings import settings

READ_ROLE = "meelu_agent_read"
USER_ID_FUNCTION = "public.meelu_agent_user_id"
POLICY = "meelu_agent_select"

BLOCKED_TABLES = frozenset(
    {
        "user",
        "access_token",
        "api_keys",
        "agent_plans",
        "agent_tenants",
        "provider_cache",
        "scratchpad",
        "scratchpad_row",
        "alembic_version",
    }
)

CURRENT_TENANT = f"(SELECT {USER_ID_FUNCTION}())"

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


def bootstrap() -> BootstrapResult:
    read = quote_ident(READ_ROLE)
    with engine.begin() as conn:
        _ensure_read_role(conn)
        conn.exec_driver_sql(f"GRANT USAGE ON SCHEMA public TO {read}")
        conn.exec_driver_sql(
            f"CREATE OR REPLACE FUNCTION {USER_ID_FUNCTION}() RETURNS text "
            "LANGUAGE sql STABLE SECURITY DEFINER SET search_path = pg_catalog, public AS "
            "$$ SELECT user_id FROM public.agent_tenants WHERE role_name = session_user $$"
        )
        conn.exec_driver_sql(f"REVOKE ALL ON FUNCTION {USER_ID_FUNCTION}() FROM PUBLIC")
        conn.exec_driver_sql(f"GRANT EXECUTE ON FUNCTION {USER_ID_FUNCTION}() TO {read}")

        tables = [
            r[0]
            for r in conn.exec_driver_sql(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )
        ]
        user_scoped = {
            r[0]
            for r in conn.exec_driver_sql(
                "SELECT table_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND column_name = 'user_id'"
            )
        }
        owned_through: dict[str, list[str]] = {}
        for child, column, parent, parent_column in conn.exec_driver_sql(
            SINGLE_COLUMN_FOREIGN_KEYS
        ):
            if child not in user_scoped and parent in user_scoped:
                owned_through.setdefault(child, []).append(
                    f"EXISTS (SELECT 1 FROM public.{quote_ident(parent)} p "
                    f"WHERE p.{quote_ident(parent_column)} = {quote_ident(column)})"
                )

        granted, secured = [], []
        for table in tables:
            qt = quote_ident(table)
            if table in user_scoped:
                using = f"user_id = {CURRENT_TENANT}"
            elif table in owned_through:
                using = " AND ".join(owned_through[table])
            else:
                using = None
            if table in BLOCKED_TABLES or using is None:
                conn.exec_driver_sql(f"REVOKE ALL ON public.{qt} FROM {read}")
                continue
            conn.exec_driver_sql(f"GRANT SELECT ON public.{qt} TO {read}")
            _secure(conn, table, using)
            granted.append(table)
            secured.append(table)

    return BootstrapResult(granted=granted, rls=secured)


def ensure_user(user_id: str) -> tuple[str, str]:
    role, schema = tenant_names(user_id)
    if user_id in _ensured:
        return role, schema
    with _lock:
        if user_id in _ensured:
            return role, schema
        qr, qs = quote_ident(role), quote_ident(schema)
        attributes = (
            f"LOGIN PASSWORD '{tenant_password(role)}' NOSUPERUSER NOCREATEDB NOCREATEROLE "
            f"NOREPLICATION NOBYPASSRLS INHERIT "
            f"CONNECTION LIMIT {settings.agent_tenant_connections * 2}"
        )
        with engine.begin() as conn:
            _ensure_read_role(conn)
            verb = "ALTER" if _role_exists(conn, role) else "CREATE"
            conn.exec_driver_sql(f"{verb} ROLE {qr} WITH {attributes}")
            conn.exec_driver_sql(f"GRANT {quote_ident(READ_ROLE)} TO {qr}")
            conn.exec_driver_sql(f"GRANT {qr} TO CURRENT_USER")
            conn.exec_driver_sql(f"CREATE SCHEMA IF NOT EXISTS {qs} AUTHORIZATION {qr}")
            conn.exec_driver_sql(f"ALTER SCHEMA {qs} OWNER TO {qr}")
            conn.exec_driver_sql(
                "INSERT INTO public.agent_tenants (role_name, user_id) VALUES (%s, %s) "
                "ON CONFLICT (role_name) DO UPDATE SET user_id = excluded.user_id",
                (role, user_id),
            )
        _ensured.add(user_id)
    return role, schema
