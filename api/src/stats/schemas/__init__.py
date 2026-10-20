from src.core.schemas import EntityModel, JsDateTime


class WaitingCounts(EntityModel):
    structure_suggestions: int = 0
    conversations_to_reply: int = 0
    leads_to_message: int = 0
    issues_open: int = 0


class StatsRecord(EntityModel):
    keep_null = frozenset({"lastCrawlAt"})

    pages: int = 0
    last_crawl_at: JsDateTime | None = None
    content_pieces: int = 0
    reports: int = 0
    waiting: WaitingCounts = WaitingCounts()


class StatsResponse(StatsRecord):
    pass
