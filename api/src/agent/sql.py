import hashlib
import hmac
import threading
from contextlib import contextmanager

from sqlalchemy import Connection, Engine, create_engine
from sqlalchemy.engine import make_url

from src.agent.context import AgentContext
from src.settings import settings

engine = create_engine(
    settings.database_url,
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=1800,
)

_tenant_engines: dict[str, Engine] = {}
_tenant_lock = threading.Lock()


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def tenant_password(role: str) -> str:
    secret = (make_url(settings.database_url).password or "").encode()
    return hmac.new(secret, role.encode(), hashlib.sha256).hexdigest()


def tenant_engine(role: str) -> Engine:
    found = _tenant_engines.get(role)
    if found is not None:
        return found
    with _tenant_lock:
        found = _tenant_engines.get(role)
        if found is None:
            url = make_url(settings.database_url).set(username=role, password=tenant_password(role))
            found = create_engine(
                url,
                pool_size=1,
                max_overflow=settings.agent_tenant_connections - 1,
                pool_pre_ping=True,
                pool_recycle=1800,
            )
            _tenant_engines[role] = found
    return found


@contextmanager
def tenant_txn(role: str, schema: str):
    with tenant_engine(role).begin() as conn:
        conn.exec_driver_sql(f"SET LOCAL statement_timeout = {settings.agent_statement_timeout_ms}")
        conn.exec_driver_sql(f"SET LOCAL work_mem = '{settings.agent_work_mem}'")
        conn.exec_driver_sql(f"SET LOCAL search_path = {quote_ident(schema)}, public")
        yield conn


@contextmanager
def user_txn(ctx: AgentContext):
    with tenant_txn(ctx.role, ctx.schema) as conn:
        yield conn


def run_single_statement(conn: Connection, query: str, limit: int):
    cursor = conn.connection.driver_connection.cursor()
    try:
        cursor.execute(query, prepare=True)
        if cursor.description is None:
            return None, [], cursor.rowcount
        columns = [d.name for d in cursor.description]
        return columns, cursor.fetchmany(limit), cursor.rowcount
    finally:
        cursor.close()
