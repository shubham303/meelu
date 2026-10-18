from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import require
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.providers.json_data_extractor.service import json_data_extractor
from src.providers.people_search.service import people_search
from src.providers.schemas import DomainStatus, ProviderCallResponse
from src.providers.seo_data.service import seo_data
from src.providers.service import provider_call_service
from src.providers.social_search.service import social_search

router = APIRouter()

FACADES = (seo_data, social_search, people_search, json_data_extractor)


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
