from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.core.schemas import EntityModel
from src.site_structure.pillars.service import pillar_page_suggestion_service
from src.site_structure.schemas import (
    HierarchyRequest,
    HierarchyResult,
    MentionsRequest,
    MentionsResult,
    PillarRankRequest,
    PillarScreenRequest,
    PillarsRequest,
    PillarsResult,
    RankRequest,
    RankResult,
    ReconcileResult,
    RemovalsRequest,
    RemovalsResult,
    ScreenRequest,
    ScreenResult,
    StructureJobCreateRequest,
    StructureJobUpdateRequest,
)
from src.site_structure.service import link_suggestion_service, structure_job_service


class StartedJob(EntityModel):
    job_id: str
    reconciled: ReconcileResult


class FinishedJob(EntityModel):
    job_id: str
    status: str


@tool(writes=True, desk="site")
async def start_structure_job(prompt: str) -> StartedJob:
    """Open a structure job for the prompt you are about to run and get its job_id; every
    suggestion you save carries it. Reconciles first: link suggestions already satisfied
    or pointing at a gone page are deleted."""
    ctx = require_site()
    async with unit_of_work() as db:
        job, reconciled = await structure_job_service.start_job(
            db, ctx.user_id, ctx.site_id, StructureJobCreateRequest(prompt=prompt)
        )
    return StartedJob(job_id=job.id, reconciled=reconciled)


@tool(writes=True, desk="site")
async def finish_structure_job(job_id: str, status: str = "COMPLETED") -> FinishedJob:
    """Close a structure job as COMPLETED or FAILED once the prompt has run."""
    ctx = require_site()
    async with unit_of_work() as db:
        job = await structure_job_service.finish_job(
            db, ctx.site_id, job_id, StructureJobUpdateRequest(status=status)
        )
    return FinishedJob(job_id=job.id, status=job.status)


@tool(writes=True, desk="site")
async def propose_unlinked_mentions(
    job_id: str, to_ids: list[str], phrases: list[str], limit_per_target: int = 50
) -> MentionsResult:
    """For each target page id, find passages elsewhere on the site that contain one of the
    phrases (its title, H1, a query it ranks for) and do not already link to it, and save a
    draft link suggestion per source page. Edges that already have a row are skipped."""
    ctx = require_site()
    body = MentionsRequest(
        job_id=job_id, to_ids=to_ids, phrases=phrases, limit_per_target=limit_per_target
    )
    async with unit_of_work() as db:
        return await link_suggestion_service.propose_unlinked_mentions(
            db, ctx.user_id, ctx.site_id, body
        )


@tool(writes=True, desk="site")
async def propose_hierarchy_links(job_id: str) -> HierarchyResult:
    """Save draft link suggestions for the site's skeleton, ignoring text similarity: home
    to and from every hub and utility page, and hub to hub where one URL path is the parent
    of the other or both share a parent. Edges that exist or already have a row are skipped."""
    ctx = require_site()
    async with unit_of_work() as db:
        return await link_suggestion_service.propose_hierarchy_links(
            db, ctx.user_id, ctx.site_id, HierarchyRequest(job_id=job_id)
        )


@tool(writes=True, desk="site")
async def propose_link_removals(job_id: str, source_table: str) -> RemovalsResult:
    """Save draft delete suggestions for the existing links listed in a table in your
    workspace schema (columns from_page_id, to_page_id, optional reason). Keeps only body
    links, never a target's last inlink or a link to the home or a hub page; scores each
    by how little the anchor's passage relates to the target."""
    ctx = require_site()
    async with unit_of_work() as db:
        return await link_suggestion_service.propose_link_removals(
            db, ctx.user_id, ctx.site_id, RemovalsRequest(job_id=job_id, source_table=source_table)
        )


@tool(writes=True, desk="site")
async def screen_link_suggestions(
    job_id: str | None = None,
    ids: list[str] | None = None,
    question: str | None = None,
    limit: int = 200,
) -> ScreenResult:
    """Run the cheap screening model over unscreened draft suggestions (a job's, or the
    given ids). A confident no becomes llm_rejected; everything else stays draft for
    review_link_suggestions. Pass a question to replace the default one the model is asked."""
    ctx = require_site()
    async with unit_of_work() as db:
        return await link_suggestion_service.screen_suggestions(
            db,
            ctx.user_id,
            ctx.site_id,
            ScreenRequest(job_id=job_id, ids=ids, question=question, limit=limit),
        )


@tool(writes=True, desk="site")
async def rank_link_suggestions(
    max_per_target: int | None = None, target_discount: float = 1.0
) -> RankResult:
    """Score every open link suggestion on the site and cut to each source page's link
    budget; rows that lose their slot become llm_rejected, kept rows keep their state.
    Run it after screening."""
    ctx = require_site()
    async with unit_of_work() as db:
        return await link_suggestion_service.rank_suggestions(
            db,
            ctx.site_id,
            RankRequest(max_per_target=max_per_target, target_discount=target_discount),
        )


@tool(writes=True, desk="site")
async def propose_pillar_pages(
    job_id: str,
    source_table: str | None = None,
    min_size: int = 4,
    min_cohesion: float = 0.35,
) -> PillarsResult:
    """Save draft pillar page suggestions: groups of pages on one topic that no existing
    page introduces and links. Without source_table it clusters every embedded page by
    meaning; with one it reads your workspace table (columns group_key, page_id, optional
    topic). Groups that are small, loose, mostly utility pages, already covered, or
    overlap an open or turned-down suggestion are dropped."""
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
    """Run the cheap screening model over unscreened draft pillar suggestions. A confident
    no becomes llm_rejected; the rest stay draft for review_pillar_suggestions."""
    ctx = require_site()
    async with unit_of_work() as db:
        return await pillar_page_suggestion_service.screen_suggestions(
            db, ctx.user_id, ctx.site_id, PillarScreenRequest(job_id=job_id, ids=ids, limit=limit)
        )


@tool(writes=True, desk="site")
async def rank_pillar_suggestions(budget: int = 5) -> RankResult:
    """Score every open pillar suggestion on the site and keep the top budget; the rest
    become llm_rejected. Run it after screening."""
    ctx = require_site()
    async with unit_of_work() as db:
        return await pillar_page_suggestion_service.rank_suggestions(
            db, ctx.site_id, PillarRankRequest(budget=budget)
        )
