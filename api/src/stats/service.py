from sqlalchemy.ext.asyncio import AsyncSession

from src.content.pieces.repository import content_pieces
from src.site_pages.repositories.pages import site_pages
from src.stats.schemas import ContentStats, SeoStats, StatsRecord


class StatsService:
    def empty(self) -> StatsRecord:
        return StatsRecord()

    async def get(self, db: AsyncSession, site_id: str) -> StatsRecord:
        piece_counts = await content_pieces.counts_by_status(db, site_id)
        page_counts = await site_pages.page_counts(db, site_id)
        return StatsRecord(
            content=ContentStats(
                drafts=piece_counts.by_status.get("draft", 0),
                blocked=piece_counts.by_status.get("blocked", 0),
            ),
            seo=SeoStats(pages=page_counts.pages),
        )


stats_service = StatsService()
