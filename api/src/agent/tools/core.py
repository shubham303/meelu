import psycopg

from src.agent.context import current
from src.agent.schemas import SqlRowsResponse, SqlWriteResponse
from src.agent.server import tool
from src.agent.sql import ensure_workspace_room, run_single_statement, schema_hint, user_txn
from src.data_analytics.shared.serialize import jsonable
from src.settings import settings


@tool()
def run_sql(query: str, limit: int = 200) -> SqlRowsResponse | SqlWriteResponse:
    """Run one SQL statement as this user. SELECTs return up to `limit` rows;
    writes are only possible in your workspace schema and report the affected
    row count. One statement per call."""
    ctx = current()
    limit = max(1, min(int(limit), settings.agent_max_sql_rows))
    try:
        with user_txn(ctx) as conn:
            ensure_workspace_room(conn, ctx.schema)
            columns, fetched, rowcount = run_single_statement(conn, query, limit + 1)
    except (psycopg.errors.UndefinedColumn, psycopg.errors.UndefinedTable) as e:
        missing_table = isinstance(e, psycopg.errors.UndefinedTable)
        with user_txn(ctx) as conn:
            hint = schema_hint(conn, ctx.schema, query, missing_table)
        raise ValueError(f"{str(e).strip()}\n{hint}".strip()) from e
    if columns is None:
        return SqlWriteResponse(row_count=rowcount, status="ok")
    rows = [jsonable(list(r)) for r in fetched[:limit]]
    return SqlRowsResponse(
        columns=columns, rows=rows, row_count=len(rows), truncated=len(fetched) > limit
    )
