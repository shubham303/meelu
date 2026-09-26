from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.core.schemas import EntityModel
from src.site_structure.constants import PILLAR_BUDGET, PILLAR_MIN_COHESION, PILLAR_MIN_SIZE
from src.site_structure.pillars.schemas import (
    PillarPageSuggestionCreateRequest,
    PillarRankRequest,
    PillarScreenRequest,
    PillarsRequest,
    PillarsResult,
)
from src.site_structure.pillars.service import pillar_page_suggestion_service
from src.site_structure.pipeline.schemas import RankResult, ScreenResult


class SavedPillarSuggestion(EntityModel):
    id: str


@tool(writes=True, desk="site")
async def save_pillar_suggestion(
    job_id: str,
    topic: str,
    member_page_ids: list[str],
    suggestion: str,
    covering_page_id: str | None = None,
    search_score: float | None = None,
) -> SavedPillarSuggestion:
    """Save one draft pillar suggestion: a hub for the topic that links the member pages.
    Pass covering_page_id to expand an existing page instead of creating a new one. Drafts
    are invisible to the user until screening and review approve them."""
    ctx = require_site()
    body = PillarPageSuggestionCreateRequest(
        job_id=job_id,
        action="expand" if covering_page_id else "create",
        topic=topic,
        member_page_ids=member_page_ids,
        covering_page_id=covering_page_id,
        suggestion=suggestion,
        search_score=search_score,
    )
    async with unit_of_work() as db:
        record = await pillar_page_suggestion_service.create(db, ctx.user_id, ctx.site_id, body)
    return SavedPillarSuggestion(id=record.id)


@tool(writes=True, desk="site")
async def propose_pillar_pages(
    job_id: str,
    source_table: str | None = None,
    min_size: int = PILLAR_MIN_SIZE,
    min_cohesion: float = PILLAR_MIN_COHESION,
) -> PillarsResult:
    """Save draft pillar page suggestions: groups of pages on one topic that no existing page
    introduces and links. Without source_table it clusters every embedded page by meaning;
    with one it reads your workspace table (columns group_key, page_id, optional topic)."""
    ctx = require_site()
    body = PillarsRequest(
        job_id=job_id, source_table=source_table, min_size=min_size, min_cohesion=min_cohesion
    )
    async with unit_of_work() as db:
        return await pillar_page_suggestion_service.propose_pillar_pages(
            db, ctx.user_id, ctx.site_id, body
        )


@tool(writes=True, desk="site")
async def screen_pillar_suggestions(
    job_id: str | None = None, ids: list[str] | None = None, limit: int = 100
) -> ScreenResult:
    """Run the cheap screening model over draft pillar suggestions: each becomes
    screening_approved or screening_rejected."""
    ctx = require_site()
    async with unit_of_work() as db:
        return await pillar_page_suggestion_service.screen_suggestions(
            db, ctx.user_id, ctx.site_id, PillarScreenRequest(job_id=job_id, ids=ids, limit=limit)
        )


@tool(writes=True, desk="site")
async def rank_pillar_suggestions(budget: int = PILLAR_BUDGET) -> RankResult:
    """Score every review_approved pillar suggestion on the site and keep the top budget; the
    rest are deleted so they can come back later. Run it after review."""
    ctx = require_site()
    async with unit_of_work() as db:
        return await pillar_page_suggestion_service.rank_suggestions(
            db, ctx.site_id, PillarRankRequest(budget=budget)
        )
