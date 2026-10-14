from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.user_prompts.models.user_prompts import UserPrompt
from src.user_prompts.schemas import (
    UserPromptChanges,
    UserPromptLabelKey,
    UserPromptListFilters,
    UserPromptNew,
    UserPromptRecord,
)


class UserPromptRepository:
    ID_PREFIX = "prompt"

    async def page(
        self,
        db: AsyncSession,
        site_id: str,
        filters: UserPromptListFilters,
        paging: PaginationParams,
    ) -> PaginatedApiResponse[UserPromptRecord]:
        query = (
            select(UserPrompt)
            .where(*self._conditions(site_id, filters))
            .order_by(UserPrompt.seq.asc())
        )
        return await PaginationService.paginate_query(
            db, query, paging.page, paging.page_size, UserPromptRecord
        )

    async def get(self, db: AsyncSession, site_id: str, prompt_id: str) -> UserPromptRecord | None:
        row = (
            await db.execute(
                select(UserPrompt).where(UserPrompt.site_id == site_id, UserPrompt.id == prompt_id)
            )
        ).scalar_one_or_none()
        return None if row is None else UserPromptRecord.model_validate(row)

    async def get_by_label(
        self, db: AsyncSession, key: UserPromptLabelKey
    ) -> UserPromptRecord | None:
        row = (
            await db.execute(
                select(UserPrompt).where(
                    UserPrompt.site_id == key.site_id,
                    UserPrompt.surface == key.surface,
                    UserPrompt.label == key.label,
                )
            )
        ).scalar_one_or_none()
        return None if row is None else UserPromptRecord.model_validate(row)

    async def create(self, db: AsyncSession, new: UserPromptNew) -> UserPromptRecord:
        now = datetime.now(UTC)
        row = UserPrompt(
            id=uid(self.ID_PREFIX),
            user_id=new.user_id,
            site_id=new.site_id,
            surface=new.surface,
            label=new.label,
            prompt=new.prompt,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.flush()
        return UserPromptRecord.model_validate(row)

    async def update(
        self, db: AsyncSession, prompt_id: str, changes: UserPromptChanges
    ) -> UserPromptRecord:
        row = (
            await db.execute(
                update(UserPrompt)
                .where(UserPrompt.id == prompt_id)
                .values(**changes.model_dump(exclude_none=True), updated_at=datetime.now(UTC))
                .returning(UserPrompt)
            )
        ).scalar_one()
        return UserPromptRecord.model_validate(row)

    async def delete(self, db: AsyncSession, prompt_id: str) -> None:
        await db.execute(delete(UserPrompt).where(UserPrompt.id == prompt_id))
        await db.flush()

    def _conditions(self, site_id: str, f: UserPromptListFilters) -> list[Any]:
        conds: list[Any] = [UserPrompt.site_id == site_id]
        if f.surface:
            conds.append(UserPrompt.surface == f.surface)
        if f.contains:
            pattern = f"%{f.contains}%"
            conds.append(UserPrompt.label.ilike(pattern) | UserPrompt.prompt.ilike(pattern))
        return conds


user_prompts = UserPromptRepository()
