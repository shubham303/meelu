from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import (
    AuthContext,
    OptionalSiteContext,
    any_site,
    optional_site,
    require,
    require_site,
)
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.sites.schemas import (
    SiteAgentUpdateRequest,
    SiteCreateRequest,
    SiteDeleteResponse,
    SiteFilters,
    SiteListItemResponse,
    SiteResponse,
    SiteSort,
    SiteUpdateRequest,
)
from src.sites.service import site_service

router = APIRouter()


@router.get("/sites")
async def list_sites(
    q: str | None = Query(None),
    domain: str | None = Query(None),
    has_repo: bool | None = Query(None, alias="hasRepo"),
    never_crawled: bool | None = Query(None, alias="neverCrawled"),
    crawled_before: datetime | None = Query(None, alias="crawledBefore"),
    crawled_after: datetime | None = Query(None, alias="crawledAfter"),
    sort: SiteSort | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("sites", "read")),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[SiteListItemResponse]:
    filters = SiteFilters(
        q=q,
        domain=domain,
        has_repo=has_repo,
        never_crawled=never_crawled,
        crawled_before=crawled_before,
        crawled_after=crawled_after,
        sort=sort,
    )
    page = await site_service.list(db, user_id, filters, paging)
    return PaginatedApiResponse[SiteListItemResponse](
        data=[SiteListItemResponse.model_validate(s) for s in page.data],
        pagination=page.pagination,
    )


@router.post("/sites", status_code=201)
async def create_site(
    body: SiteCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("sites", "write")),
) -> SiteResponse:
    return SiteResponse.model_validate(await site_service.create(db, user_id, body))


@router.get("/sites/{site_id}")
async def get_site(
    site_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("sites", "read")),
) -> SiteResponse:
    return SiteResponse.model_validate(await site_service.get(db, user_id, site_id))


@router.put("/sites/{site_id}")
async def put_site(
    site_id: str,
    body: SiteUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("sites", "write")),
) -> SiteResponse:
    return SiteResponse.model_validate(await site_service.update(db, user_id, site_id, body))


@router.patch("/sites/{site_id}")
async def patch_site(
    site_id: str,
    body: SiteUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("sites", "write")),
) -> SiteResponse:
    return SiteResponse.model_validate(await site_service.update(db, user_id, site_id, body))


@router.delete("/sites/{site_id}")
async def delete_site(
    site_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("sites", "write")),
) -> SiteDeleteResponse:
    record = await site_service.delete(db, user_id, site_id)
    return SiteDeleteResponse(id=record.id)


@router.get("/site")
async def get_current_site(
    db: AsyncSession = Depends(get_db),
    ctx: OptionalSiteContext = Depends(optional_site),
) -> SiteResponse | None:
    if ctx.site_id is None:
        return None
    return SiteResponse.model_validate(await site_service.get(db, ctx.user_id, ctx.site_id))


@router.put("/site")
async def put_current_site(
    body: SiteUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SiteResponse:
    return SiteResponse.model_validate(
        await site_service.update(db, ctx.user_id, ctx.site_id, body)
    )


@router.patch("/site")
async def patch_current_site(
    body: SiteAgentUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SiteResponse:
    return SiteResponse.model_validate(
        await site_service.update_as_agent(db, ctx.user_id, ctx.site_id, body)
    )


@router.delete("/site")
async def delete_current_site(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(any_site),
) -> SiteDeleteResponse:
    record = await site_service.delete(db, ctx.user_id, ctx.site_id)
    return SiteDeleteResponse(id=record.id)
