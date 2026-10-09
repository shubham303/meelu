from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.site_pages.llm_extraction.service import site_page_llm_extraction_service
from src.site_pages.schemas import (
    SiteChunkResponse,
    SitePageBatchRequest,
    SitePageBatchResult,
    SitePageCreateRequest,
    SitePageDeleteResponse,
    SitePageDiscoveryResponse,
    SitePageExportListItemResponse,
    SitePageGraphResult,
    SitePageLinksResponse,
    SitePageListQuery,
    SitePageListResponse,
    SitePagePruneResult,
    SitePageResponse,
    SitePageSlimListItemResponse,
    SitePageStatsResponse,
    SitePageTextListItemResponse,
    SitePageUpdateRequest,
    SitePageVisitedRequest,
    SitePageVisitedResult,
    SitePageVisitSweepResult,
)
from src.site_pages.schemas.links import SitePageOutlinksRequest, SitePageOutlinksResult
from src.site_pages.schemas.llm_extraction import (
    PageLlmExtractionCreateRequest,
    PageLlmExtractionDeleteResponse,
    PageLlmExtractionListQuery,
    PageLlmExtractionListResponse,
    PageLlmExtractionPageTypeRequest,
    PageLlmExtractionResponse,
    PageLlmExtractionReviewQueueQuery,
    PageLlmExtractionReviewQueueResponse,
    PageLlmExtractionReviewRequest,
    PageLlmExtractionStatsResponse,
)
from src.site_pages.schemas.search import SitePageSearchRequest, SitePageSearchResponse
from src.site_pages.service import site_page_service

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
    result = await site_page_service.list_pages(
        db, ctx.site_id, q.filters(), q.paging(), q.view, q.search_text
    )
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
    return await site_page_service.search(db, ctx.site_id, body)


@router.post("/site/pages")
async def save_pages(
    body: SitePageBatchRequest | SitePageCreateRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageBatchResult | SitePageResponse:
    if isinstance(body, SitePageBatchRequest):
        return await site_page_service.save_many(db, ctx.user_id, ctx.site_id, body)
    response.status_code = 201
    return SitePageResponse.model_validate(
        await site_page_service.save(db, ctx.user_id, ctx.site_id, body)
    )


@router.get("/site/pages/by-url")
async def page_by_url(
    url: str = Query(...),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageResponse:
    return SitePageResponse.model_validate(await site_page_service.get_by_url(db, ctx.site_id, url))


@router.get("/site/pages/stats")
async def page_stats(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageStatsResponse:
    return SitePageStatsResponse.model_validate(
        await site_page_service.stats(db, ctx.user_id, ctx.site_id)
    )


@router.get("/site/pages/discovery")
async def page_discovery(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageDiscoveryResponse:
    return SitePageDiscoveryResponse.model_validate(
        await site_page_service.discovery(db, ctx.site_id)
    )


@router.post("/site/pages/visited")
async def mark_visited(
    body: SitePageVisitedRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageVisitSweepResult | SitePageVisitedResult:
    if body.reset:
        return await site_page_service.start_visit_sweep(db, ctx.site_id)
    return await site_page_service.mark_visited(db, ctx.site_id, body)


@router.post("/site/pages/prune")
async def prune_pages(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePagePruneResult:
    return await site_page_service.prune(db, ctx.site_id)


@router.post("/site/pages/links")
async def save_outlinks(
    body: SitePageOutlinksRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageOutlinksResult:
    return await site_page_service.save_outlinks(db, ctx.user_id, ctx.site_id, body)


@router.post("/site/pages/graph")
async def rebuild_graph(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageGraphResult:
    await site_page_service.rebuild_graph(db, ctx.site_id)
    return SitePageGraphResult()


@router.get("/site/pages/{page_id}")
async def get_page(
    page_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageResponse:
    return SitePageResponse.model_validate(await site_page_service.get(db, ctx.site_id, page_id))


@router.get("/site/pages/{page_id}/links")
async def page_links(
    page_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageLinksResponse:
    return SitePageLinksResponse.model_validate(
        await site_page_service.links(db, ctx.site_id, page_id)
    )


@router.put("/site/pages/{page_id}")
async def put_page(
    page_id: str,
    body: SitePageUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageResponse:
    record = await site_page_service.update(db, ctx.user_id, ctx.site_id, page_id, body)
    return SitePageResponse.model_validate(record)


@router.patch("/site/pages/{page_id}")
async def patch_page(
    page_id: str,
    body: SitePageUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageResponse:
    record = await site_page_service.update(db, ctx.user_id, ctx.site_id, page_id, body)
    return SitePageResponse.model_validate(record)


@router.delete("/site/pages/{page_id}")
async def delete_page(
    page_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> SitePageDeleteResponse:
    removed = await site_page_service.delete(db, ctx.user_id, ctx.site_id, page_id)
    return SitePageDeleteResponse(id=removed.id, url=removed.url)


@router.get("/site/chunks")
async def list_chunks(
    page_id: str = Query(..., alias="pageId"),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> list[SiteChunkResponse]:
    return [
        SiteChunkResponse.model_validate(c)
        for c in await site_page_service.chunks(db, ctx.site_id, page_id)
    ]


@router.get("/site/page-llm-extractions")
async def list_extractions(
    q: Annotated[PageLlmExtractionListQuery, Query()],
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageLlmExtractionListResponse:
    result = await site_page_llm_extraction_service.list_extractions(
        db, ctx.site_id, q.page_type, q.paging()
    )
    return PageLlmExtractionListResponse(
        data=[PageLlmExtractionResponse.model_validate(r) for r in result.data],
        pagination=result.pagination,
    )


@router.post("/site/page-llm-extractions")
async def save_extraction(
    body: PageLlmExtractionCreateRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageLlmExtractionResponse:
    response.status_code = 201
    return PageLlmExtractionResponse.model_validate(
        await site_page_llm_extraction_service.save(db, ctx.user_id, ctx.site_id, body)
    )


@router.post("/site/page-llm-extractions/by-page/{page_id}/page-type")
async def set_extraction_page_type(
    page_id: str,
    body: PageLlmExtractionPageTypeRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageLlmExtractionResponse:
    return PageLlmExtractionResponse.model_validate(
        await site_page_llm_extraction_service.set_page_type(
            db, ctx.user_id, ctx.site_id, page_id, body.page_type
        )
    )


@router.get("/site/page-llm-extractions/review-queue")
async def extraction_review_queue(
    q: Annotated[PageLlmExtractionReviewQueueQuery, Query()],
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageLlmExtractionReviewQueueResponse:
    return PageLlmExtractionReviewQueueResponse.model_validate(
        await site_page_llm_extraction_service.review_queue(db, ctx.site_id, q.limit)
    )


@router.post("/site/page-llm-extractions/by-page/{page_id}/review")
async def save_extraction_review(
    page_id: str,
    body: PageLlmExtractionReviewRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageLlmExtractionResponse:
    return PageLlmExtractionResponse.model_validate(
        await site_page_llm_extraction_service.save_review(db, ctx.site_id, page_id, body)
    )


@router.get("/site/page-llm-extractions/stats")
async def extraction_stats(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageLlmExtractionStatsResponse:
    return PageLlmExtractionStatsResponse(
        stats=await site_page_llm_extraction_service.stats(db, ctx.site_id)
    )


@router.get("/site/page-llm-extractions/by-page/{page_id}")
async def extraction_by_page(
    page_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageLlmExtractionResponse:
    return PageLlmExtractionResponse.model_validate(
        await site_page_llm_extraction_service.get_by_page(db, ctx.site_id, page_id)
    )


@router.get("/site/page-llm-extractions/{extraction_id}")
async def get_extraction(
    extraction_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageLlmExtractionResponse:
    return PageLlmExtractionResponse.model_validate(
        await site_page_llm_extraction_service.get(db, ctx.site_id, extraction_id)
    )


@router.delete("/site/page-llm-extractions/{extraction_id}")
async def delete_extraction(
    extraction_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageLlmExtractionDeleteResponse:
    await site_page_llm_extraction_service.delete(db, ctx.site_id, extraction_id)
    return PageLlmExtractionDeleteResponse(id=extraction_id)
