from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.seo.keyword_content_pages.repository import seo_keyword_content_pages
from src.seo.keyword_content_pages.schemas import KeywordContentPageRecord
from src.seo.keyword_gsc_pages.repository import seo_keyword_gsc_pages
from src.seo.keyword_gsc_pages.schemas import KeywordGscPageRecord
from src.seo.keywords.repository import seo_keywords
from src.seo.keywords.schemas import KeywordFilter, KeywordRecord
from src.seo.precompute.embed import seo_embed_service
from src.seo.state.repository import seo_site_states

KEYWORD_NOT_FOUND = "No such keyword on this website."


class SeoKeywordService:
    async def list(
        self, db: AsyncSession, site_id: str, f: KeywordFilter, paging: PaginationParams
    ) -> PaginatedApiResponse[KeywordRecord]:
        return await seo_keywords.list(db, site_id, f, paging)

    async def get(self, db: AsyncSession, site_id: str, keyword_id: str) -> KeywordRecord:
        found = await seo_keywords.get(db, site_id, keyword_id)
        if found is None:
            raise HTTPException(404, KEYWORD_NOT_FOUND)
        return found

    async def pages(
        self, db: AsyncSession, site_id: str, keyword_id: str
    ) -> tuple[list[KeywordGscPageRecord], list[KeywordContentPageRecord]]:
        await self.get(db, site_id, keyword_id)
        return (
            await seo_keyword_gsc_pages.list_for_keyword(db, site_id, keyword_id),
            await seo_keyword_content_pages.list_for_keyword(db, site_id, keyword_id),
        )

    async def add(
        self, db: AsyncSession, user_id: str, site_id: str, keywords: list[str], source: str
    ) -> list[str]:
        await seo_site_states.ensure(db, user_id, site_id)
        await seo_keywords.insert_many(db, user_id, site_id, keywords, source)
        await seo_embed_service.embed_pending(db, user_id, site_id)
        ids = await seo_keywords.ids_for(db, site_id, keywords)
        return [ids[k] for k in keywords if k in ids]


seo_keyword_service = SeoKeywordService()
