from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.content.models.post_media import PostMedia
from src.content.schemas.media import PostMediaContent, PostMediaRecord
from src.core.ids import uid


class PostMediaRepository:
    ID_PREFIX = "pmd"

    async def create(
        self, db: AsyncSession, user_id: str, values: dict[str, Any]
    ) -> PostMediaRecord:
        now = datetime.now(UTC)
        row = PostMedia(
            id=uid(self.ID_PREFIX), user_id=user_id, created_at=now, updated_at=now, **values
        )
        db.add(row)
        await db.flush()
        await db.refresh(row)
        return PostMediaRecord.model_validate(row)

    async def get(self, db: AsyncSession, user_id: str, media_id: str) -> PostMediaRecord | None:
        row = (
            await db.execute(
                select(PostMedia).where(PostMedia.user_id == user_id, PostMedia.id == media_id)
            )
        ).scalar_one_or_none()
        return None if row is None else PostMediaRecord.model_validate(row)

    async def get_content(
        self, db: AsyncSession, user_id: str, media_id: str
    ) -> PostMediaContent | None:
        row = (
            await db.execute(
                select(PostMedia.data, PostMedia.content_type).where(
                    PostMedia.user_id == user_id, PostMedia.id == media_id
                )
            )
        ).first()
        return None if row is None else PostMediaContent(data=row[0], content_type=row[1])


post_medias = PostMediaRepository()
