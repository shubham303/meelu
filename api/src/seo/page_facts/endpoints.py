from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.seo.keyword_gsc_pages.schemas import KeywordGscPageRecord
from src.seo.page_facts.schemas import PageFactsRecord
from src.seo.page_facts.service import seo_page_facts_service

router = APIRouter()


@router.get("/pages")
async def list_page_facts(
    live: bool | None = Query(None),
    paging: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PaginatedApiResponse[PageFactsRecord]:
    return await seo_page_facts_service.list(db, ctx.site_id, paging, live)


@router.get("/pages/{page_id}/keywords")
async def page_keywords(
    page_id: str,
    paging: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PaginatedApiResponse[KeywordGscPageRecord]:
    return await seo_page_facts_service.keywords(db, ctx.site_id, page_id, paging)
