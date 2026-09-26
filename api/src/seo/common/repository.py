from datetime import UTC, datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService


def now() -> datetime:
    return datetime.now(UTC)


def vector_list(value) -> list[float] | None:
    return None if value is None else [float(x) for x in value]


async def count(db: AsyncSession, query: Select) -> int:
    return int((await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0)


async def page(db: AsyncSession, query: Select, order, paging: PaginationParams, record):
    clauses = order if isinstance(order, tuple) else (order,)
    rows = (
        await db.execute(query.order_by(*clauses).offset(paging.offset).limit(paging.page_size))
    ).scalars()
    total = await count(db, query)
    return PaginatedApiResponse[record](
        data=[record.model_validate(r) for r in rows],
        pagination=PaginationService.build_pagination_meta(total, paging.page, paging.page_size),
    )
