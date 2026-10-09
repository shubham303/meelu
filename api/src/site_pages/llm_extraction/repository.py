from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Integer, cast, delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.site_pages.models.site_page_llm_extraction import SitePageLlmExtraction
from src.site_pages.schemas.llm_extraction import (
    ExtractionState,
    PageLlmExtractionCreateRequest,
    PageLlmExtractionRecord,
)


class SitePageLlmExtractionRepository:
    ID_PREFIX = "spx"

    async def set_page_type(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        page_id: str,
        page_type: str,
        content_hash: str | None,
    ) -> PageLlmExtractionRecord | None:
        now = datetime.now(UTC)
        stmt = (
            pg_insert(SitePageLlmExtraction)
            .values(
                id=uid(self.ID_PREFIX),
                user_id=user_id,
                site_id=site_id,
                page_id=page_id,
                page_type=page_type,
                extracted_from_hash=content_hash,
                created_at=now,
                extracted_at=now,
                updated_at=now,
                extract_attempts=0,
            )
            .on_conflict_do_update(
                index_elements=[SitePageLlmExtraction.page_id],
                set_={
                    "page_type": page_type,
                    "extracted_from_hash": content_hash,
                    "error": None,
                    "extract_attempts": 0,
                    "updated_at": now,
                },
                where=SitePageLlmExtraction.page_type.is_(None),
            )
            .returning(SitePageLlmExtraction.id)
        )
        saved = (await db.execute(stmt)).scalar_one_or_none()
        if saved is None:
            return None
        await db.flush()
        return await self.get(db, site_id, saved)

    async def upsert(
        self, db: AsyncSession, user_id: str, site_id: str, body: PageLlmExtractionCreateRequest
    ) -> PageLlmExtractionRecord:
        now = datetime.now(UTC)
        values: dict[str, Any] = {**body.values(), "extracted_at": now, "updated_at": now}
        failed = body.error is not None
        stmt = (
            pg_insert(SitePageLlmExtraction)
            .values(
                id=uid(self.ID_PREFIX),
                user_id=user_id,
                site_id=site_id,
                page_id=body.page_id,
                created_at=now,
                extract_attempts=1 if failed else 0,
                **values,
            )
            .on_conflict_do_update(
                index_elements=[SitePageLlmExtraction.page_id],
                set_={
                    **values,
                    "extract_attempts": (
                        SitePageLlmExtraction.extract_attempts + 1 if failed else 0
                    ),
                },
            )
            .returning(SitePageLlmExtraction.id)
        )
        saved = (await db.execute(stmt)).scalar_one()
        await db.flush()
        found = await self.get(db, site_id, saved)
        assert found is not None
        return found

    async def get(
        self, db: AsyncSession, site_id: str, extraction_id: str
    ) -> PageLlmExtractionRecord | None:
        result = await db.execute(
            select(SitePageLlmExtraction)
            .where(
                SitePageLlmExtraction.site_id == site_id,
                SitePageLlmExtraction.id == extraction_id,
            )
            .limit(1)
            .execution_options(populate_existing=True)
        )
        row = result.scalar_one_or_none()
        return None if row is None else PageLlmExtractionRecord.model_validate(row)

    async def get_by_page(
        self, db: AsyncSession, site_id: str, page_id: str
    ) -> PageLlmExtractionRecord | None:
        result = await db.execute(
            select(SitePageLlmExtraction)
            .where(
                SitePageLlmExtraction.site_id == site_id, SitePageLlmExtraction.page_id == page_id
            )
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return None if row is None else PageLlmExtractionRecord.model_validate(row)

    async def by_page_ids(
        self, db: AsyncSession, site_id: str, page_ids: list[str]
    ) -> dict[str, PageLlmExtractionRecord]:
        if not page_ids:
            return {}
        rows = await db.execute(
            select(SitePageLlmExtraction).where(
                SitePageLlmExtraction.site_id == site_id,
                SitePageLlmExtraction.page_id.in_(set(page_ids)),
            )
        )
        return {row.page_id: PageLlmExtractionRecord.model_validate(row) for row in rows.scalars()}

    async def list_filtered(
        self, db: AsyncSession, site_id: str, page_type: str | None, paging: PaginationParams
    ) -> PaginatedApiResponse[PageLlmExtractionRecord]:
        stmt = select(SitePageLlmExtraction).where(SitePageLlmExtraction.site_id == site_id)
        if page_type:
            stmt = stmt.where(SitePageLlmExtraction.page_type == page_type)
        stmt = stmt.order_by(SitePageLlmExtraction.seq.desc())
        return await PaginationService.paginate_query(
            db,
            stmt,
            page=paging.page,
            page_size=paging.page_size,
            response_model=PageLlmExtractionRecord,
        )

    async def delete(self, db: AsyncSession, site_id: str, extraction_id: str) -> bool:
        result = await db.execute(
            delete(SitePageLlmExtraction)
            .where(
                SitePageLlmExtraction.site_id == site_id,
                SitePageLlmExtraction.id == extraction_id,
            )
            .returning(SitePageLlmExtraction.id)
        )
        return result.scalar_one_or_none() is not None

    async def review_queue(self, db: AsyncSession, site_id: str) -> list[tuple[str, str | None]]:
        rows = await db.execute(
            select(SitePageLlmExtraction.page_id, SitePageLlmExtraction.extracted_from_hash)
            .where(
                SitePageLlmExtraction.site_id == site_id,
                SitePageLlmExtraction.use_large_llm_review.is_(True),
            )
            .order_by(SitePageLlmExtraction.extracted_at.asc())
        )
        return [(r.page_id, r.extracted_from_hash) for r in rows]

    async def save_review(
        self,
        db: AsyncSession,
        site_id: str,
        page_id: str,
        content_hash: str,
        model: str,
        values: dict[str, Any],
    ) -> PageLlmExtractionRecord | None:
        now = datetime.now(UTC)
        saved = (
            await db.execute(
                update(SitePageLlmExtraction)
                .where(
                    SitePageLlmExtraction.site_id == site_id,
                    SitePageLlmExtraction.page_id == page_id,
                    SitePageLlmExtraction.use_large_llm_review.is_(True),
                    SitePageLlmExtraction.extracted_from_hash == content_hash,
                )
                .values(**values, model=model, error=None, extracted_at=now, updated_at=now)
                .returning(SitePageLlmExtraction.id)
            )
        ).scalar_one_or_none()
        if saved is None:
            return None
        await db.flush()
        return await self.get(db, site_id, saved)

    async def states_by_page_ids(
        self, db: AsyncSession, site_id: str, page_ids: list[str]
    ) -> dict[str, ExtractionState]:
        if not page_ids:
            return {}
        rows = await db.execute(
            select(
                SitePageLlmExtraction.page_id,
                SitePageLlmExtraction.page_type,
                SitePageLlmExtraction.extracted_from_hash,
                SitePageLlmExtraction.error,
                SitePageLlmExtraction.extract_attempts,
            ).where(
                SitePageLlmExtraction.site_id == site_id,
                SitePageLlmExtraction.page_id.in_(set(page_ids)),
            )
        )
        return {r.page_id: ExtractionState.model_validate(dict(r)) for r in rows.mappings()}

    async def page_types_by_page_ids(
        self, db: AsyncSession, site_id: str, page_ids: list[str] | None = None
    ) -> dict[str, str | None]:
        if page_ids is not None and not page_ids:
            return {}
        conds: list[Any] = [SitePageLlmExtraction.site_id == site_id]
        if page_ids is not None:
            conds.append(SitePageLlmExtraction.page_id.in_(set(page_ids)))
        rows = await db.execute(
            select(SitePageLlmExtraction.page_id, SitePageLlmExtraction.page_type).where(*conds)
        )
        return {r.page_id: r.page_type for r in rows}

    async def broad_page_types_by_page_ids(
        self, db: AsyncSession, site_id: str, page_ids: list[str] | None = None
    ) -> dict[str, str | None]:
        if page_ids is not None and not page_ids:
            return {}
        conds: list[Any] = [SitePageLlmExtraction.site_id == site_id]
        if page_ids is not None:
            conds.append(SitePageLlmExtraction.page_id.in_(set(page_ids)))
        rows = await db.execute(
            select(SitePageLlmExtraction.page_id, SitePageLlmExtraction.broad_page_type).where(
                *conds
            )
        )
        return {r.page_id: r.broad_page_type for r in rows}

    async def page_ids_with_types(
        self, db: AsyncSession, site_id: str, page_types: list[str]
    ) -> list[str]:
        if not page_types:
            return []
        rows = await db.execute(
            select(SitePageLlmExtraction.page_id).where(
                SitePageLlmExtraction.site_id == site_id,
                SitePageLlmExtraction.page_type.in_(set(page_types)),
            )
        )
        return list(rows.scalars().all())

    async def states_by_site_ids(
        self, db: AsyncSession, site_ids: list[str]
    ) -> dict[str, ExtractionState]:
        if not site_ids:
            return {}
        rows = await db.execute(
            select(
                SitePageLlmExtraction.page_id,
                SitePageLlmExtraction.page_type,
                SitePageLlmExtraction.extracted_from_hash,
                SitePageLlmExtraction.error,
                SitePageLlmExtraction.extract_attempts,
            ).where(SitePageLlmExtraction.site_id.in_(set(site_ids)))
        )
        return {r.page_id: ExtractionState.model_validate(dict(r)) for r in rows.mappings()}

    async def count_by_page_type(self, db: AsyncSession, site_id: str) -> dict[str | None, int]:
        rows = await db.execute(
            select(SitePageLlmExtraction.page_type, cast(func.count(), Integer))
            .where(SitePageLlmExtraction.site_id == site_id)
            .group_by(SitePageLlmExtraction.page_type)
        )
        return {r[0]: int(r[1]) for r in rows}


site_page_llm_extractions = SitePageLlmExtractionRepository()
