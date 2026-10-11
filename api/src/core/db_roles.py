import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

from src.agent.security import READ_ROLE
from src.settings import settings

LARGE_OBJECT_WRITERS = (
    "lo_creat(integer)",
    "lo_create(oid)",
    "lo_from_bytea(oid, bytea)",
    "lo_import(text)",
    "lo_import(text, oid)",
    "lo_put(oid, bigint, bytea)",
    "lowrite(integer, bytea)",
)

ADVISORY_LOCK_FUNCTIONS = (
    "SELECT p.oid::regprocedure::text FROM pg_proc p "
    "JOIN pg_namespace n ON n.oid = p.pronamespace "
    "WHERE n.nspname = 'pg_catalog' AND p.proname LIKE %s"
)

APP_ROLE_ATTRIBUTES = "LOGIN NOSUPERUSER CREATEROLE NOCREATEDB NOREPLICATION NOBYPASSRLS"

PUBLIC_RELATIONS = """
SELECT c.relname, c.relkind FROM pg_class c
 WHERE c.relnamespace = 'public'::regnamespace
   AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
   AND c.relowner <> %(role)s::regrole
   AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_class'::regclass
                    AND d.objid = c.oid AND d.deptype IN ('e', 'a', 'i'))
 ORDER BY c.relkind = 'S', c.relname
"""

PUBLIC_FUNCTIONS = """
SELECT p.oid::regprocedure::text FROM pg_proc p
 WHERE p.pronamespace = 'public'::regnamespace AND p.proowner <> %(role)s::regrole
   AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_proc'::regclass
                    AND d.objid = p.oid AND d.deptype = 'e')
"""

PUBLIC_TYPES = """
SELECT t.typname FROM pg_type t
 WHERE t.typnamespace = 'public'::regnamespace AND t.typtype IN ('e', 'd')
   AND t.typowner <> %(role)s::regrole
   AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_type'::regclass
                    AND d.objid = t.oid AND d.deptype = 'e')
"""

TENANT_ROLES = """
SELECT r.rolname FROM pg_roles r
  JOIN pg_auth_members m ON m.member = r.oid
 WHERE m.roleid = %(read)s::regrole AND r.rolname LIKE 'agent\\_%%'
"""

RELATION_KEYWORD = {
    "r": "TABLE",
    "p": "TABLE",
    "f": "FOREIGN TABLE",
    "v": "VIEW",
    "m": "MATERIALIZED VIEW",
    "S": "SEQUENCE",
}


def _ensure_role(conn: psycopg.Connection, role: str, password: str) -> None:
    exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
    verb = "ALTER" if exists else "CREATE"
    conn.execute(
        sql.SQL("{} ROLE {} WITH {} PASSWORD {}").format(
            sql.SQL(verb),
            sql.Identifier(role),
            sql.SQL(APP_ROLE_ATTRIBUTES),
            sql.Literal(password),
        )
    )


def _ensure_read_role(conn: psycopg.Connection) -> None:
    if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (READ_ROLE,)).fetchone():
        conn.execute(sql.SQL("CREATE ROLE {} NOLOGIN").format(sql.Identifier(READ_ROLE)))


def _hand_over_public_objects(conn: psycopg.Connection, role: str) -> None:
    owner = sql.Identifier(role)
    for name, kind in conn.execute(PUBLIC_RELATIONS, {"role": role}).fetchall():
        conn.execute(
            sql.SQL("ALTER {} public.{} OWNER TO {}").format(
                sql.SQL(RELATION_KEYWORD[kind]), sql.Identifier(name), owner
            )
        )
    for (signature,) in conn.execute(PUBLIC_FUNCTIONS, {"role": role}).fetchall():
        conn.execute(sql.SQL("ALTER FUNCTION {} OWNER TO {}").format(sql.SQL(signature), owner))
    for (name,) in conn.execute(PUBLIC_TYPES, {"role": role}).fetchall():
        conn.execute(
            sql.SQL("ALTER TYPE public.{} OWNER TO {}").format(sql.Identifier(name), owner)
        )


def _lock_down_public(conn: psycopg.Connection, role: str) -> None:
    owner = sql.Identifier(role)
    conn.execute("REVOKE USAGE ON LANGUAGE plpgsql, sql FROM PUBLIC")
    conn.execute(sql.SQL("GRANT USAGE ON LANGUAGE sql TO {}").format(owner))
    for function in LARGE_OBJECT_WRITERS:
        conn.execute(
            sql.SQL("REVOKE EXECUTE ON FUNCTION pg_catalog.{} FROM PUBLIC").format(
                sql.SQL(function)
            )
        )
    for (signature,) in conn.execute(ADVISORY_LOCK_FUNCTIONS, ("pg\\_%advisory\\_%",)).fetchall():
        conn.execute(
            sql.SQL("REVOKE EXECUTE ON FUNCTION {} FROM PUBLIC").format(sql.SQL(signature))
        )
        conn.execute(
            sql.SQL("GRANT EXECUTE ON FUNCTION {} TO {}").format(sql.SQL(signature), owner)
        )


def _admit_tenant_roles(conn: psycopg.Connection, role: str) -> None:
    owner = sql.Identifier(role)
    conn.execute(
        sql.SQL("GRANT {} TO {} WITH ADMIN OPTION").format(sql.Identifier(READ_ROLE), owner)
    )
    for (tenant,) in conn.execute(TENANT_ROLES, {"read": READ_ROLE}).fetchall():
        conn.execute(
            sql.SQL("GRANT {} TO {} WITH ADMIN OPTION, INHERIT TRUE, SET TRUE").format(
                sql.Identifier(tenant), owner
            )
        )


def grant_app_role(admin_url: str, app_url: str) -> str:
    app = make_url(app_url)
    role, password = app.username, app.password
    if not role or not password:
        raise ValueError("DATABASE_URL must carry the app role's user name and password.")
    admin = make_url(admin_url).set(drivername="postgresql")
    with psycopg.connect(admin.render_as_string(hide_password=False)) as conn:
        if conn.execute("SELECT current_user = %s", (role,)).fetchone()[0]:
            raise ValueError("MIGRATE_DATABASE_URL and DATABASE_URL must use different roles.")
        _ensure_role(conn, role, password)
        owner = sql.Identifier(role)
        database = conn.execute("SELECT current_database()").fetchone()[0]
        conn.execute(
            sql.SQL("GRANT CONNECT, CREATE, TEMPORARY ON DATABASE {} TO {}").format(
                sql.Identifier(database), owner
            )
        )
        conn.execute(sql.SQL("GRANT USAGE, CREATE ON SCHEMA public TO {}").format(owner))
        conn.execute(sql.SQL("GRANT SET ON PARAMETER temp_file_limit TO {}").format(owner))
        _ensure_read_role(conn)
        _hand_over_public_objects(conn, role)
        _lock_down_public(conn, role)
        _admit_tenant_roles(conn, role)
    return role


def main() -> None:
    if not settings.migrate_database_url:
        raise SystemExit("MIGRATE_DATABASE_URL is not set.")
    role = grant_app_role(settings.migrate_database_url, settings.database_url)
    print(f"app role {role} ready")


if __name__ == "__main__":
    main()
