from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.sql import quote_ident


class WorkspaceTableRepository:
    async def rows(self, db: AsyncSession, schema: str, table: str) -> list[dict[str, Any]]:
        result = await db.execute(text(f"SELECT * FROM {quote_ident(schema)}.{quote_ident(table)}"))
        return [dict(row) for row in result.mappings().all()]


workspace_tables = WorkspaceTableRepository()
