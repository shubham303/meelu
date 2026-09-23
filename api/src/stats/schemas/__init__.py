from src.core.schemas import EntityModel


class ContentStats(EntityModel):
    drafts: int = 0
    blocked: int = 0


class SeoStats(EntityModel):
    pages: int = 0


class StatsRecord(EntityModel):
    content: ContentStats = ContentStats()
    seo: SeoStats = SeoStats()


class StatsResponse(EntityModel):
    content: ContentStats
    seo: SeoStats
