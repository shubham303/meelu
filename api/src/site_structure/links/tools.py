from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.core.schemas import EntityModel
from src.site_structure.links.schemas import (
    HierarchyRequest,
    HierarchyResult,
    LinkSuggestionCreateRequest,
    MentionsRequest,
    MentionsResult,
    MentionTarget,
    PairsRequest,
    PairsResult,
    RankRequest,
    RemovalsRequest,
    RemovalsResult,
    ScreenRequest,
)
from src.site_structure.links.service import link_suggestion_service
from src.site_structure.pipeline.schemas import RankResult, ScreenResult


class SavedLinkSuggestion(EntityModel):
    id: str


@tool(writes=True, desk="site")
async def save_link_suggestion(
    job_id: str,
    from_page_id: str,
    to_page_id: str,
    suggestion: str,
    action: str = "create",
    from_chunk_id: str | None = None,
    search_score: float | None = None,
) -> SavedLinkSuggestion:
    """Save one draft suggestion to add (action create) or remove (action delete) the link
    from_page_id -> to_page_id, anchored in from_chunk_id when given. Drafts are invisible
    to the user until screening and review approve them; higher search_score is better."""
    ctx = require_site()
    body = LinkSuggestionCreateRequest(
        job_id=job_id,
        from_page_id=from_page_id,
        to_page_id=to_page_id,
        suggestion=suggestion,
        action=action,
        from_chunk_id=from_chunk_id,
        search_score=search_score,
    )
    async with unit_of_work() as db:
        record = await link_suggestion_service.create(db, ctx.user_id, ctx.site_id, body)
    return SavedLinkSuggestion(id=record.id)


@tool(writes=True, desk="site")
async def propose_hierarchy_links(job_id: str) -> HierarchyResult:
    """Save draft link suggestions for the site's skeleton, ignoring text similarity: home
    to and from every utility page, and hub to hub where one URL path is the parent of the
    other. Links that exist or already have a suggestion are
    skipped."""
    ctx = require_site()
    async with unit_of_work() as db:
        return await link_suggestion_service.add_hierarchy_edges(
            db, ctx.user_id, ctx.site_id, HierarchyRequest(job_id=job_id)
        )


@tool(writes=True, desk="site")
async def propose_unlinked_mentions(
    job_id: str, targets: list[MentionTarget], limit_per_target: int = 50
) -> MentionsResult:
    """For each target page, find passages elsewhere on the site that contain one of its
    phrases (its title, H1, key phrases from its meta description, a query it ranks for)
    and do not already link to it, and save a draft link suggestion per source page. Pages
    out of link budget are skipped. Phrases match word for word, so pass short phrases."""
    ctx = require_site()
    body = MentionsRequest(job_id=job_id, targets=targets, limit_per_target=limit_per_target)
    async with unit_of_work() as db:
        return await link_suggestion_service.propose_unlinked_mentions(
            db, ctx.user_id, ctx.site_id, body
        )


@tool(writes=True, desk="site")
async def propose_link_removals(job_id: str, source_table: str) -> RemovalsResult:
    """Save draft delete suggestions for the existing links listed in a table in your
    workspace schema (columns from_page_id, to_page_id, optional reason). Keeps only body
    links, never a target's last inlink or a link to the home or a hub page."""
    ctx = require_site()
    async with unit_of_work() as db:
        return await link_suggestion_service.propose_link_removals(
            db, ctx.user_id, ctx.site_id, RemovalsRequest(job_id=job_id, source_table=source_table)
        )


@tool(writes=True, desk="site")
async def propose_links_from_table(
    job_id: str, source_table: str, min_similarity: float | None = None, per_source: int = 3
) -> PairsResult:
    """Save draft add suggestions for the page pairs in a table in your workspace schema
    (columns from_page_id, to_page_id, optional reason). Each pair keeps only its source
    passage closest to the target's summary, and only when that passage clears min_similarity
    (default: the site search gate); each source keeps its per_source closest pairs."""
    ctx = require_site()
    body = PairsRequest(
        job_id=job_id,
        source_table=source_table,
        min_similarity=min_similarity,
        per_source=per_source,
    )
    async with unit_of_work() as db:
        return await link_suggestion_service.propose_links_from_table(
            db, ctx.user_id, ctx.site_id, body
        )


@tool(writes=True, desk="site")
async def screen_link_suggestions(
    job_id: str | None = None,
    ids: list[str] | None = None,
    question: str | None = None,
    limit: int = 200,
) -> ScreenResult:
    """Run the cheap screening model over draft link suggestions (a job's, or the given ids):
    each becomes screening_approved or screening_rejected. Pass a question to replace the
    default one the model is asked."""
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
    """Score every review_approved link suggestion on the site and keep what fits each page's
    link budget; the rest are deleted so they can come back once budget frees up. Run it
    after review."""
    ctx = require_site()
    async with unit_of_work() as db:
        return await link_suggestion_service.rank_suggestions(
            db,
            ctx.site_id,
            RankRequest(max_per_target=max_per_target, target_discount=target_discount),
        )
