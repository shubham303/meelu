from typing import Literal

from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.seo.generators.schemas import CannibalisationRequest, PageEditsRequest
from src.seo.generators.service import seo_generator_service
from src.seo.page_suggestions.schemas import CreateResult


@tool(writes=True, desk="seo")
async def propose_page_edits(
    job_id: str,
    evidence: Literal["all", "gsc", "cluster", "ctr", "questions", "decay"] = "all",
    page_ids: list[str] | None = None,
    keyword_ids: list[str] | None = None,
    min_position: float = 4,
    max_position: float = 20,
    min_impressions: int = 100,
) -> CreateResult:
    """Save draft edit suggestions from Search Console and cluster evidence: queries a page
    ranks for but barely covers (gsc), cluster subtopics its owner page misses (cluster),
    pages ranked but not clicked (ctr), unanswered question queries (questions), and pages
    whose clicks fell (decay). Filters are in the guide."""
    ctx = require_site()
    body = PageEditsRequest(
        job_id=job_id,
        evidence=evidence,
        page_ids=page_ids,
        keyword_ids=keyword_ids,
        min_position=min_position,
        max_position=max_position,
        min_impressions=min_impressions,
    )
    async with unit_of_work() as db:
        return await seo_generator_service.propose_page_edits(db, ctx.user_id, ctx.site_id, body)


@tool(writes=True, desk="seo")
async def propose_cannibalisation(
    job_id: str, page_ids: list[str] | None = None, min_shared_impressions: int = 50
) -> CreateResult:
    """Save draft pairs for pages that alternate on the same Search Console queries: an edit
    on the stronger page and a delete-and-merge on the weaker, reviewed as one. Protected
    pages never get a delete; see the guide."""
    ctx = require_site()
    body = CannibalisationRequest(
        job_id=job_id, page_ids=page_ids, min_shared_impressions=min_shared_impressions
    )
    async with unit_of_work() as db:
        return await seo_generator_service.propose_cannibalisation(
            db, ctx.user_id, ctx.site_id, body
        )
