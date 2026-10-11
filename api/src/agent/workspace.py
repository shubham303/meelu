import asyncio
from typing import Any

from sqlalchemy.exc import ProgrammingError

from src.agent.security import ensure_tenant
from src.agent.sql import quote_ident, run_single_statement, tenant_txn
from src.settings import settings


class WorkspaceTableRepository:
    async def rows(self, user_id: str, site_id: str, table: str) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._rows, user_id, site_id, table)

    def _rows(self, user_id: str, site_id: str, table: str) -> list[dict[str, Any]]:
        role, schema = ensure_tenant(user_id, site_id)
        cap = settings.agent_max_workspace_rows
        try:
            with tenant_txn(role, schema) as conn:
                source = f"SELECT * FROM {quote_ident(schema)}.{quote_ident(table)} LIMIT {cap + 1}"
                size = conn.exec_driver_sql(
                    f"SELECT COALESCE(SUM(pg_column_size(t.*)), 0) FROM ({source}) t"
                ).scalar_one()
                if size > settings.agent_max_frame_bytes:
                    raise ValueError(
                        f"{table} holds more than {settings.agent_max_frame_bytes // 1024**2} MB; "
                        "narrow it before handing it over."
                    )
                result = conn.exec_driver_sql(source)
                rows = [dict(row) for row in result.mappings().all()]
        except ProgrammingError as exc:
            raise ValueError(f"Could not read {table} from your workspace schema.") from exc
        if len(rows) > cap:
            raise ValueError(f"{table} has more than {cap} rows; narrow it before handing it over.")
        return rows

    async def query(
        self, user_id: str, site_id: str, sql: str
    ) -> tuple[list[str], list[tuple[Any, ...]]]:
        return await asyncio.to_thread(self._query, user_id, site_id, sql)

    def _query(
        self, user_id: str, site_id: str, sql: str
    ) -> tuple[list[str], list[tuple[Any, ...]]]:
        role, schema = ensure_tenant(user_id, site_id)
        cap = settings.agent_max_workspace_rows
        try:
            with tenant_txn(role, schema) as conn:
                columns, rows, _ = run_single_statement(
                    conn, sql, cap + 1, max_bytes=settings.agent_max_frame_bytes
                )
        except Exception as exc:
            raise ValueError(f"The query failed: {exc}") from exc
        if columns is None:
            raise ValueError("The query must be a SELECT that returns rows.")
        if len(rows) > cap:
            raise ValueError(f"The query returned more than {cap} rows; narrow it.")
        return columns, [tuple(row) for row in rows]


workspace_tables = WorkspaceTableRepository()
