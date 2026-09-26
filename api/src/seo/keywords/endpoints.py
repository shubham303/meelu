from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.core.schemas import EntityModel
from src.seo.keyword_content_pages.schemas import KeywordContentPageRecord
from src.seo.keyword_gsc_pages.schemas import KeywordGscPageRecord
from src.seo.keywords.schemas import KeywordFilter, KeywordRecord
from src.seo.keywords.service import seo_keyword_service

router = APIRouter()


class KeywordPagesResponse(EntityModel):
    gsc: list[KeywordGscPageRecord]
    content: list[KeywordContentPageRecord]


def keyword_filter(
    source: str | None = Query(None),
    cluster_id: str | None = Query(None, alias="clusterId"),
    branded: bool | None = Query(None),
    has_facts: bool | None = Query(None, alias="hasFacts"),
    search: str | None = Query(None),
) -> KeywordFilter:
    return KeywordFilter(
        source=source or None,
        cluster_id=cluster_id or None,
        branded=branded,
        has_facts=has_facts,
        search=(search or "").strip() or None,
    )


@router.get("/keywords")
async def list_keywords(
    f: KeywordFilter = Depends(keyword_filter),
    paging: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> PaginatedApiResponse[KeywordRecord]:
    return await seo_keyword_service.list(db, ctx.site_id, f, paging)


@router.get("/keywords/{keyword_id}")
async def get_keyword(
    keyword_id: str, db: AsyncSession = Depends(get_db), ctx: AuthContext = Depends(require_site)
) -> KeywordRecord:
    return await seo_keyword_service.get(db, ctx.site_id, keyword_id)


@router.get("/keywords/{keyword_id}/pages")
async def keyword_pages(
    keyword_id: str, db: AsyncSession = Depends(get_db), ctx: AuthContext = Depends(require_site)
) -> KeywordPagesResponse:
    gsc, content = await seo_keyword_service.pages(db, ctx.site_id, keyword_id)
    return KeywordPagesResponse(gsc=gsc, content=content)
