from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.seo.common import fields
from src.seo.page_suggestions.schemas import (
    CreateResult,
    PageSuggestionFilter,
    PageSuggestionRecord,
    SavePageSuggestionRequest,
)
from src.seo.page_suggestions.service import seo_page_suggestion_service

router = APIRouter()


def suggestion_filter(
    state: str | None = Query("ready"),
    action: str | None = Query(None),
    job_id: str | None = Query(None, alias="jobId"),
    page_id: str | None = Query(None, alias="pageId"),
    topic_key: str | None = Query(None, alias="topicKey"),
) -> PageSuggestionFilter:
    return PageSuggestionFilter(
        state=None if fields.blank(state) or state == "any" else fields.state(state),
        action=None if fields.blank(action) else fields.action(action),
        job_id=job_id or None,
        page_id=page_id or None,
        topic_key=topic_key or None,
    )


@router.get("/page-suggestions")
async def list_suggestions(
    f: PageSuggestionFilter = Depends(suggestion_filter),
    paging: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PaginatedApiResponse[PageSuggestionRecord]:
    return await seo_page_suggestion_service.list(db, ctx.site_id, f, paging)


@router.post("/page-suggestions", status_code=201)
async def save_suggestion(
    body: SavePageSuggestionRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CreateResult:
    return await seo_page_suggestion_service.save(db, ctx.user_id, ctx.site_id, body)


@router.get("/page-suggestions/{suggestion_id}")
async def get_suggestion(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageSuggestionRecord:
    return await seo_page_suggestion_service.get(db, ctx.site_id, suggestion_id)


@router.post("/page-suggestions/{suggestion_id}/reject")
async def reject_suggestion(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageSuggestionRecord:
    return await seo_page_suggestion_service.settle(db, ctx.site_id, suggestion_id, "user_rejected")


@router.post("/page-suggestions/{suggestion_id}/done")
async def done_suggestion(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PageSuggestionRecord:
    return await seo_page_suggestion_service.settle(db, ctx.site_id, suggestion_id, "done")
