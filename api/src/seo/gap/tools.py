from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.seo.gap.schemas import GapPagesRequest, TopicPagesRequest, TopicPagesResult
from src.seo.gap.service import seo_gap_service
from src.seo.page_suggestions.schemas import CreateResult


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
        return await seo_gap_service.propose_gap_pages(db, ctx.user_id, ctx.site_id, body)


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
        return await seo_gap_service.propose_topic_pages(db, ctx.user_id, ctx.site_id, body)
