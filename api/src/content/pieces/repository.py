from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.content.models.content_pieces import ContentPiece
from src.content.schemas.pieces import ContentPieceRecord
from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService


class ContentPieceRepository:
    ID_PREFIX = "cpc"

    async def count(self, db: AsyncSession, site_id: str) -> int:
        total = await db.scalar(
            select(func.count()).select_from(ContentPiece).where(ContentPiece.site_id == site_id)
        )
        return int(total or 0)

    async def get(self, db: AsyncSession, site_id: str, piece_id: str) -> ContentPieceRecord | None:
        row = (
            await db.execute(
                select(ContentPiece).where(
                    ContentPiece.site_id == site_id, ContentPiece.id == piece_id
                )
            )
        ).scalar_one_or_none()
        return None if row is None else ContentPieceRecord.model_validate(row)

    async def create(
        self, db: AsyncSession, user_id: str, site_id: str, values: dict[str, Any]
    ) -> ContentPieceRecord:
        now = datetime.now(UTC)
        row = ContentPiece(
            id=uid(self.ID_PREFIX),
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

    async def update(
        self, db: AsyncSession, piece_id: str, values: dict[str, Any]
    ) -> ContentPieceRecord:
        row = (
            await db.execute(
                update(ContentPiece)
                .where(ContentPiece.id == piece_id)
                .values(**values, updated_at=datetime.now(UTC))
                .returning(ContentPiece)
            )
        ).scalar_one()
        await db.flush()
        return ContentPieceRecord.model_validate(row)

    async def delete(self, db: AsyncSession, piece_id: str) -> None:
        await db.execute(delete(ContentPiece).where(ContentPiece.id == piece_id))
        await db.flush()

    async def list(
        self,
        db: AsyncSession,
        site_id: str,
        paging: PaginationParams,
        *,
        search: str | None = None,
    ) -> PaginatedApiResponse[ContentPieceRecord]:
        query = self._query(site_id, search=search)
        return await PaginationService.paginate_query(
            db,
            query.order_by(ContentPiece.updated_at.desc()),
            paging.page,
            paging.page_size,
            ContentPieceRecord,
        )

    def _query(
        self,
        site_id: str,
        *,
        search: str | None = None,
    ) -> Select:
        where = [ContentPiece.site_id == site_id]
        if search:
            like = f"%{search}%"
            where.append(
                or_(
                    ContentPiece.title.ilike(like),
                    ContentPiece.h1.ilike(like),
                    ContentPiece.target_keyword.ilike(like),
                    ContentPiece.body_markdown.ilike(like),
                )
            )
        return select(ContentPiece).where(*where)


content_pieces = ContentPieceRepository()
