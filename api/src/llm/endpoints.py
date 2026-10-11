import json
from typing import get_args

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import current_user_id
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.llm.schemas import (
    LlmCallResponse,
    LlmModelResponse,
    LlmPreferenceResponse,
    LlmPreferenceUpdateRequest,
    Purpose,
)
from src.llm.service import anthropic_error, llm_service
from src.sites.repository import sites

router = APIRouter()

MESSAGES_PATH = "/llm/v1/messages"
PURPOSES = frozenset(get_args(Purpose))


@router.get("/llm/models")
async def list_models(user_id: str = Depends(current_user_id)) -> list[LlmModelResponse]:
    return await llm_service.models()


@router.get("/llm/preference")
async def get_preference(
    db: AsyncSession = Depends(get_db), user_id: str = Depends(current_user_id)
) -> LlmPreferenceResponse:
    return await llm_service.preference(db, user_id)


@router.put("/llm/preference")
async def update_preference(
    body: LlmPreferenceUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
) -> LlmPreferenceResponse:
    return await llm_service.set_preference(db, user_id, body)


@router.get("/llm/calls")
async def list_calls(
    model: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[LlmCallResponse]:
    return await llm_service.list_calls(db, user_id, model, paging)


@router.post(MESSAGES_PATH)
async def create_message(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
) -> Response:
    site_id = request.headers.get("x-meelu-site") or None
    if site_id and await sites.get(db, user_id, site_id) is None:
        return anthropic_error(404, "not_found_error", f"No website {site_id} in this workspace.")
    purpose = request.headers.get("x-meelu-purpose") or "agent"
    if purpose not in PURPOSES:
        return anthropic_error(400, "invalid_request_error", f"Unknown purpose {purpose}.")
    try:
        body = json.loads(await request.body())
    except ValueError:
        return anthropic_error(400, "invalid_request_error", "The body must be JSON.")
    if not isinstance(body, dict):
        return anthropic_error(400, "invalid_request_error", "The body must be a JSON object.")
    return await llm_service.messages(db, user_id, site_id, purpose, dict(request.headers), body)
