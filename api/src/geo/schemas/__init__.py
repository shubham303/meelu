from typing import Any

from pydantic import Field

from src.core.schemas import EntityModel, JsDateTime, RequestModel

INTENTS = ("informational", "commercial", "transactional", "navigational")
POINT_STATUSES = ("answers", "partly", "missing")
VERDICTS = ("no_page", "partial", "low_rank", "covered")
CHECK_STATUSES = ("running", "done", "error", "stopped")
QUERY_SOURCES = ("user", "suggested")
AI_PLATFORMS = ("chat_gpt", "claude", "ai_overview")
GOOD_POSITION = 10.0
MAX_QUERIES_PER_SITE = 100
MAX_QUERY_CHARS = 300
CANDIDATE_PAGES = 3
STALE_DAYS = 7
RUNNING_TIMEOUT_MINUTES = 20
CHECK_CONCURRENCY = 3


class QueryUpsertItem(RequestModel):
    text: str
    enabled: bool = True
    source: str = "user"


class QueryPatchRequest(RequestModel):
    text: str | None = None
    enabled: bool | None = None

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class ChecksStartRequest(RequestModel):
    query_ids: list[str] | None = None


class Citation(EntityModel):
    url: str
    title: str | None = None


class PointResult(EntityModel):
    point: str
    status: str
    evidence: str | None = None


class PageResult(EntityModel):
    page_id: str
    url: str
    title: str | None = None
    coverage: float
    points: list[PointResult]


class AiAnswer(EntityModel):
    platform: str
    shown: bool
    text: str = ""
    citations: list[Citation] = Field(default_factory=list)
    cited_us: bool = False
    covers: list[str] = Field(default_factory=list)
    misses: list[str] = Field(default_factory=list)
    error: str | None = None


class CheckProgress(EntityModel):
    stage: str | None = None
    pages_found: int | None = None
    points: int | None = None
    pages_judged: int = 0
    answers_fetched: int = 0


class CheckResponse(EntityModel):
    id: str
    site_id: str
    query_id: str
    status: str
    progress: CheckProgress = Field(default_factory=CheckProgress)
    started_at: JsDateTime
    finished_at: JsDateTime | None = None
    error: str | None = None
    intent: str | None = None
    required_points: list[str]
    verdict: str | None = None
    page_id: str | None = None
    page_url: str | None = None
    position: float | None = None
    pages: list[PageResult]
    ai_answers: list[AiAnswer]
    page_adds: list[str]
    suggestion: str | None = None
    model: str | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class QueryResponse(EntityModel):
    id: str
    site_id: str
    text: str
    source: str
    enabled: bool
    latest_check: CheckResponse | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class UpsertResponse(EntityModel):
    inserted: int
    updated: int


class DeleteResponse(EntityModel):
    id: str


class ChecksStartResponse(EntityModel):
    started: list[CheckResponse]
    already_running: int


class ChecksStopResponse(EntityModel):
    stopped: int


class SummaryResponse(EntityModel):
    queries: int
    unchecked: int
    running: int
    no_page: int
    partial: int
    low_rank: int
    covered: int
    cited: int
    last_checked_at: JsDateTime | None = None
