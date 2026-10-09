from fastapi import APIRouter, Depends, Query
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import OptionalSiteContext, optional_site, require
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.core.schemas import RequestModel
from src.providers.json_data_extractor.service import json_data_extractor
from src.providers.registry import Caller
from src.providers.schemas import DomainStatus, ProviderCallResponse
from src.providers.seo_data.service import seo_data
from src.providers.service import provider_call_service
from src.providers.social_search.service import social_search

router = APIRouter()

FACADES = (seo_data, social_search, json_data_extractor)


class SocialSearchRequest(RequestModel):
    platform: str
    keywords: list[str]
    since: str | None = None
    limit: int = Field(default=30, ge=1, le=100)


def caller_of(ctx: OptionalSiteContext) -> Caller:
    return Caller(user_id=ctx.user_id, site_id=ctx.site_id)


@router.get("/providers/status")
async def providers_status(
    user_id: str = Depends(require("providers", "read")),
) -> list[DomainStatus]:
    return [f.status() for f in FACADES]


@router.get("/providers/calls")
async def list_calls(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("providers", "read")),
    paging: PaginationParams = Depends(get_pagination_params),
    domain: str | None = Query(default=None),
) -> PaginatedApiResponse[ProviderCallResponse]:
    return await provider_call_service.list(db, user_id, paging, domain)


@router.get("/providers/social-listening/platforms")
async def social_platforms(user_id: str = Depends(require("providers", "read"))) -> dict:
    return {"platforms": social_search.available_platforms()}


@router.post("/providers/social-listening/search")
async def social_search_posts(
    body: SocialSearchRequest,
    db: AsyncSession = Depends(get_db),
    ctx: OptionalSiteContext = Depends(optional_site),
) -> dict:
    posts = await social_search.search_platform(
        db, caller_of(ctx), body.platform, body.keywords, body.since, body.limit
    )
    return {"posts": posts}
