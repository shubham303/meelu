from src.core.schemas import EntityModel


class OutreachStats(EntityModel):
    projects: int = 0
    runs: int = 0
    active_runs: int = 0
    prospects: int = 0
    drafts: int = 0
    sent: int = 0
    replies: int = 0


class ContentStats(EntityModel):
    drafts: int = 0
    scheduled: int = 0
    posted: int = 0
    attention: int = 0


class SeoStats(EntityModel):
    pages: int = 0


class StatsRecord(EntityModel):
    outreach: OutreachStats = OutreachStats()
    content: ContentStats = ContentStats()
    seo: SeoStats = SeoStats()


class StatsResponse(EntityModel):
    outreach: OutreachStats
    content: ContentStats
    seo: SeoStats
