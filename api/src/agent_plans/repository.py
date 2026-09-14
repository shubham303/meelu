from datetime import UTC, datetime

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent_plans.models.agent_plan import AgentPlan
from src.agent_plans.schemas import AgentPlanRecord
from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService


def _visible(user_id: str):
    return or_(AgentPlan.user_id.is_(None), AgentPlan.user_id == user_id)


async def get_plan(db: AsyncSession, user_id: str, plan_id: str) -> AgentPlanRecord | None:
    row = (
        await db.execute(select(AgentPlan).where(AgentPlan.id == plan_id, _visible(user_id)))
    ).scalar_one_or_none()
    return None if row is None else AgentPlanRecord.model_validate(row)


async def get_plan_by_slug(db: AsyncSession, user_id: str, slug: str) -> AgentPlanRecord | None:
    row = (
        await db.execute(
            select(AgentPlan)
            .where(AgentPlan.slug == slug, _visible(user_id))
            .order_by(AgentPlan.user_id.desc().nulls_last())
            .limit(1)
        )
    ).scalar_one_or_none()
    return None if row is None else AgentPlanRecord.model_validate(row)


async def list_plans(
    db: AsyncSession, user_id: str, paging: PaginationParams
) -> PaginatedApiResponse[AgentPlanRecord]:
    query = select(AgentPlan).where(_visible(user_id)).order_by(AgentPlan.slug)
    return await PaginationService.paginate_query(
        db, query, paging.page, paging.page_size, AgentPlanRecord
    )


async def search_plans(
    db: AsyncSession, user_id: str, tsquery, paging: PaginationParams
) -> PaginatedApiResponse[AgentPlanRecord]:
    query = (
        select(AgentPlan)
        .where(AgentPlan.tsv.op("@@")(tsquery), _visible(user_id))
        .order_by(func.ts_rank(AgentPlan.tsv, tsquery).desc(), AgentPlan.slug)
    )
    return await PaginationService.paginate_query(
        db, query, paging.page, paging.page_size, AgentPlanRecord
    )


async def create_plan(
    db: AsyncSession, user_id: str, slug: str, question: str, plan: str
) -> AgentPlanRecord:
    now = datetime.now(UTC)
    row = AgentPlan(
        id=uid("plan"),
        user_id=user_id,
        slug=slug,
        question=question,
        plan=plan,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.flush()
    return AgentPlanRecord.model_validate(row)


async def update_plan(db: AsyncSession, plan_id: str, values: dict[str, str]) -> AgentPlanRecord:
    row = (
        await db.execute(
            update(AgentPlan)
            .where(AgentPlan.id == plan_id)
            .values(**values, updated_at=datetime.now(UTC))
            .returning(AgentPlan)
        )
    ).scalar_one()
    return AgentPlanRecord.model_validate(row)


async def delete_plan(db: AsyncSession, plan_id: str) -> None:
    await db.execute(delete(AgentPlan).where(AgentPlan.id == plan_id))
    await db.flush()


async def upsert_builtin(db: AsyncSession, slug: str, question: str, plan: str) -> None:
    now = datetime.now(UTC)
    stmt = insert(AgentPlan).values(
        id=uid("plan"),
        user_id=None,
        slug=slug,
        question=question,
        plan=plan,
        created_at=now,
        updated_at=now,
    )
    await db.execute(
        stmt.on_conflict_do_update(
            index_elements=[AgentPlan.slug],
            index_where=AgentPlan.user_id.is_(None),
            set_={
                "question": stmt.excluded.question,
                "plan": stmt.excluded.plan,
                "updated_at": now,
            },
        )
    )
    await db.flush()


async def prune_builtins(db: AsyncSession, keep: list[str]) -> int:
    result = await db.execute(
        delete(AgentPlan).where(AgentPlan.user_id.is_(None), AgentPlan.slug.not_in(keep))
    )
    await db.flush()
    return result.rowcount
