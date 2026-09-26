from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent_plans.library import BUILTIN_PLANS
from src.agent_plans.repository import agent_plans
from src.agent_plans.schemas import (
    AgentPlanCreateRequest,
    AgentPlanRecord,
    AgentPlanSyncResult,
    AgentPlanUpdateRequest,
)
from src.core.pagination import PaginatedApiResponse, PaginationParams


class AgentPlanService:
    async def sync_builtins(self, db: AsyncSession) -> AgentPlanSyncResult:
        for slug, entry in BUILTIN_PLANS.items():
            await agent_plans.upsert_builtin(db, slug, entry["question"], entry["plan"])
        pruned = await agent_plans.prune_builtins(db, list(BUILTIN_PLANS))
        return AgentPlanSyncResult(synced=len(BUILTIN_PLANS), pruned=pruned)

    async def list_plans(
        self,
        db: AsyncSession,
        user_id: str,
        paging: PaginationParams,
        search: str | None = None,
    ) -> PaginatedApiResponse[AgentPlanRecord]:
        if search:
            return await self._search(db, user_id, search, paging)
        return await agent_plans.page(db, user_id, paging)

    async def get_plan(self, db: AsyncSession, user_id: str, plan_id: str) -> AgentPlanRecord:
        record = await agent_plans.get(db, user_id, plan_id)
        if record is None:
            raise HTTPException(404, "Not found")
        return record

    async def get_plan_by_slug(self, db: AsyncSession, user_id: str, slug: str) -> AgentPlanRecord:
        record = await agent_plans.get_by_slug(db, user_id, slug)
        if record is None:
            raise HTTPException(404, f"No plan {slug!r}.")
        return record

    async def create_plan(
        self, db: AsyncSession, user_id: str, body: AgentPlanCreateRequest
    ) -> AgentPlanRecord:
        await self._ensure_slug_free(db, user_id, body.slug, None)
        return await agent_plans.create(db, user_id, body.slug, body.question, body.plan)

    async def update_plan(
        self, db: AsyncSession, user_id: str, plan_id: str, body: AgentPlanUpdateRequest
    ) -> AgentPlanRecord:
        record = await self.get_plan(db, user_id, plan_id)
        self._ensure_owned(record, user_id)
        values = body.changes()
        if not values:
            raise HTTPException(400, "Nothing to update: give slug, question and/or plan.")
        if "slug" in values:
            await self._ensure_slug_free(db, user_id, values["slug"], record.id)
        return await agent_plans.update(db, record.id, values)

    async def delete_plan(self, db: AsyncSession, user_id: str, plan_id: str) -> AgentPlanRecord:
        record = await self.get_plan(db, user_id, plan_id)
        self._ensure_owned(record, user_id)
        await agent_plans.delete(db, record.id)
        return record

    async def _search(
        self, db: AsyncSession, user_id: str, query: str, paging: PaginationParams
    ) -> PaginatedApiResponse[AgentPlanRecord]:
        result = await agent_plans.search(db, user_id, query, paging)
        if result.pagination.total > 0:
            return result
        words = [w for w in query.split() if len(w) > 2][:8]
        if not words:
            return result
        return await agent_plans.search_any_words(db, user_id, words, paging)

    async def _ensure_slug_free(
        self, db: AsyncSession, user_id: str, slug: str, except_id: str | None
    ) -> None:
        other = await agent_plans.get_by_slug(db, user_id, slug)
        if other is not None and other.id != except_id:
            raise HTTPException(409, f'A plan with slug "{slug}" already exists.')

    def _ensure_owned(self, record: AgentPlanRecord, user_id: str) -> None:
        if record.user_id != user_id:
            raise HTTPException(403, "Built-in plans cannot be changed; create your own instead.")


agent_plan_service = AgentPlanService()
