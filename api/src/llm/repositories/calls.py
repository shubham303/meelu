from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.llm.models.llm_call import LlmCall
from src.llm.schemas import LlmCallRecord


class LlmCallRepository:
    async def create(self, db: AsyncSession, user_id: str, values: dict[str, Any]) -> LlmCallRecord:
        now = datetime.now(UTC)
        row = LlmCall(id=uid("llm"), user_id=user_id, created_at=now, updated_at=now, **values)
        db.add(row)
        await db.flush()
        return LlmCallRecord.model_validate(row)

    async def set_charged(self, db: AsyncSession, call_id: str, charged_micros: int) -> None:
        row = await db.get(LlmCall, call_id)
        if row is None:
            return
        row.charged_micros = charged_micros
        row.updated_at = datetime.now(UTC)
        await db.flush()

    async def page(
        self, db: AsyncSession, user_id: str, model: str | None, paging: PaginationParams
    ) -> PaginatedApiResponse[LlmCallRecord]:
        conds = [LlmCall.user_id == user_id]
        if model:
            conds.append(LlmCall.model == model)
        total = (
            await db.execute(select(func.count()).select_from(LlmCall).where(*conds))
        ).scalar_one()
        result = await db.execute(
            select(LlmCall)
            .where(*conds)
            .order_by(LlmCall.seq.desc())
            .offset(paging.offset)
            .limit(paging.page_size)
        )
        return PaginatedApiResponse[LlmCallRecord](
            data=[LlmCallRecord.model_validate(row) for row in result.scalars().all()],
            pagination=PaginationService.build_pagination_meta(
                total, paging.page, paging.page_size
            ),
        )


llm_calls = LlmCallRepository()
