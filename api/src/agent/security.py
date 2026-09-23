import threading

from src.agent.context import tenant_names
from src.agent.schemas import BootstrapResult
from src.agent.sql import engine, quote_ident

READ_ROLE = "meelu_agent_read"

BLOCKED_TABLES = frozenset(
    {
        "user",
        "access_token",
        "api_keys",
        "agent_plans",
        "provider_cache",
    }
)

_ensured: set[str] = set()
_lock = threading.Lock()


def _role_exists(conn, role: str) -> bool:
    row = conn.exec_driver_sql("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
    return row is not None


def bootstrap() -> BootstrapResult:
    with engine.begin() as conn:
        if not _role_exists(conn, READ_ROLE):
            conn.exec_driver_sql(f"CREATE ROLE {quote_ident(READ_ROLE)} NOLOGIN")
        conn.exec_driver_sql(f"GRANT USAGE ON SCHEMA public TO {quote_ident(READ_ROLE)}")

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

        granted, secured = [], []
        for table in tables:
            if table in BLOCKED_TABLES:
                continue
            qt = quote_ident(table)
            conn.exec_driver_sql(f"GRANT SELECT ON public.{qt} TO {quote_ident(READ_ROLE)}")
            granted.append(table)
            if table in user_scoped:
                conn.exec_driver_sql(f"ALTER TABLE public.{qt} ENABLE ROW LEVEL SECURITY")
                conn.exec_driver_sql(f"DROP POLICY IF EXISTS meelu_agent_select ON public.{qt}")
                conn.exec_driver_sql(
                    f"CREATE POLICY meelu_agent_select ON public.{qt} FOR SELECT "
                    f"USING (user_id = current_setting('meelu.user_id', true))"
                )
                secured.append(table)

    return BootstrapResult(granted=granted, rls=secured)


def ensure_user(user_id: str) -> tuple[str, str]:
    role, schema = tenant_names(user_id)
    if user_id in _ensured:
        return role, schema
    with _lock:
        if user_id in _ensured:
            return role, schema
        with engine.begin() as conn:
            if not _role_exists(conn, role):
                conn.exec_driver_sql(f"CREATE ROLE {quote_ident(role)} NOLOGIN")
            conn.exec_driver_sql(f"GRANT {quote_ident(READ_ROLE)} TO {quote_ident(role)}")
            conn.exec_driver_sql(f"GRANT {quote_ident(role)} TO CURRENT_USER")
            conn.exec_driver_sql(
                f"CREATE SCHEMA IF NOT EXISTS {quote_ident(schema)} AUTHORIZATION {quote_ident(role)}"
            )
        _ensured.add(user_id)
    return role, schema
