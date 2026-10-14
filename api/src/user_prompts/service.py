from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.user_prompts.repository import user_prompts
from src.user_prompts.schemas import (
    UserPromptChanges,
    UserPromptCreateRequest,
    UserPromptLabelKey,
    UserPromptListFilters,
    UserPromptNew,
    UserPromptRecord,
    UserPromptUpdateRequest,
)


class UserPromptService:
    async def list_prompts(
        self,
        db: AsyncSession,
        site_id: str,
        filters: UserPromptListFilters,
        paging: PaginationParams,
    ) -> PaginatedApiResponse[UserPromptRecord]:
        return await user_prompts.page(db, site_id, filters, paging)

    async def get_prompt(self, db: AsyncSession, site_id: str, prompt_id: str) -> UserPromptRecord:
        record = await user_prompts.get(db, site_id, prompt_id)
        if record is None:
            raise HTTPException(404, "Not found")
        return record

    async def create_prompt(
        self, db: AsyncSession, user_id: str, site_id: str, body: UserPromptCreateRequest
    ) -> UserPromptRecord:
        key = UserPromptLabelKey(site_id=site_id, surface=body.surface, label=body.label)
        await self._require_free_label(db, key, None)
        return await user_prompts.create(
            db,
            UserPromptNew(
                user_id=user_id,
                site_id=site_id,
                surface=body.surface,
                label=body.label,
                prompt=body.prompt,
            ),
        )

    async def update_prompt(
        self, db: AsyncSession, site_id: str, prompt_id: str, body: UserPromptUpdateRequest
    ) -> UserPromptRecord:
        existing = await self.get_prompt(db, site_id, prompt_id)
        changes = UserPromptChanges(label=body.label, prompt=body.prompt)
        if changes.is_empty():
            raise HTTPException(400, "Nothing to save.")
        if changes.label is not None and changes.label != existing.label:
            key = UserPromptLabelKey(
                site_id=site_id, surface=existing.surface, label=changes.label
            )
            await self._require_free_label(db, key, existing.id)
        return await user_prompts.update(db, existing.id, changes)

    async def delete_prompt(
        self, db: AsyncSession, site_id: str, prompt_id: str
    ) -> UserPromptRecord:
        record = await self.get_prompt(db, site_id, prompt_id)
        await user_prompts.delete(db, record.id)
        return record

    async def _require_free_label(
        self, db: AsyncSession, key: UserPromptLabelKey, own_id: str | None
    ) -> None:
        clash = await user_prompts.get_by_label(db, key)
        if clash is not None and clash.id != own_id:
            raise HTTPException(409, f'A saved prompt named "{key.label}" already exists here.')


user_prompt_service = UserPromptService()
