from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.seo.keyword_gsc_pages.repository import seo_keyword_gsc_pages
from src.seo.keyword_gsc_pages.schemas import KeywordGscPageRecord
from src.seo.page_facts.repository import seo_page_facts
from src.seo.page_facts.schemas import PageFactsRecord


class SeoPageFactsService:
    async def list(
        self, db: AsyncSession, site_id: str, paging: PaginationParams, live: bool | None
    ) -> PaginatedApiResponse[PageFactsRecord]:
        return await seo_page_facts.list(db, site_id, paging, live)

    async def keywords(
        self, db: AsyncSession, site_id: str, page_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[KeywordGscPageRecord]:
        return await seo_keyword_gsc_pages.list_for_page(db, site_id, page_id, paging)


seo_page_facts_service = SeoPageFactsService()
