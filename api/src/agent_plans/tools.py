from src.agent.context import current
from src.agent.server import tool
from src.agent_plans.service import agent_plan_service
from src.agent_plans.schemas import (
    AgentPlanFindResponse,
    AgentPlanMatchResponse,
    AgentPlanPlanResponse,
)
from src.core.database import unit_of_work
from src.core.pagination import PaginationParams

FIND_PAGE_SIZE = 5


@tool()
async def find_plans(query: str) -> AgentPlanFindResponse:
    """Search the library of vetted query plans for anticipated questions; returns
    matching questions only. Call this before designing SQL from the bare schema,
    then fetch a match with get_plan."""
    ctx = current()
    async with unit_of_work() as db:
        page = await agent_plan_service.list_plans(
            db, ctx.user_id, PaginationParams(page_size=FIND_PAGE_SIZE), search=query
        )
    matches = [AgentPlanMatchResponse.model_validate(h) for h in page.data]
    return AgentPlanFindResponse(matches=matches, n=len(matches))


@tool()
async def get_plan(slug: str) -> AgentPlanPlanResponse:
    """Fetch one query plan by slug (from find_plans): the question it answers and
    the step-by-step plan with SQL to adapt."""
    ctx = current()
    async with unit_of_work() as db:
        record = await agent_plan_service.get_plan_by_slug(db, ctx.user_id, slug)
    return AgentPlanPlanResponse.model_validate(record)
