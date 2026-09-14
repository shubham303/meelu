from contextlib import contextmanager

from sqlalchemy import create_engine

from src.agent.context import AgentContext
from src.settings import settings

engine = create_engine(
    settings.database_url,
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=1800,
)


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


@contextmanager
def user_txn(ctx: AgentContext):
    with engine.begin() as conn:
        conn.exec_driver_sql("SELECT set_config('meelu.user_id', %s, true)", (ctx.user_id,))
        if ctx.site_id:
            conn.exec_driver_sql("SELECT set_config('meelu.site_id', %s, true)", (ctx.site_id,))
        conn.exec_driver_sql(f"SET LOCAL statement_timeout = {settings.agent_statement_timeout_ms}")
        conn.exec_driver_sql(f"SET LOCAL work_mem = '{settings.agent_work_mem}'")
        conn.exec_driver_sql(f"SET LOCAL search_path = {quote_ident(ctx.schema)}, public")
        conn.exec_driver_sql(f"SET LOCAL ROLE {quote_ident(ctx.role)}")
        yield conn
