import secrets
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pwdlib import PasswordHash
from pydantic import field_validator
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.ids import uid
from src.core.logging import get_logger
from src.core.schemas import EntityModel, RequestModel
from src.credits import service as credits_service
from src.keys.repository import create_key, find_user_by_api_key
from src.profile.models.user import AccessToken, User
from src.profile.repository import create_profile
from src.settings import settings
from src.sites import repository as sites_repository

log = get_logger("auth")

password_hash = PasswordHash.recommended()
_dummy_hash = password_hash.hash(secrets.token_urlsafe(16))


def _session_cutoff() -> datetime:
    return datetime.now(UTC) - timedelta(seconds=settings.session_lifetime_seconds)


async def session_user(db: AsyncSession, token: str | None) -> User | None:
    if not token:
        return None
    result = await db.execute(
        select(User)
        .join(AccessToken, AccessToken.user_id == User.id)
        .where(
            AccessToken.token == token,
            AccessToken.created_at > _session_cutoff(),
            User.is_active,
        )
    )
    return result.scalar_one_or_none()


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


class RegisterRequest(RequestModel):
    email: str
    password: str
    name: str = ""

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        email = v.strip()
        if not email:
            raise ValueError("email is required.")
        return email

    @field_validator("password")
    @classmethod
    def _validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password should be at least 6 characters long.")
        return v


class LoginRequest(RequestModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _validate_email(cls, v: str) -> str:
        return v.strip()


class UserResponse(EntityModel):
    id: str
    email: str
    name: str | None
    image: str | None


session_router = APIRouter()


@session_router.post("/register", status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)) -> UserResponse:
    existing = await db.execute(select(User.id).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(400, "An account with this email already exists.")

    user = User(
        id=uid("user"),
        email=body.email,
        hashed_password=password_hash.hash(body.password),
        name=body.name,
        is_active=True,
        is_superuser=False,
        is_verified=False,
    )
    db.add(user)
    await db.flush()

    await create_key(db, user.id, "Default MCP key")
    await credits_service.signup_grant(db, user.id)
    try:
        await create_profile(db, user.id, {"full_name": user.name})
    except Exception as e:
        log.error("seed_profile_failed", user_id=user.id, error=str(e))
    await db.commit()

    return UserResponse.model_validate(user)


@session_router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)) -> Response:
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    hashed = user.hashed_password if user else _dummy_hash
    if not password_hash.verify(body.password, hashed) or user is None or not user.is_active:
        raise HTTPException(400, "Wrong email or password.")

    token = secrets.token_urlsafe(32)
    db.add(AccessToken(token=token, user_id=user.id))
    await db.commit()

    response = Response(status_code=204)
    _set_session_cookie(response, token)
    return response


@session_router.post("/logout")
async def logout(request: Request, db: AsyncSession = Depends(get_db)) -> Response:
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        await db.execute(delete(AccessToken).where(AccessToken.token == token))
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
        owner = await find_user_by_api_key(db, api_key)
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


async def _resolve_site(db: AsyncSession, request: Request, user_id: str) -> str:
    header = request.headers.get("x-meelu-site")
    asked = header if header is not None else request.query_params.get("siteId")

    if asked:
        if await sites_repository.get_site(db, user_id, asked):
            return asked
        raise HTTPException(404, f"No website {asked} in this workspace.")

    only = await sites_repository.default_site_id(db, user_id)
    if only:
        return only

    count = await sites_repository.count_sites(db, user_id)
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


async def optional_site(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
) -> OptionalSiteContext:
    try:
        site_id = await _resolve_site(db, request, user_id)
    except HTTPException:
        if await sites_repository.count_sites(db, user_id) == 0:
            return OptionalSiteContext(user_id=user_id, site_id=None)
        raise
    return OptionalSiteContext(user_id=user_id, site_id=site_id)


def require(feature: str, operation: str) -> Callable[..., Coroutine[Any, Any, str]]:
    async def dependency(user_id: str = Depends(current_user_id)) -> str:
        return user_id

    return dependency
