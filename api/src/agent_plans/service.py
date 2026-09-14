from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent_plans import repository as repo
from src.agent_plans.library import BUILTIN_PLANS
from src.agent_plans.schemas import (
    AgentPlanCreateRequest,
    AgentPlanRecord,
    AgentPlanSyncResult,
    AgentPlanUpdateRequest,
)
from src.core.pagination import PaginatedApiResponse, PaginationParams


async def sync_builtins(db: AsyncSession) -> AgentPlanSyncResult:
    for slug, entry in BUILTIN_PLANS.items():
        await repo.upsert_builtin(db, slug, entry["question"], entry["plan"])
    pruned = await repo.prune_builtins(db, list(BUILTIN_PLANS))
    await db.commit()
    return AgentPlanSyncResult(synced=len(BUILTIN_PLANS), pruned=pruned)


async def _search(
    db: AsyncSession, user_id: str, query: str, paging: PaginationParams
) -> PaginatedApiResponse[AgentPlanRecord]:
    result = await repo.search_plans(
        db, user_id, func.websearch_to_tsquery("english", query), paging
    )
    if result.pagination.total > 0:
        return result
    words = [w for w in query.split() if len(w) > 2][:8]
    if not words:
        return result
    return await repo.search_plans(
        db, user_id, func.to_tsquery("english", " | ".join(words)), paging
    )


async def list_plans(
    db: AsyncSession, user_id: str, paging: PaginationParams, search: str | None = None
) -> PaginatedApiResponse[AgentPlanRecord]:
    if search:
        return await _search(db, user_id, search, paging)
    return await repo.list_plans(db, user_id, paging)


async def get_plan(db: AsyncSession, user_id: str, plan_id: str) -> AgentPlanRecord:
    record = await repo.get_plan(db, user_id, plan_id)
    if record is None:
        raise HTTPException(404, "Not found")
    return record


async def get_plan_by_slug(db: AsyncSession, user_id: str, slug: str) -> AgentPlanRecord:
    record = await repo.get_plan_by_slug(db, user_id, slug)
    if record is None:
        raise HTTPException(404, f"No plan {slug!r}.")
    return record


async def _ensure_slug_free(
    db: AsyncSession, user_id: str, slug: str, except_id: str | None
) -> None:
    other = await repo.get_plan_by_slug(db, user_id, slug)
    if other is not None and other.id != except_id:
        raise HTTPException(409, f'A plan with slug "{slug}" already exists.')


async def create_plan(
    db: AsyncSession, user_id: str, body: AgentPlanCreateRequest
) -> AgentPlanRecord:
    await _ensure_slug_free(db, user_id, body.slug, None)
    return await repo.create_plan(db, user_id, body.slug, body.question, body.plan)


def _ensure_owned(record: AgentPlanRecord, user_id: str) -> None:
    if record.user_id != user_id:
        raise HTTPException(403, "Built-in plans cannot be changed; create your own instead.")


async def update_plan(
    db: AsyncSession, user_id: str, plan_id: str, body: AgentPlanUpdateRequest
) -> AgentPlanRecord:
    record = await get_plan(db, user_id, plan_id)
    _ensure_owned(record, user_id)
    values = body.changes()
    if not values:
        raise HTTPException(400, "Nothing to update: give slug, question and/or plan.")
    if "slug" in values:
        await _ensure_slug_free(db, user_id, values["slug"], record.id)
    return await repo.update_plan(db, record.id, values)


async def delete_plan(db: AsyncSession, user_id: str, plan_id: str) -> AgentPlanRecord:
    record = await get_plan(db, user_id, plan_id)
    _ensure_owned(record, user_id)
    await repo.delete_plan(db, record.id)
    return record
