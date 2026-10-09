from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.profile.models.profile import Profile
from src.profile.models.user import AccessToken, User
from src.profile.schemas import ProfileRecord, UserRecord


class ProfileRepository:
    ID_PREFIX = "prof"
    PROTECTED = frozenset({"id", "user_id", "created_at", "updated_at"})

    async def get(self, db: AsyncSession, user_id: str) -> ProfileRecord | None:
        row = await self._row(db, user_id)
        return None if row is None else ProfileRecord.model_validate(row)

    async def create(self, db: AsyncSession, user_id: str, values: dict[str, Any]) -> ProfileRecord:
        now = datetime.now(UTC)
        row = Profile(
            id=uid(self.ID_PREFIX),
            user_id=user_id,
            created_at=now,
            updated_at=now,
            **self._writable(values),
        )
        db.add(row)
        await db.flush()
        return ProfileRecord.model_validate(row)

    async def update(
        self, db: AsyncSession, user_id: str, values: dict[str, Any]
    ) -> ProfileRecord | None:
        row = await self._row(db, user_id)
        if row is None:
            return None
        for key, value in self._writable(values).items():
            setattr(row, key, value)
        row.updated_at = datetime.now(UTC)
        await db.flush()
        return ProfileRecord.model_validate(row)

    async def delete(self, db: AsyncSession, user_id: str) -> None:
        row = await self._row(db, user_id)
        if row is None:
            return
        await db.delete(row)
        await db.flush()

    async def _row(self, db: AsyncSession, user_id: str) -> Profile | None:
        result = await db.execute(select(Profile).where(Profile.user_id == user_id).limit(1))
        return result.scalar_one_or_none()

    def _writable(self, values: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in values.items() if k not in self.PROTECTED}


class UserRepository:
    ID_PREFIX = "user"

    async def get(self, db: AsyncSession, user_id: str) -> UserRecord | None:
        row = await db.get(User, user_id)
        return None if row is None else UserRecord.model_validate(row)

    async def find_by_email(self, db: AsyncSession, email: str) -> UserRecord | None:
        result = await db.execute(select(User).where(User.email == email).limit(1))
        row = result.scalar_one_or_none()
        return None if row is None else UserRecord.model_validate(row)

    async def find_by_auth_id(self, db: AsyncSession, auth_id: str) -> UserRecord | None:
        result = await db.execute(select(User).where(User.auth_id == auth_id).limit(1))
        row = result.scalar_one_or_none()
        return None if row is None else UserRecord.model_validate(row)

    async def create(
        self,
        db: AsyncSession,
        auth_id: str,
        email: str,
        name: str,
        image: str | None,
        is_verified: bool,
    ) -> UserRecord:
        row = User(
            id=uid(self.ID_PREFIX),
            auth_id=auth_id,
            email=email,
            name=name,
            image=image,
            is_active=True,
            is_superuser=False,
            is_verified=is_verified,
        )
        db.add(row)
        await db.flush()
        return UserRecord.model_validate(row)

    async def update(self, db: AsyncSession, user_id: str, values: dict[str, Any]) -> UserRecord:
        row = await db.get(User, user_id)
        for key, value in values.items():
            setattr(row, key, value)
        row.updated_at = datetime.now(UTC)
        await db.flush()
        return UserRecord.model_validate(row)


class AccessTokenRepository:
    async def create(self, db: AsyncSession, user_id: str, token: str) -> None:
        db.add(AccessToken(token=token, user_id=user_id))
        await db.flush()

    async def find_user_id(
        self, db: AsyncSession, token: str, created_after: datetime
    ) -> str | None:
        result = await db.execute(
            select(AccessToken.user_id).where(
                AccessToken.token == token, AccessToken.created_at > created_after
            )
        )
        return result.scalar_one_or_none()

    async def delete(self, db: AsyncSession, token: str) -> None:
        await db.execute(delete(AccessToken).where(AccessToken.token == token))


profiles = ProfileRepository()
users = UserRepository()
access_tokens = AccessTokenRepository()
