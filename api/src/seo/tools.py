from typing import Any, Literal

from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.core.schemas import EntityModel
from src.seo import export, service
from src.seo.schemas import (
    CannibalisationRequest,
    CollectCompetitorKeywordsRequest,
    CollectCompetitorsRequest,
    CollectKeywordsRequest,
    CollectResult,
    CollectSerpsRequest,
    CreateResult,
    GapPagesRequest,
    PageEditsRequest,
    RankRequest,
    RankResult,
    ReconcileResult,
    ReviewRequest,
    ReviewResult,
    SavePageSuggestionRequest,
    ScreenRequest,
    ScreenResult,
    SeoJobCreateRequest,
    SeoJobUpdateRequest,
    TopicPagesRequest,
    TopicPagesResult,
)


class StartedJob(EntityModel):
    job_id: str
    reconciled: ReconcileResult
    ready: dict[str, int]


class FinishedJob(EntityModel):
    job_id: str
    status: str


@tool(writes=True, desk="seo")
async def start_seo_job(prompt: str) -> StartedJob:
    """Open an SEO job for the prompt you are about to run and get its job_id; every
    suggestion you save carries it. Reconciles first and reports the site's standing ready
    rows per action."""
    ctx = require_site()
    async with unit_of_work() as db:
        job, reconciled = await service.start_job(
            db, ctx.user_id, ctx.site_id, SeoJobCreateRequest(prompt=prompt)
        )
        summary = await service.overview(db, ctx.user_id, ctx.site_id)
    ready = {a: getattr(summary.suggestions, a).get("ready", 0) for a in ("add", "edit", "delete")}
    return StartedJob(job_id=job.id, reconciled=reconciled, ready=ready)


@tool(writes=True, desk="seo")
async def finish_seo_job(job_id: str, status: str = "COMPLETED") -> FinishedJob:
    """Close an SEO job as COMPLETED or FAILED once the prompt has run."""
    ctx = require_site()
    async with unit_of_work() as db:
        job = await service.finish_job(db, ctx.site_id, job_id, SeoJobUpdateRequest(status=status))
    return FinishedJob(job_id=job.id, status=job.status)


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
        return await service.propose_page_edits(db, ctx.user_id, ctx.site_id, body)


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
        return await service.propose_cannibalisation(db, ctx.user_id, ctx.site_id, body)


@tool(writes=True, desk="seo")
async def save_page_suggestion(
    job_id: str,
    action: Literal["add", "edit", "delete"],
    topic_key: str,
    suggestion: str,
    page_id: str | None = None,
    merge_into_page_id: str | None = None,
    keyword_ids: list[str] | None = None,
    terms: list[str] | None = None,
    evidence: dict[str, Any] | None = None,
) -> CreateResult:
    """Save one page suggestion you wrote yourself; it lands ready for the user. topic_key is
    the head keyword it is about; a delete needs merge_into_page_id and obeys the same
    protections as the generators."""
    ctx = require_site()
    body = SavePageSuggestionRequest(
        job_id=job_id,
        action=action,
        topic_key=topic_key,
        suggestion=suggestion,
        page_id=page_id,
        merge_into_page_id=merge_into_page_id,
        keyword_ids=keyword_ids or [],
        terms=terms or [],
        evidence=evidence or {},
    )
    async with unit_of_work() as db:
        return await service.save_suggestion(db, ctx.user_id, ctx.site_id, body)


@tool(writes=True, desk="seo")
async def screen_page_suggestions(
    job_id: str, ids: list[str] | None = None, question: str | None = None, limit: int = 200
) -> ScreenResult:
    """Run the cheap screening model over the job's draft suggestions; a confident no
    becomes llm_rejected, the rest stay draft for review_page_suggestions."""
    ctx = require_site()
    async with unit_of_work() as db:
        return await service.screen_suggestions(
            db,
            ctx.user_id,
            ctx.site_id,
            ScreenRequest(job_id=job_id, ids=ids, question=question, limit=limit),
        )


@tool(writes=True, desk="seo")
async def review_page_suggestions(
    job_id: str, prompt: str, ids: list[str] | None = None, limit: int = 200
) -> ReviewResult:
    """Have the review model read each draft against your prompt with the live page,
    keyword and search-result facts, rewrite the suggestion and settle it reviewed or
    llm_rejected. Adds without a search snapshot come back in needs_serp; run it after
    screening and before rank_page_suggestions."""
    ctx = require_site()
    async with unit_of_work() as db:
        return await service.review_suggestions(
            db,
            ctx.user_id,
            ctx.site_id,
            ReviewRequest(job_id=job_id, prompt=prompt, ids=ids, limit=limit),
        )


@tool(writes=True, desk="seo")
async def rank_page_suggestions(
    job_id: str, budget_add: int = 10, budget_edit: int = 20, budget_delete: int = 5
) -> RankResult:
    """Score the job's reviewed rows per action and keep the budget as ready; the rest
    become llm_rejected. A cannibalisation pair counts once against budget_delete."""
    ctx = require_site()
    async with unit_of_work() as db:
        return await service.rank_suggestions(
            db,
            ctx.site_id,
            RankRequest(
                job_id=job_id,
                budget_add=budget_add,
                budget_edit=budget_edit,
                budget_delete=budget_delete,
            ),
        )


@tool(writes=True, desk="seo")
async def collect_keywords(
    job_id: str,
    seeds: list[str] | None = None,
    keyword_ids: list[str] | None = None,
    source_table: str | None = None,
    from_ranked: bool = True,
    max_seeds: int = 10,
    ideas_per_seed: int = 30,
    dry_run: bool = False,
) -> CollectResult:
    """Grow the keyword table from the vendor: keywords our domain ranks for, ideas per seed
    (seeds default to the top Search Console queries), and facts for rows that lack them.
    Charges the job's vendor budget; dry_run reports the calls it would make."""
    ctx = require_site()
    body = CollectKeywordsRequest(
        job_id=job_id,
        seeds=seeds,
        keyword_ids=keyword_ids,
        source_table=source_table,
        from_ranked=from_ranked,
        max_seeds=max_seeds,
        ideas_per_seed=ideas_per_seed,
        dry_run=dry_run,
    )
    async with unit_of_work() as db:
        return await service.collect_keywords(db, ctx.user_id, ctx.site_id, body)


@tool(writes=True, desk="seo")
async def collect_competitors(
    job_id: str, limit: int = 10, keyword_ids: list[str] | None = None
) -> CollectResult:
    """Find candidate competitor domains from the vendor's rival list and the results pages
    of our top queries, saved as candidates. The user confirms them on the SEO screen;
    only confirmed competitors feed the gap generator."""
    ctx = require_site()
    body = CollectCompetitorsRequest(job_id=job_id, limit=limit, keyword_ids=keyword_ids)
    async with unit_of_work() as db:
        return await service.collect_competitors(db, ctx.user_id, ctx.site_id, body)


@tool(writes=True, desk="seo")
async def collect_competitor_keywords(
    job_id: str, competitor_ids: list[str] | None = None, limit: int = 300
) -> CollectResult:
    """Pull the keywords each confirmed competitor ranks for, with their facts, into the
    keyword and competitor-keyword tables. Skips competitors fetched in the last two weeks."""
    ctx = require_site()
    body = CollectCompetitorKeywordsRequest(
        job_id=job_id, competitor_ids=competitor_ids, limit=limit
    )
    async with unit_of_work() as db:
        return await service.collect_competitor_keywords(db, ctx.user_id, ctx.site_id, body)


@tool(writes=True, desk="seo")
async def collect_serps(
    job_id: str,
    keyword_ids: list[str] | None = None,
    terms: list[str] | None = None,
    suggestion_ids: list[str] | None = None,
    source_table: str | None = None,
    device: Literal["desktop", "mobile"] = "desktop",
    max_keywords: int = 30,
) -> CollectResult:
    """Store the top-10 results page for keywords (by id, by text, by the head keyword of
    given suggestions, by workspace table, or the job's drafts when none is given), plus
    the questions and related searches on it. Refuses more than max_keywords."""
    ctx = require_site()
    body = CollectSerpsRequest(
        job_id=job_id,
        keyword_ids=keyword_ids,
        terms=terms,
        suggestion_ids=suggestion_ids,
        source_table=source_table,
        device=device,
        max_keywords=max_keywords,
    )
    async with unit_of_work() as db:
        return await service.collect_serps(db, ctx.user_id, ctx.site_id, body)


@tool(writes=True, desk="seo")
async def propose_gap_pages(
    job_id: str,
    keyword_ids: list[str] | None = None,
    min_volume: int = 50,
    max_difficulty: int = 60,
) -> CreateResult:
    """Save draft add suggestions for keyword clusters confirmed competitors rank top ten for
    and no page of ours covers. Needs confirmed competitors and their keywords collected."""
    ctx = require_site()
    body = GapPagesRequest(
        job_id=job_id, keyword_ids=keyword_ids, min_volume=min_volume, max_difficulty=max_difficulty
    )
    async with unit_of_work() as db:
        return await service.propose_gap_pages(db, ctx.user_id, ctx.site_id, body)


@tool(writes=True, desk="seo")
async def propose_topic_pages(
    job_id: str,
    topic: str,
    source_table: str | None = None,
    ideas_per_seed: int = 30,
    dry_run: bool = False,
) -> TopicPagesResult:
    """Grow keyword ideas from a topic (charged), group them, drop groups a page already
    covers, and save the rest as draft add suggestions."""
    ctx = require_site()
    body = TopicPagesRequest(
        job_id=job_id,
        topic=topic,
        source_table=source_table,
        ideas_per_seed=ideas_per_seed,
        dry_run=dry_run,
    )
    async with unit_of_work() as db:
        return await service.propose_topic_pages(db, ctx.user_id, ctx.site_id, body)


@tool(desk="seo")
async def seo_download_data(
    dataset: Literal[
        "keywords", "gsc_pages", "content_pages", "competitor_keywords", "serps", "suggestions"
    ],
) -> dict:
    """Export one SEO dataset as a CSV file and return its path and row count. Analyse the
    file with the analytics engine; the rows never come back inline."""
    ctx = require_site()
    async with unit_of_work() as db:
        path, rows = await export.write_csv(db, ctx.site_id, ctx.schema, dataset)
    return {"path": str(path), "rows": rows, "dataset": dataset}
