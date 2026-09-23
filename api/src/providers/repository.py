from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.providers.models.provider_cache import ProviderCache
from src.providers.models.provider_call import ProviderCall
from src.providers.schemas import ProviderCallResponse


async def cached(db: AsyncSession, cache_key: str) -> ProviderCache | None:
    row = await db.execute(
        select(ProviderCache).where(
            ProviderCache.cache_key == cache_key,
            ProviderCache.expires_at > datetime.now(UTC),
        )
    )
    return row.scalar_one_or_none()


async def put_cache(
    db: AsyncSession,
    *,
    cache_key: str,
    domain: str,
    capability: str,
    provider: str,
    request: dict[str, Any],
    response: Any,
    vendor_cost_micros: int,
    ttl: timedelta,
) -> None:
    now = datetime.now(UTC)
    values = {
        "domain": domain,
        "capability": capability,
        "provider": provider,
        "request": request,
        "response": response,
        "vendor_cost_micros": vendor_cost_micros,
        "fetched_at": now,
        "expires_at": now + ttl,
        "updated_at": now,
    }
    await db.execute(
        insert(ProviderCache)
        .values(id=uid("pcache"), cache_key=cache_key, created_at=now, **values)
        .on_conflict_do_update(index_elements=["cache_key"], set_=values)
    )


async def log_call(
    db: AsyncSession,
    *,
    user_id: str,
    site_id: str | None,
    domain: str,
    capability: str,
    provider: str | None,
    cache_key: str,
    cache_hit: bool,
    vendor_cost_micros: int,
    charged_micros: int,
    status: str,
    error: str | None,
    duration_ms: int,
) -> ProviderCall:
    now = datetime.now(UTC)
    row = ProviderCall(
        id=uid("pcall"),
        user_id=user_id,
        site_id=site_id,
        domain=domain,
        capability=capability,
        provider=provider,
        cache_key=cache_key,
        cache_hit=cache_hit,
        vendor_cost_micros=vendor_cost_micros,
        charged_micros=charged_micros,
        status=status,
        error=error,
        duration_ms=duration_ms,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.flush()
    return row


async def list_calls(
    db: AsyncSession, user_id: str, paging: PaginationParams, domain: str | None
) -> PaginatedApiResponse[ProviderCallResponse]:
    query = select(ProviderCall).where(ProviderCall.user_id == user_id)
    if domain:
        query = query.where(ProviderCall.domain == domain)
    query = query.order_by(ProviderCall.seq.desc())
    return await PaginationService.paginate_query(
        db, query, paging.page, paging.page_size, ProviderCallResponse
    )
