from sqlalchemy.ext.asyncio import AsyncSession

from src.content.pieces import service as pieces_service
from src.outreach import service as outreach_service
from src.site_pages import service as site_pages_service
from src.stats.schemas import ContentStats, OutreachStats, SeoStats, StatsRecord


def empty_stats() -> StatsRecord:
    return StatsRecord()


async def get_stats(db: AsyncSession, user_id: str, site_id: str) -> StatsRecord:
    piece_counts = await pieces_service.counts(db, site_id)
    page_stats = await site_pages_service.stats(db, user_id, site_id)
    outreach_counts = await outreach_service.counts(db, user_id, site_id)

    return StatsRecord(
        outreach=OutreachStats.model_validate(outreach_counts.model_dump()),
        content=ContentStats(
            drafts=piece_counts.by_status["draft"],
            scheduled=piece_counts.by_status["scheduled"],
            posted=piece_counts.by_status["posted"],
            attention=piece_counts.by_status["failed"] + piece_counts.by_status["blocked"],
        ),
        seo=SeoStats(pages=page_stats.pages),
    )
