from sqlalchemy.ext.asyncio import AsyncSession

from src.content.pieces.repository import content_pieces
from src.crawl_jobs.repository import site_crawl_jobs
from src.find_leads.repositories.leads import leads
from src.reports.repository import reports
from src.site_pages.repositories.pages import site_pages
from src.site_structure.links.repository import link_suggestions
from src.site_structure.pillars.repository import pillar_page_suggestions
from src.social_listening.repositories.posts import social_listening_posts
from src.stats.schemas import StatsRecord, WaitingCounts
from src.technical_seo.repository import site_audit_runs, site_issues, site_page_issues


class StatsService:
    def empty(self) -> StatsRecord:
        return StatsRecord()

    async def get(self, db: AsyncSession, user_id: str, site_id: str) -> StatsRecord:
        page_counts = await site_pages.page_counts(db, site_id)
        crawl = await site_crawl_jobs.latest(db, site_id)
        return StatsRecord(
            pages=page_counts.pages,
            last_crawl_at=crawl.finished_at if crawl else None,
            content_pieces=await content_pieces.count(db, site_id),
            reports=await reports.count(db, user_id, site_id),
            waiting=await self.waiting(db, site_id),
        )

    async def waiting(self, db: AsyncSession, site_id: str) -> WaitingCounts:
        links = await link_suggestions.summary(db, site_id)
        pillars = await pillar_page_suggestions.summary(db, site_id)
        posts = await social_listening_posts.status_counts(db, site_id)
        lead_counts = await leads.status_counts(db, site_id)
        return WaitingCounts(
            structure_suggestions=links.review_approved + pillars.review_approved,
            conversations_to_reply=posts.get("to_reply", 0),
            leads_to_message=lead_counts.get("new", 0),
            issues_open=await self.open_issues(db, site_id),
        )

    async def open_issues(self, db: AsyncSession, site_id: str) -> int:
        run = await site_audit_runs.latest(db, site_id)
        if run is None:
            return 0
        site_level = await site_issues.count_by_state(db, run.id)
        page_level = await site_page_issues.count_by_state(db, run.id)
        return site_level.open + page_level.open


stats_service = StatsService()
