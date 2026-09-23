from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.site_pages import service
from src.site_pages.schemas import (
    SiteChunkResponse,
    SitePageBatchRequest,
    SitePageBatchResult,
    SitePageCreateRequest,
    SitePageDeleteResponse,
    SitePageDiscoveryResponse,
    SitePageExportListItemResponse,
    SitePageGraphResult,
    SitePageKeywordCoverageResponse,
    SitePageKeywordQuery,
    SitePageListQuery,
    SitePageListResponse,
    SitePagePruneResult,
    SitePageResponse,
    SitePageSearchRequest,
    SitePageSearchResponse,
    SitePageSlimListItemResponse,
    SitePageStatsResponse,
    SitePageTextListItemResponse,
    SitePageUpdateRequest,
    SitePageVisitedRequest,
    SitePageVisitedResult,
    SitePageVisitSweepResult,
)

router = APIRouter()

LIST_ITEM_RESPONSE = {
    "slim": SitePageSlimListItemResponse,
    "text": SitePageTextListItemResponse,
    "export": SitePageExportListItemResponse,
    "full": SitePageResponse,
}


@router.get("/site/pages")
async def list_pages(
    q: Annotated[SitePageListQuery, Query()],
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageListResponse:
    result = await service.pages(db, ctx.site_id, q.filters(), q.paging(), q.view, q.search_text)
    item = LIST_ITEM_RESPONSE[q.view or "slim"]
    return SitePageListResponse(
        data=[item.model_validate(p) for p in result.data],
        pagination=result.pagination,
        note=result.note,
    )


@router.post("/site/pages/search")
async def search_pages(
    body: SitePageSearchRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageSearchResponse:
    return await service.search(db, ctx.site_id, body)


@router.post("/site/pages")
async def save_pages(
    body: SitePageBatchRequest | SitePageCreateRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageBatchResult | SitePageResponse:
    if isinstance(body, SitePageBatchRequest):
        return await service.save_pages(db, ctx.user_id, ctx.site_id, body)
    response.status_code = 201
    return SitePageResponse.model_validate(
        await service.save_page(db, ctx.user_id, ctx.site_id, body)
    )


@router.get("/site/pages/by-url")
async def page_by_url(
    url: str = Query(...),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageResponse:
    return SitePageResponse.model_validate(await service.resolve_page(db, ctx.site_id, url))


@router.get("/site/pages/stats")
async def page_stats(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageStatsResponse:
    return SitePageStatsResponse.model_validate(await service.stats(db, ctx.user_id, ctx.site_id))


@router.get("/site/pages/discovery")
async def page_discovery(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageDiscoveryResponse:
    return SitePageDiscoveryResponse.model_validate(await service.discovery(db, ctx.site_id))


@router.get("/site/pages/keywords")
async def covered_keywords(
    q: Annotated[SitePageKeywordQuery, Query()],
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageKeywordCoverageResponse:
    result = await service.covered_keywords(db, ctx.site_id, q.filters(), q.limit)
    return SitePageKeywordCoverageResponse.model_validate(result)


@router.post("/site/pages/visited")
async def mark_visited(
    body: SitePageVisitedRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageVisitSweepResult | SitePageVisitedResult:
    if body.reset:
        return await service.start_visit_sweep(db, ctx.site_id)
    return await service.mark_visited(db, ctx.site_id, body)


@router.post("/site/pages/prune")
async def prune_pages(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePagePruneResult:
    return await service.prune_pages(db, ctx.site_id)


@router.post("/site/pages/graph")
async def rebuild_graph(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageGraphResult:
    await service.rebuild_graph(db, ctx.site_id)
    return SitePageGraphResult()


@router.get("/site/pages/{page_id}")
async def get_page(
    page_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageResponse:
    return SitePageResponse.model_validate(await service.page(db, ctx.site_id, page_id))


@router.put("/site/pages/{page_id}")
async def put_page(
    page_id: str,
    body: SitePageUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageResponse:
    record = await service.update_page(db, ctx.user_id, ctx.site_id, page_id, body)
    return SitePageResponse.model_validate(record)


@router.patch("/site/pages/{page_id}")
async def patch_page(
    page_id: str,
    body: SitePageUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageResponse:
    record = await service.update_page(db, ctx.user_id, ctx.site_id, page_id, body)
    return SitePageResponse.model_validate(record)


@router.delete("/site/pages/{page_id}")
async def delete_page(
    page_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageDeleteResponse:
    removed = await service.delete_page(db, ctx.user_id, ctx.site_id, page_id)
    return SitePageDeleteResponse(id=removed.id, url=removed.url)


@router.get("/site/chunks")
async def list_chunks(
    page_id: str = Query(..., alias="pageId"),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> list[SiteChunkResponse]:
    return [
        SiteChunkResponse.model_validate(c) for c in await service.chunks(db, ctx.site_id, page_id)
    ]
