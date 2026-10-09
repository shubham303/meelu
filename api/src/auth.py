from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.schemas import EntityModel, RequestModel
from src.credits.service import credit_service
from src.identity.service import identity_service
from src.keys.repository import api_keys
from src.profile.repository import access_tokens, users
from src.profile.schemas import UserRecord
from src.settings import settings
from src.sites.repository import sites


def _session_cutoff() -> datetime:
    return datetime.now(UTC) - timedelta(seconds=settings.session_lifetime_seconds)


async def session_user(db: AsyncSession, token: str | None) -> UserRecord | None:
    if not token:
        return None
    user_id = await access_tokens.find_user_id(db, token, _session_cutoff())
    if user_id is None:
        return None
    user = await users.get(db, user_id)
    return user if user is not None and user.is_active else None


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=settings.session_lifetime_seconds,
        path="/",
        httponly=True,
        samesite="lax",
        secure=False,
    )


class SessionRequest(RequestModel):
    access_token: str


class UserResponse(EntityModel):
    id: str
    email: str
    name: str | None
    image: str | None


class SessionResponse(EntityModel):
    user: UserResponse
    created: bool


session_router = APIRouter()


@session_router.post("/session")
async def start_session(
    body: SessionRequest, response: Response, db: AsyncSession = Depends(get_db)
) -> SessionResponse:
    result = await identity_service.sign_in(db, body.access_token)
    await db.commit()
    _set_session_cookie(response, result.token)
    return SessionResponse(user=UserResponse.model_validate(result.user), created=result.created)


@session_router.post("/logout")
async def logout(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        await identity_service.sign_out(db, token)
        await db.commit()

    response = Response(status_code=204)
    response.delete_cookie(settings.session_cookie_name, path="/")
    return response


@session_router.get("/me")
async def me(request: Request, db: AsyncSession = Depends(get_db)) -> UserResponse:
    user = await session_user(db, request.cookies.get(settings.session_cookie_name))
    if user is None:
        raise HTTPException(401, "Not authenticated.")
    return UserResponse.model_validate(user)


async def current_user_id(request: Request, db: AsyncSession = Depends(get_db)) -> str:
    api_key = request.headers.get("x-api-key")
    if api_key:
        owner = await api_keys.find_owner(db, api_key)
        if owner:
            return owner.user_id
        raise HTTPException(401, "Invalid API key.")

    user = await session_user(db, request.cookies.get(settings.session_cookie_name))
    if user is not None:
        return user.id

    raise HTTPException(401, "Not authenticated. Sign in or pass an x-api-key header.")


@dataclass
class AuthContext:
    user_id: str
    site_id: str


@dataclass
class OptionalSiteContext:
    user_id: str
    site_id: str | None


async def _resolve_site(
    db: AsyncSession, request: Request, user_id: str, gated: bool = True
) -> str:
    header = request.headers.get("x-meelu-site")
    asked = header if header is not None else request.query_params.get("siteId")

    if asked:
        site = await sites.get(db, user_id, asked)
        if site:
            if gated:
                credit_service.require_active_site(site.id, site.status)
            return site.id
        raise HTTPException(404, f"No website {asked} in this workspace.")

    site = await sites.get_default(db, user_id)
    if site:
        if gated:
            credit_service.require_active_site(site.id, site.status)
        return site.id

    count = await sites.count(db, user_id)
    if count == 0:
        raise HTTPException(
            400,
            "No website in this workspace yet. Add one with POST /api/v1/sites — everything "
            "the agent does is argued from a website's own record.",
        )
    raise HTTPException(
        400,
        f"This workspace has {count} websites, so a request has to name one. Send the "
        f"x-meelu-site header (or ?siteId=) — GET /api/v1/sites lists them.",
    )


async def require_site(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
) -> AuthContext:
    return AuthContext(user_id=user_id, site_id=await _resolve_site(db, request, user_id))


async def any_site(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
) -> AuthContext:
    return AuthContext(
        user_id=user_id, site_id=await _resolve_site(db, request, user_id, gated=False)
    )


async def optional_site(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
) -> OptionalSiteContext:
    try:
        site_id = await _resolve_site(db, request, user_id, gated=False)
    except HTTPException:
        if await sites.count(db, user_id) == 0:
            return OptionalSiteContext(user_id=user_id, site_id=None)
        raise
    return OptionalSiteContext(user_id=user_id, site_id=site_id)


async def require_superuser(request: Request, db: AsyncSession = Depends(get_db)) -> str:
    api_key = request.headers.get("x-api-key")
    owner = await api_keys.find_owner(db, api_key) if api_key else None
    user = (
        await users.get(db, owner.user_id)
        if owner
        else await session_user(db, request.cookies.get(settings.session_cookie_name))
    )
    if user is None:
        raise HTTPException(401, "Not authenticated. Sign in or pass an x-api-key header.")
    if not user.is_superuser:
        raise HTTPException(403, "This endpoint is for Meelu operators only.")
    return user.id


def require(feature: str, operation: str) -> Callable[..., Coroutine[Any, Any, str]]:
    async def dependency(user_id: str = Depends(current_user_id)) -> str:
        return user_id

    return dependency
