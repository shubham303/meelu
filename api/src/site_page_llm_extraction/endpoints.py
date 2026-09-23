from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.site_page_llm_extraction import service
from src.site_page_llm_extraction.schemas import (
    PageLlmExtractionCreateRequest,
    PageLlmExtractionDeleteResponse,
    PageLlmExtractionListQuery,
    PageLlmExtractionListResponse,
    PageLlmExtractionResponse,
    PageLlmExtractionRunResponse,
    PageLlmExtractionStatsResponse,
)

router = APIRouter()


@router.get("/site/page-llm-extractions")
async def list_extractions(
    q: Annotated[PageLlmExtractionListQuery, Query()],
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageLlmExtractionListResponse:
    result = await service.list_extractions(db, ctx.site_id, q.page_type, q.paging())
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
        await service.save(db, ctx.user_id, ctx.site_id, body)
    )


@router.get("/site/page-llm-extractions/stats")
async def extraction_stats(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageLlmExtractionStatsResponse:
    return PageLlmExtractionStatsResponse(stats=await service.stats(db, ctx.site_id))


@router.post("/site/page-llm-extractions/run")
async def run_extraction(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageLlmExtractionRunResponse:
    return await service.run(db, ctx.user_id, ctx.site_id)


@router.get("/site/page-llm-extractions/by-page/{page_id}")
async def extraction_by_page(
    page_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageLlmExtractionResponse:
    return PageLlmExtractionResponse.model_validate(
        await service.get_by_page(db, ctx.site_id, page_id)
    )


@router.get("/site/page-llm-extractions/{extraction_id}")
async def get_extraction(
    extraction_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageLlmExtractionResponse:
    return PageLlmExtractionResponse.model_validate(
        await service.get(db, ctx.site_id, extraction_id)
    )


@router.delete("/site/page-llm-extractions/{extraction_id}")
async def delete_extraction(
    extraction_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageLlmExtractionDeleteResponse:
    await service.delete(db, ctx.site_id, extraction_id)
    return PageLlmExtractionDeleteResponse(id=extraction_id)
