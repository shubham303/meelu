from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.seo.pipeline.schemas import (
    RankRequest,
    RankResult,
    ScreenRequest,
    ScreenResult,
)
from src.seo.pipeline.service import seo_pipeline_service


@tool(writes=True, desk="seo")
async def screen_page_suggestions(
    job_id: str, ids: list[str] | None = None, question: str | None = None, limit: int = 200
) -> ScreenResult:
    """Run the cheap screening model over the job's draft suggestions; a confident no
    becomes llm_rejected, the rest stay draft for review_page_suggestions."""
    ctx = require_site()
    async with unit_of_work() as db:
        return await seo_pipeline_service.screen(
            db,
            ctx.user_id,
            ctx.site_id,
            ScreenRequest(job_id=job_id, ids=ids, question=question, limit=limit),
        )


@tool(writes=True, desk="seo")
async def rank_page_suggestions(
    job_id: str, budget_add: int = 10, budget_edit: int = 20, budget_delete: int = 5
) -> RankResult:
    """Score the job's reviewed rows per action and keep the budget as ready; the rest
    become llm_rejected. A cannibalisation pair counts once against budget_delete."""
    ctx = require_site()
    async with unit_of_work() as db:
        return await seo_pipeline_service.rank(
            db,
            ctx.site_id,
            RankRequest(
                job_id=job_id,
                budget_add=budget_add,
                budget_edit=budget_edit,
                budget_delete=budget_delete,
            ),
        )
