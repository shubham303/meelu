from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.content.models.content_pieces import ContentPiece
from src.content.schemas.pieces import ContentPieceCountsResponse, ContentPieceRecord
from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService


def _query(
    site_id: str,
    *,
    status: str | None = None,
    channel_key: str | None = None,
    search: str | None = None,
):
    where = [ContentPiece.site_id == site_id]
    if status:
        where.append(ContentPiece.status == status)
    if channel_key:
        where.append(ContentPiece.channel_key == channel_key)
    if search:
        like = f"%{search}%"
        where.append(or_(ContentPiece.title.ilike(like), ContentPiece.body_markdown.ilike(like)))
    return select(ContentPiece).where(*where)


async def list_pieces(
    db: AsyncSession,
    site_id: str,
    paging: PaginationParams,
    *,
    status: str | None = None,
    channel_key: str | None = None,
    search: str | None = None,
) -> PaginatedApiResponse[ContentPieceRecord]:
    query = _query(site_id, status=status, channel_key=channel_key, search=search).order_by(
        ContentPiece.updated_at.desc()
    )
    return await PaginationService.paginate_query(
        db, query, paging.page, paging.page_size, ContentPieceRecord
    )


async def counts_by_status(db: AsyncSession, site_id: str) -> ContentPieceCountsResponse:
    rows = await db.execute(
        select(ContentPiece.status, func.count())
        .where(ContentPiece.site_id == site_id)
        .group_by(ContentPiece.status)
    )
    return ContentPieceCountsResponse(by_status={status: int(n) for status, n in rows.all()})


async def get_piece(db: AsyncSession, site_id: str, piece_id: str) -> ContentPieceRecord | None:
    row = (
        await db.execute(
            select(ContentPiece).where(ContentPiece.site_id == site_id, ContentPiece.id == piece_id)
        )
    ).scalar_one_or_none()
    return None if row is None else ContentPieceRecord.model_validate(row)


async def create_piece(
    db: AsyncSession, user_id: str, site_id: str, values: dict[str, Any]
) -> ContentPieceRecord:
    now = datetime.now(UTC)
    row = ContentPiece(
        id=uid("cpc"),
        user_id=user_id,
        site_id=site_id,
        created_at=now,
        updated_at=now,
        **values,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return ContentPieceRecord.model_validate(row)


async def update_piece(
    db: AsyncSession, piece_id: str, values: dict[str, Any]
) -> ContentPieceRecord:
    row = (
        await db.execute(
            update(ContentPiece)
            .where(ContentPiece.id == piece_id)
            .values(**values, updated_at=datetime.now(UTC))
            .returning(ContentPiece)
        )
    ).scalar_one()
    return ContentPieceRecord.model_validate(row)


async def delete_piece(db: AsyncSession, piece_id: str) -> None:
    await db.execute(delete(ContentPiece).where(ContentPiece.id == piece_id))
    await db.flush()
