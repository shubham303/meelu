import functools
import hashlib
import hmac
from contextlib import contextmanager
from typing import Any

import psycopg
from sqlalchemy import Connection, Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from src.agent.context import AgentContext
from src.core.logging import log_connection_checkouts
from src.settings import settings

engine = create_engine(
    settings.database_url,
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
    pool_recycle=1800,
)
log_connection_checkouts(engine, "agent_sql")


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def tenant_password(role: str) -> str:
    secret = (make_url(settings.database_url).password or "").encode()
    return hmac.new(secret, role.encode(), hashlib.sha256).hexdigest()


@functools.lru_cache(maxsize=1024)
def tenant_engine(role: str) -> Engine:
    url = make_url(settings.database_url).set(username=role, password=tenant_password(role))
    return create_engine(url, poolclass=NullPool)


@contextmanager
def tenant_txn(role: str, schema: str):
    with tenant_engine(role).begin() as conn:
        conn.exec_driver_sql(f"SET LOCAL statement_timeout = {settings.agent_statement_timeout_ms}")
        conn.exec_driver_sql(f"SET LOCAL work_mem = '{settings.agent_work_mem}'")
        conn.exec_driver_sql("SET LOCAL hash_mem_multiplier = 2")
        conn.exec_driver_sql("SET LOCAL maintenance_work_mem = '64MB'")
        conn.exec_driver_sql(f"SET LOCAL search_path = {quote_ident(schema)}, public")
        yield conn


@contextmanager
def user_txn(ctx: AgentContext):
    if ctx.role is None or ctx.schema is None:
        raise ValueError("No website selected. Pass the x-meelu-site header.")
    with tenant_txn(ctx.role, ctx.schema) as conn:
        yield conn


RESULT_CURSOR = "meelu_result"
FETCH_BATCH = 50


class ResultTooLarge(ValueError):
    pass


def _cell_bytes(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, (bytes, bytearray, memoryview, str)):
        return len(value)
    return len(str(value))


def _take(batch: list, kept: list, limit: int, used: int, max_bytes: int) -> int:
    for row in batch:
        if len(kept) >= limit:
            break
        used += sum(_cell_bytes(v) for v in row)
        if used > max_bytes:
            raise ResultTooLarge(
                f"The result is larger than {max_bytes // 1024**2} MB. Select fewer or narrower "
                "columns, aggregate, or materialize it in your workspace schema."
            )
        kept.append(row)
    return used


def _declare(raw, query: str) -> bool:
    try:
        with raw.transaction():
            raw.execute(f"DECLARE {RESULT_CURSOR} NO SCROLL CURSOR FOR {query}", prepare=True)
    except psycopg.Error:
        return False
    return True


def run_single_statement(
    conn: Connection, query: str, limit: int, max_bytes: int | None = None
) -> tuple[list[str] | None, list[tuple], int]:
    cap = settings.agent_max_result_bytes if max_bytes is None else max_bytes
    raw = conn.connection.driver_connection
    kept: list[tuple] = []
    used = 0
    if _declare(raw, query):
        cursor = raw.cursor()
        try:
            columns = None
            while len(kept) < limit:
                cursor.execute(
                    f"SET LOCAL statement_timeout = {settings.agent_statement_timeout_ms}"
                )
                cursor.execute(f"FETCH {FETCH_BATCH} FROM {RESULT_CURSOR}")
                columns = [d.name for d in cursor.description]
                batch = cursor.fetchall()
                used = _take(batch, kept, limit, used, cap)
                if len(batch) < FETCH_BATCH:
                    break
            cursor.execute(f"CLOSE {RESULT_CURSOR}")
        finally:
            cursor.close()
        return columns, kept, len(kept)
    cursor = raw.cursor()
    try:
        cursor.execute(query, prepare=True)
        if cursor.description is None:
            return None, [], cursor.rowcount
        columns = [d.name for d in cursor.description]
        while len(kept) < limit:
            batch = cursor.fetchmany(FETCH_BATCH)
            if not batch:
                break
            used = _take(batch, kept, limit, used, cap)
        return columns, kept, cursor.rowcount
    finally:
        cursor.close()


def workspace_bytes(conn: Connection, schema: str) -> int:
    row = conn.exec_driver_sql(
        "SELECT coalesce(sum(pg_total_relation_size(c.oid)), 0) FROM pg_class c "
        "JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = %s AND c.relkind IN ('r', 'm', 'p')",
        (schema,),
    ).fetchone()
    return int(row[0])


def ensure_workspace_room(conn: Connection, schema: str) -> None:
    used = workspace_bytes(conn, schema)
    if used > settings.agent_max_workspace_bytes:
        raise ValueError(
            f"Your workspace schema holds {used // 1024**2} MB, above the "
            f"{settings.agent_max_workspace_bytes // 1024**2} MB quota. Drop tables you no "
            "longer need before running more SQL."
        )
