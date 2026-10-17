from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.providers.registry import Caller
from src.seo.search_suggestions.schemas import SearchSuggestions, SearchSuggestionsRequest
from src.seo.search_suggestions.service import search_suggestions_service
from src.sites.service import site_service

router = APIRouter()


@router.post("/site/seo/search-suggestions")
async def search_suggestions(
    body: SearchSuggestionsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> list[SearchSuggestions]:
    site = await site_service.get(db, ctx.user_id, ctx.site_id)
    return await search_suggestions_service.suggestions(
        Caller(user_id=ctx.user_id, site_id=ctx.site_id), site, body
    )
