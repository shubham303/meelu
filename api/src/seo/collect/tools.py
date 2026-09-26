from typing import Literal

from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.seo.collect.schemas import (
    CollectCompetitorKeywordsRequest,
    CollectCompetitorsRequest,
    CollectKeywordsRequest,
    CollectResult,
    CollectSerpsRequest,
)
from src.seo.collect.service import seo_collect_service


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
        return await seo_collect_service.collect_keywords(db, ctx.user_id, ctx.site_id, body)


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
        return await seo_collect_service.collect_competitors(db, ctx.user_id, ctx.site_id, body)


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
        return await seo_collect_service.collect_competitor_keywords(
            db, ctx.user_id, ctx.site_id, body
        )


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
        return await seo_collect_service.collect_serps(db, ctx.user_id, ctx.site_id, body)
