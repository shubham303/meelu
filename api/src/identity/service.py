import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.credits.service import credit_service
from src.identity import better_auth
from src.keys.repository import api_keys, hash_key
from src.profile.repository import access_tokens, profiles, users
from src.profile.schemas import UserRecord
from src.settings import settings

log = get_logger()


@dataclass(frozen=True)
class SignIn:
    user: UserRecord
    token: str
    created: bool


class IdentityService:
    async def sign_in(self, db: AsyncSession, access_token: str) -> SignIn:
        try:
            identity = await better_auth.verify_token(access_token)
        except better_auth.AuthTokenError as e:
            raise HTTPException(401, str(e)) from e
        except better_auth.AuthUnavailableError as e:
            raise HTTPException(503, str(e)) from e

        user, created = await self._resolve_user(db, identity)
        if not user.is_active:
            raise HTTPException(403, "This account is disabled.")

        token = secrets.token_urlsafe(32)
        await access_tokens.create(db, user.id, hash_key(token))
        return SignIn(user=user, token=token, created=created)

    async def revoke_all_sessions(self, db: AsyncSession, access_token: str) -> int:
        try:
            identity = await better_auth.verify_token(access_token)
        except better_auth.AuthTokenError as e:
            raise HTTPException(401, str(e)) from e
        except better_auth.AuthUnavailableError as e:
            raise HTTPException(503, str(e)) from e
        user = await users.find_by_auth_id(db, identity.id)
        if user is None:
            return 0
        return await access_tokens.delete_for_user(db, user.id)

    async def _resolve_user(
        self, db: AsyncSession, identity: better_auth.AuthIdentity
    ) -> tuple[UserRecord, bool]:
        if not identity.email_verified:
            raise HTTPException(403, "Confirm your email address before signing in.")
        user = await users.find_by_auth_id(db, identity.id)
        if user is not None:
            return await self._refresh(db, user, identity), False

        user = await users.find_by_email(db, identity.email)
        if user is not None:
            if user.auth_id is not None:
                raise HTTPException(409, "This email is linked to a different sign-in.")
            return await self._refresh(db, user, identity, link=True), False

        user = await users.create(
            db,
            auth_id=identity.id,
            email=identity.email,
            name=identity.name,
            image=identity.image,
            is_verified=identity.email_verified,
        )
        await self._seed(db, user)
        return user, True

    async def _refresh(
        self,
        db: AsyncSession,
        user: UserRecord,
        identity: better_auth.AuthIdentity,
        link: bool = False,
    ) -> UserRecord:
        changes: dict = {}
        if link:
            changes["auth_id"] = identity.id
        if identity.email_verified and not user.is_verified:
            changes["is_verified"] = True
        if identity.image and not user.image:
            changes["image"] = identity.image
        if identity.name and not user.name:
            changes["name"] = identity.name
        return await users.update(db, user.id, changes) if changes else user

    async def _seed(self, db: AsyncSession, user: UserRecord) -> None:
        await api_keys.create(db, user.id, "Default MCP key")
        await credit_service.open_account(db, user.id)
        try:
            await profiles.create(db, user.id, {"full_name": user.name})
        except Exception as e:
            log.error("identity.signup.profile_seed_failed", user_id=user.id, error=str(e))

    async def sign_out(self, db: AsyncSession, token: str) -> None:
        await access_tokens.delete(db, hash_key(token))

    async def purge_expired_sessions(self, db: AsyncSession) -> int:
        cutoff = datetime.now(UTC) - timedelta(seconds=settings.session_lifetime_seconds)
        return await access_tokens.delete_created_before(db, cutoff)


identity_service = IdentityService()
