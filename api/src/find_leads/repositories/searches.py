from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.find_leads.models.search import LeadSearch


class LeadSearchRepository:
    ID_PREFIX = "lq"

    async def by_query(
        self, db: AsyncSession, site_id: str, platform: str, queries: list[str] | None = None
    ) -> dict[str, LeadSearch]:
        stmt = select(LeadSearch).where(
            LeadSearch.site_id == site_id, LeadSearch.platform == platform
        )
        if queries is not None:
            if not queries:
                return {}
            stmt = stmt.where(LeadSearch.query.in_(queries))
        result = await db.execute(stmt)
        return {row.query: row for row in result.scalars().all()}

    async def record(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        platform: str,
        rows: list[dict],
        searched_at: datetime,
    ) -> None:
        if not rows:
            return
        now = datetime.now(UTC)
        stmt = pg_insert(LeadSearch).values(
            [
                {
                    "id": uid(self.ID_PREFIX),
                    "user_id": user_id,
                    "site_id": site_id,
                    "platform": platform,
                    "query": row["query"],
                    "page": row.get("page", 1),
                    "results": row.get("results", []),
                    "searched_at": searched_at,
                    "created_at": now,
                    "updated_at": now,
                }
                for row in rows
            ]
        )
        stmt = stmt.on_conflict_do_update(
            constraint="lead_search_site_query_key",
            set_={
                "page": stmt.excluded.page,
                "results": stmt.excluded.results,
                "searched_at": stmt.excluded.searched_at,
                "updated_at": now,
            },
        )
        await db.execute(stmt)
        await db.flush()

    async def delete_older_than(self, db: AsyncSession, cutoff: datetime) -> int:
        result = await db.execute(delete(LeadSearch).where(LeadSearch.searched_at < cutoff))
        await db.flush()
        return int(result.rowcount or 0)


lead_searches = LeadSearchRepository()
