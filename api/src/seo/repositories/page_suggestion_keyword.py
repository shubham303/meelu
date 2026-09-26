from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.seo.models.page_suggestion import SeoPageSuggestionKeyword


class SeoPageSuggestionKeywordRepository:
    async def replace(self, db: AsyncSession, suggestion_id: str, keyword_ids: list[str]) -> None:
        await db.execute(
            delete(SeoPageSuggestionKeyword).where(
                SeoPageSuggestionKeyword.suggestion_id == suggestion_id
            )
        )
        if keyword_ids:
            await db.execute(
                insert(SeoPageSuggestionKeyword)
                .values(
                    [{"suggestion_id": suggestion_id, "keyword_id": k} for k in set(keyword_ids)]
                )
                .on_conflict_do_nothing()
            )

    async def keyword_ids(self, db: AsyncSession, suggestion_id: str) -> list[str]:
        rows = await db.execute(
            select(SeoPageSuggestionKeyword.keyword_id).where(
                SeoPageSuggestionKeyword.suggestion_id == suggestion_id
            )
        )
        return list(rows.scalars().all())


seo_page_suggestion_keywords = SeoPageSuggestionKeywordRepository()
