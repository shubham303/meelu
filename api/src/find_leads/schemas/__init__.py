from typing import Any

from pydantic import Field

from src.core.schemas import EntityModel, JsDateTime, RequestModel

SOURCES = ("posts", "linkedin", "web")
PIPELINE_STATUSES = ("candidate", "shortlisted")
USER_STATUSES = ("new", "contacted", "discarded")
LEAD_STATUSES = PIPELINE_STATUSES + USER_STATUSES
RUN_STATUSES = ("running", "done", "stopped", "error")
SEEN_JUDGED = "judged"
SEEN_DISCARDED = "discarded"
MAX_BRIEFS_PER_SITE = 10
KEYWORDS_PER_BRIEF = 2
WEB_ANGLES_PER_BRIEF = 3
PER_KEYWORD = 25
LOOKBACK_DAYS = 7
MAX_POST_AGE_DAYS = 30
MAX_CANDIDATES_PER_RUN = 1000
MAX_ROUNDS = 10
DEFAULT_TARGET = 20
MAX_TARGET = 100
MAX_CANDIDATES_PER_SOURCE = 40
MAX_ENRICHED_PER_RUN = 60
ACTIVITY_ITEMS = 5
MAX_EVIDENCE = 3
MINIMUM_BALANCE_USD = 1
DEFAULT_SOURCES = ["posts", "linkedin"]
SKIP_HOURS = 12
WEB_CACHE_HOURS = 6
SEARCH_RETENTION_DAYS = 30
WEB_PLATFORM = "web"


class LinkedinPlan(RequestModel):
    query: str = ""
    titles: list[str] = []
    locations: list[str] = []


class RoundPlan(RequestModel):
    keywords: list[str] = []
    web: list[str] = []


class BriefPlan(RequestModel):
    keywords: list[str] = []
    linkedin: LinkedinPlan | None = None
    web: list[str] = []
    rounds: list[RoundPlan] = []


class BriefCreateRequest(RequestModel):
    text: str
    enabled: bool = True
    sources: list[str] | None = None


class BriefUpsertItem(RequestModel):
    text: str
    enabled: bool = True
    sources: list[str] | None = None
    source: str = "user"


class BriefPatchRequest(RequestModel):
    text: str | None = None
    enabled: bool | None = None
    sources: list[str] | None = None
    plan: BriefPlan | None = None

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class RunCreateRequest(RequestModel):
    target_count: int = Field(DEFAULT_TARGET, ge=1, le=MAX_TARGET)


class RunUpdateRequest(RequestModel):
    status: str | None = None
    round: int | None = Field(None, ge=1, le=MAX_ROUNDS)
    shortlisted_count: int | None = None
    kept_count: int | None = None
    error: str | None = None

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class BriefSearch(RequestModel):
    brief_id: str
    keywords: list[str] = []


class CollectRequest(RequestModel):
    source: str
    platform: str | None = None
    searches: list[BriefSearch] | None = None


class Evidence(RequestModel):
    url: str
    quote: str
    at: str | None = None


class CandidateItem(RequestModel):
    brief_id: str | None = None
    name: str | None = None
    handle: str | None = None
    headline: str | None = None
    website: str | None = None
    profile_url: str | None = None
    email: str | None = None
    email_source_url: str | None = None
    snippet: str | None = None
    evidence: list[Evidence] = []


class CandidatesRequest(RequestModel):
    run_id: str
    source: str = WEB_PLATFORM
    platform: str = WEB_PLATFORM
    leads: list[CandidateItem]


class JudgeVerdict(RequestModel):
    id: str
    keep: bool
    reason: str | None = None
    angle: str | None = None
    evidence: list[Evidence] = []


class JudgeRequest(RequestModel):
    leads: list[JudgeVerdict]


class CheckRequest(RequestModel):
    ids: list[str] = Field(max_length=200)


class WebSearchRecord(RequestModel):
    query: str
    results: list[dict[str, Any]] = Field(default_factory=list, max_length=50)


class LeadPatchRequest(RequestModel):
    status: str | None = None

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class LeadFilters(RequestModel):
    statuses: list[str] | None = None
    brief_id: str | None = None
    run_id: str | None = None
    source: str | None = None
    q: str | None = None


class BriefResponse(EntityModel):
    id: str
    site_id: str
    text: str
    enabled: bool
    source: str
    sources: list[str]
    plan: dict[str, Any]
    found: int = 0
    kept: int = 0
    created_at: JsDateTime
    updated_at: JsDateTime


class RunResponse(EntityModel):
    id: str
    site_id: str
    status: str
    target_count: int
    round: int
    started_at: JsDateTime
    finished_at: JsDateTime | None = None
    found_count: int
    shortlisted_count: int
    kept_count: int
    source_stats: dict[str, Any]
    error: str | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class LeadResponse(EntityModel):
    id: str
    site_id: str
    brief_id: str | None = None
    run_id: str | None = None
    source: str
    platform: str
    name: str | None = None
    handle: str | None = None
    headline: str | None = None
    profile_url: str | None = None
    email: str | None = None
    email_source_url: str | None = None
    website: str | None = None
    snippet: str | None = None
    evidence: list[dict[str, Any]]
    activity: list[dict[str, Any]]
    enriched_at: JsDateTime | None = None
    reason: str | None = None
    angle: str | None = None
    status: str
    contacted_at: JsDateTime | None = None
    discarded_at: JsDateTime | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class CheckResponse(EntityModel):
    fits: list[str]
    removed: int


class SearchResponse(EntityModel):
    platform: str
    query: str
    page: int
    searched_at: JsDateTime
    results: list[dict[str, Any]]


class InsertedResponse(EntityModel):
    inserted: int
    skipped: int


class VerdictResponse(EntityModel):
    kept: int
    removed: int


class UpsertResponse(EntityModel):
    inserted: int
    updated: int


class DeleteResponse(EntityModel):
    id: str


class SummaryResponse(EntityModel):
    new: int
    contacted: int
    discarded: int
    unprocessed: int
    last_run: RunResponse | None = None
