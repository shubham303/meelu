from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.seo.site_search.models.site_page_index_status import SitePageIndexStatus
from src.seo.site_search.schemas import (
    NewSitePageIndexStatus,
    SitePageIndexStatusRecord,
)

APPLY_CHUNK = 200
LOOKUP_CHUNK = 5000


def _timestamp(value: str | None) -> datetime | None:
    return None if not value else datetime.fromisoformat(value)


class SitePageIndexStatusRepository:
    ID_PREFIX = "pidx"

    async def list_by_page_ids(
        self, db: AsyncSession, site_id: str, page_ids: list[str]
    ) -> list[SitePageIndexStatusRecord]:
        wanted = list(dict.fromkeys(page_ids))
        found: list[SitePageIndexStatusRecord] = []
        for i in range(0, len(wanted), LOOKUP_CHUNK):
            rows = (
                await db.execute(
                    select(SitePageIndexStatus).where(
                        SitePageIndexStatus.site_id == site_id,
                        SitePageIndexStatus.page_id.in_(wanted[i : i + LOOKUP_CHUNK]),
                    )
                )
            ).scalars()
            found.extend(SitePageIndexStatusRecord.model_validate(r) for r in rows)
        return found

    async def upsert_many(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        rows: dict[str, NewSitePageIndexStatus],
    ) -> int:
        if not rows:
            return 0
        now = datetime.now(UTC)
        applied = 0
        items = list(rows.items())
        for i in range(0, len(items), APPLY_CHUNK):
            values = [
                {
                    "id": uid(self.ID_PREFIX),
                    "user_id": user_id,
                    "site_id": site_id,
                    "page_id": page_id,
                    "index_state": r.index_state,
                    "coverage_state": r.coverage_state,
                    "google_canonical": r.google_canonical,
                    "last_crawl_time": _timestamp(r.last_crawl_time),
                    "index_checked_at": now,
                }
                for page_id, r in items[i : i + APPLY_CHUNK]
            ]
            stmt = pg_insert(SitePageIndexStatus).values(values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["page_id"],
                set_={
                    "index_state": stmt.excluded.index_state,
                    "coverage_state": stmt.excluded.coverage_state,
                    "google_canonical": stmt.excluded.google_canonical,
                    "last_crawl_time": stmt.excluded.last_crawl_time,
                    "index_checked_at": now,
                    "updated_at": now,
                },
            ).returning(SitePageIndexStatus.id)
            applied += len((await db.execute(stmt)).all())
        return applied

    async def list_for_site(
        self, db: AsyncSession, site_id: str
    ) -> list[SitePageIndexStatusRecord]:
        rows = (
            await db.execute(
                select(SitePageIndexStatus).where(SitePageIndexStatus.site_id == site_id)
            )
        ).scalars()
        return [SitePageIndexStatusRecord.model_validate(r) for r in rows]


site_page_index_statuses = SitePageIndexStatusRepository()
