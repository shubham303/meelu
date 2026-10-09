from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.seo.keyword_tracking.constants import BATCH_ROWS, VOLUME_HISTORY_ID_PREFIX
from src.seo.keyword_tracking.models.seo_volume_history import SeoVolumeHistory
from src.seo.keyword_tracking.schemas import VolumeRow

KEY = ("site_id", "keyword", "location_code", "language_code", "month")

VALUES = ("search_volume", "clickstream_volume", "cpc", "competition")


class VolumeHistoryRepository:
    async def months(
        self, db: AsyncSession, site_id: str, location_code: int, language_code: str, since: date
    ) -> list[tuple[str, date, int | None]]:
        rows = await db.execute(
            select(
                SeoVolumeHistory.keyword,
                SeoVolumeHistory.month,
                func.coalesce(SeoVolumeHistory.clickstream_volume, SeoVolumeHistory.search_volume),
            ).where(
                SeoVolumeHistory.site_id == site_id,
                SeoVolumeHistory.location_code == location_code,
                SeoVolumeHistory.language_code == language_code,
                SeoVolumeHistory.month >= since,
            )
        )
        return [(k, m, v) for k, m, v in rows.all()]

    async def markets(self, db: AsyncSession, site_id: str) -> list[tuple[int, str]]:
        rows = await db.execute(
            select(SeoVolumeHistory.location_code, SeoVolumeHistory.language_code)
            .where(SeoVolumeHistory.site_id == site_id)
            .distinct()
        )
        return [(c, lang) for c, lang in rows.all()]

    async def upsert_many(
        self, db: AsyncSession, user_id: str, site_id: str, rows: list[VolumeRow]
    ) -> int:
        if not rows:
            return 0
        now = datetime.now(UTC)
        values = [
            {
                **r.model_dump(),
                "id": uid(VOLUME_HISTORY_ID_PREFIX),
                "user_id": user_id,
                "site_id": site_id,
                "created_at": now,
                "updated_at": now,
            }
            for r in rows
        ]
        for start in range(0, len(values), BATCH_ROWS):
            statement = insert(SeoVolumeHistory).values(values[start : start + BATCH_ROWS])
            updated = {
                c: func.coalesce(statement.excluded[c], getattr(SeoVolumeHistory, c))
                for c in VALUES
            } | {"updated_at": now}
            await db.execute(
                statement.on_conflict_do_update(index_elements=list(KEY), set_=updated)
            )
        return len(values)


seo_volume_history = VolumeHistoryRepository()
