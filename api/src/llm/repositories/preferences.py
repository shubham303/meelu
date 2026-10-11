from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.llm.models.llm_preference import LlmPreference


class LlmPreferenceRepository:
    async def get(self, db: AsyncSession, user_id: str) -> str | None:
        result = await db.execute(
            select(LlmPreference.default_model).where(LlmPreference.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert(self, db: AsyncSession, user_id: str, default_model: str) -> str:
        now = datetime.now(UTC)
        await db.execute(
            insert(LlmPreference)
            .values(user_id=user_id, default_model=default_model, updated_at=now)
            .on_conflict_do_update(
                index_elements=[LlmPreference.user_id],
                set_={"default_model": default_model, "updated_at": now},
            )
        )
        await db.flush()
        return default_model


llm_preferences = LlmPreferenceRepository()
