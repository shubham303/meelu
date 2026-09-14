from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.content.media import repository as repo
from src.content.numbers import number_or_null
from src.content.schemas.media import PostMediaContent, PostMediaRecord

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
IMAGE_TYPES = ("image/jpeg", "image/png", "image/webp", "image/gif")


def _megabytes(size: int) -> str:
    value = Decimal(size) / Decimal(1024) / Decimal(1024)
    return str(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


async def upload_media(
    db: AsyncSession,
    user_id: str,
    data: bytes,
    content_type: str,
    filename: str | None,
    width: Any = None,
    height: Any = None,
) -> PostMediaRecord:
    if content_type not in IMAGE_TYPES:
        raise HTTPException(
            400,
            f"Images only — JPEG, PNG, WebP or GIF. That one is {content_type or 'unknown'}.",
        )

    size = len(data)
    if size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            400,
            f"That image is {_megabytes(size)}MB. The limit is 5MB — these are stored "
            f"in Postgres, not a bucket.",
        )
    if size == 0:
        raise HTTPException(400, "That file is empty.")

    return await repo.create_post_media(
        db,
        user_id,
        {
            "data": data,
            "content_type": content_type,
            "byte_size": size,
            "width": number_or_null(width),
            "height": number_or_null(height),
            "original_name": filename or None,
        },
    )


async def read_media(db: AsyncSession, user_id: str, media_id: str) -> PostMediaContent:
    media = await repo.get_post_media_content(db, user_id, media_id)
    if media is None:
        raise HTTPException(404, "Not found")
    return media
