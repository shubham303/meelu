from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.seo.models.serp import SeoSerpSnapshot
from src.seo.schemas import SerpSnapshotRecord

PRUNE_SQL = """
delete from seo_serp_snapshots s where s.id in (
  select id from (
    select id, row_number() over (partition by keyword_id, device order by fetched_at desc) as rn
    from seo_serp_snapshots where site_id = :site_id and keyword_id = :keyword_id
  ) r where rn > :keep
)
"""

class SeoSerpSnapshotRepository:
    ID_PREFIX = "snap"

    async def create(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        keyword_id: str,
        device: str,
        fetched_at: datetime,
        features: list[str],
    ) -> SerpSnapshotRecord:
        row = SeoSerpSnapshot(
            id=uid(self.ID_PREFIX),
            user_id=user_id,
            site_id=site_id,
            keyword_id=keyword_id,
            device=device,
            fetched_at=fetched_at,
            features=features,
            created_at=fetched_at,
            updated_at=fetched_at,
        )
        db.add(row)
        await db.flush()
        return SerpSnapshotRecord.model_validate(row)

    async def latest(
        self, db: AsyncSession, site_id: str, keyword_id: str
    ) -> SerpSnapshotRecord | None:
        row = (
            await db.execute(
                select(SeoSerpSnapshot)
                .where(SeoSerpSnapshot.site_id == site_id, SeoSerpSnapshot.keyword_id == keyword_id)
                .order_by(SeoSerpSnapshot.fetched_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        return None if row is None else SerpSnapshotRecord.model_validate(row)

    async def fresh_keyword_ids(
        self,
        db: AsyncSession,
        site_id: str,
        device: str,
        cutoff: datetime,
        keyword_ids: list[str],
    ) -> set[str]:
        if not keyword_ids:
            return set()
        rows = await db.execute(
            select(SeoSerpSnapshot.keyword_id).where(
                SeoSerpSnapshot.site_id == site_id,
                SeoSerpSnapshot.device == device,
                SeoSerpSnapshot.fetched_at > cutoff,
                SeoSerpSnapshot.keyword_id.in_(keyword_ids),
            )
        )
        return set(rows.scalars().all())

    async def prune(self, db: AsyncSession, site_id: str, keyword_id: str, keep: int) -> None:
        await db.execute(
            text(PRUNE_SQL), {"site_id": site_id, "keyword_id": keyword_id, "keep": keep}
        )

    async def list_for_site(self, db: AsyncSession, site_id: str) -> list[SerpSnapshotRecord]:
        rows = (
            await db.execute(
                select(SeoSerpSnapshot)
                .where(SeoSerpSnapshot.site_id == site_id)
                .order_by(SeoSerpSnapshot.fetched_at.desc())
            )
        ).scalars()
        return [SerpSnapshotRecord.model_validate(r) for r in rows]


seo_serp_snapshots = SeoSerpSnapshotRepository()
