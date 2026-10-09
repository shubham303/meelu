from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.seo.keyword_tracking.constants import BATCH_ROWS, RANK_HISTORY_ID_PREFIX
from src.seo.keyword_tracking.models.seo_rank_history import SeoRankHistory
from src.seo.keyword_tracking.schemas import RankRow

KEY = ("site_id", "keyword", "location_code", "language_code", "observed_on", "url")

VALUES = ("source", "domain", "is_site", "rank_group", "rank_absolute", "title")


class RankHistoryRepository:
    async def keywords_with_source(
        self,
        db: AsyncSession,
        site_id: str,
        keywords: list[str],
        location_code: int,
        language_code: str,
        source: str,
    ) -> set[str]:
        rows = await db.scalars(
            select(SeoRankHistory.keyword)
            .where(
                SeoRankHistory.site_id == site_id,
                SeoRankHistory.keyword.in_(keywords),
                SeoRankHistory.location_code == location_code,
                SeoRankHistory.language_code == language_code,
                SeoRankHistory.source == source,
            )
            .distinct()
        )
        return set(rows)

    async def snapshot_days(
        self, db: AsyncSession, site_id: str, location_code: int, language_code: str, since: date
    ) -> list[tuple[str, date]]:
        rows = await db.execute(
            select(SeoRankHistory.keyword, SeoRankHistory.observed_on)
            .where(*self._market(site_id, location_code, language_code, since))
            .distinct()
        )
        return [(k, d) for k, d in rows.all()]

    async def site_rankings(
        self, db: AsyncSession, site_id: str, location_code: int, language_code: str, since: date
    ) -> list[tuple[str, date, int, str]]:
        rows = await db.execute(
            select(
                SeoRankHistory.keyword,
                SeoRankHistory.observed_on,
                SeoRankHistory.rank_group,
                SeoRankHistory.url,
            ).where(
                *self._market(site_id, location_code, language_code, since),
                SeoRankHistory.is_site.is_(True),
            )
        )
        return [(k, d, r, u) for k, d, r, u in rows.all()]

    async def markets(self, db: AsyncSession, site_id: str) -> list[tuple[int, str]]:
        rows = await db.execute(
            select(SeoRankHistory.location_code, SeoRankHistory.language_code)
            .where(SeoRankHistory.site_id == site_id)
            .distinct()
        )
        return [(c, lang) for c, lang in rows.all()]

    def _market(self, site_id: str, location_code: int, language_code: str, since: date):
        return (
            SeoRankHistory.site_id == site_id,
            SeoRankHistory.location_code == location_code,
            SeoRankHistory.language_code == language_code,
            SeoRankHistory.observed_on >= since,
        )

    async def upsert_many(
        self, db: AsyncSession, user_id: str, site_id: str, rows: list[RankRow]
    ) -> int:
        if not rows:
            return 0
        now = datetime.now(UTC)
        unique = {
            (r.keyword, r.location_code, r.language_code, r.observed_on, r.url): r for r in rows
        }
        values = [
            {
                **r.model_dump(),
                "id": uid(RANK_HISTORY_ID_PREFIX),
                "user_id": user_id,
                "site_id": site_id,
                "created_at": now,
                "updated_at": now,
            }
            for r in unique.values()
        ]
        for start in range(0, len(values), BATCH_ROWS):
            statement = insert(SeoRankHistory).values(values[start : start + BATCH_ROWS])
            updated = {c: statement.excluded[c] for c in VALUES} | {"updated_at": now}
            await db.execute(
                statement.on_conflict_do_update(index_elements=list(KEY), set_=updated)
            )
        return len(values)


seo_rank_history = RankHistoryRepository()
