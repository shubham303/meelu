from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.social_listening.models.config import SocialListeningConfig
from src.social_listening.schemas import ConfigResponse


class SocialListeningConfigRepository:
    ID_PREFIX = "slc"

    async def get(self, db: AsyncSession, site_id: str) -> SocialListeningConfig | None:
        result = await db.execute(
            select(SocialListeningConfig).where(SocialListeningConfig.site_id == site_id).limit(1)
        )
        return result.scalars().first()

    async def create(self, db: AsyncSession, user_id: str, site_id: str) -> SocialListeningConfig:
        row = SocialListeningConfig(
            id=uid(self.ID_PREFIX),
            user_id=user_id,
            site_id=site_id,
            platforms=[],
            results_per_keyword=50,
            min_relevance=0.6,
            min_similarity=0.8,
            max_age_days=365,
            drop_dead_posts=True,
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return row

    async def update(
        self, db: AsyncSession, row: SocialListeningConfig, values: dict[str, Any]
    ) -> ConfigResponse:
        for key, value in values.items():
            setattr(row, key, value)
        row.updated_at = datetime.now(UTC)
        await db.flush()
        return ConfigResponse.model_validate(row)


social_listening_configs = SocialListeningConfigRepository()
