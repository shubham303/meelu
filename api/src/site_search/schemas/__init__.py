import math
import re
from datetime import date
from typing import Any, Literal

from pydantic import Field, field_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel

DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_DAYS_PER_BATCH = 31
MAX_TEXT_CHARS = 2048
SYNC_END_STATUSES = ("completed", "failed", "cancelled")


def _count(value: Any) -> int:
    if isinstance(value, bool):
        n = 1.0 if value else 0.0
    elif isinstance(value, (int, float)):
        n = float(value)
    elif isinstance(value, str):
        try:
            n = float(value)
        except ValueError:
            n = 0.0
    else:
        n = 0.0
    if not math.isfinite(n):
        n = 0.0
    return max(0, math.floor(n + 0.5))


def _number(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value) if math.isfinite(float(value)) else 0.0
    if isinstance(value, str):
        try:
            n = float(value)
        except ValueError:
            return 0.0
        return n if math.isfinite(n) else 0.0
    return 0.0


class SearchPropertyRequest(RequestModel):
    property: str

    @field_validator("property", mode="before")
    @classmethod
    def _validate_property(cls, v: Any) -> str:
        clean = ("" if v is None else str(v)).strip()
        if not clean:
            raise ValueError("property is required — the exact Search Console property.")
        return clean


class SearchDailyRowInput(RequestModel):
    query: str
    page: str
    clicks: int = 0
    impressions: int = 0
    position: float = 0.0

    @field_validator("query", "page", mode="before")
    @classmethod
    def _validate_text(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("query and page must be strings.")
        return v[:MAX_TEXT_CHARS]

    @field_validator("clicks", "impressions", mode="before")
    @classmethod
    def _validate_count(cls, v: Any) -> int:
        return _count(v)

    @field_validator("position", mode="before")
    @classmethod
    def _validate_position(cls, v: Any) -> float:
        return _number(v)


class SearchDayRowsInput(RequestModel):
    day: str
    rows: list[SearchDailyRowInput] = Field(default_factory=list)

    @field_validator("day", mode="before")
    @classmethod
    def _validate_day(cls, v: Any) -> str:
        day = "" if v is None else str(v)
        if not DAY_RE.match(day):
            raise ValueError(f'"{day}" is not a YYYY-MM-DD day.')
        return day


class SearchRowsIngestRequest(RequestModel):
    days: list[SearchDayRowsInput]

    @field_validator("days")
    @classmethod
    def _validate_days(cls, v: list[SearchDayRowsInput]) -> list[SearchDayRowsInput]:
        if len(v) == 0:
            raise ValueError(
                "Send `days: [{ day, rows }]` — a sync batch with no days writes nothing."
            )
        if len(v) > MAX_DAYS_PER_BATCH:
            raise ValueError("At most 31 days per batch — post month-sized batches.")
        return v


class SearchInspectionInput(RequestModel):
    url: str
    verdict: str | None = None
    coverage_state: str | None = None
    google_canonical: str | None = None
    last_crawl_time: str | None = None


class SearchInspectionsIngestRequest(RequestModel):
    inspections: list[SearchInspectionInput]

    @field_validator("inspections")
    @classmethod
    def _validate_inspections(cls, v: list[SearchInspectionInput]) -> list[SearchInspectionInput]:
        if len(v) == 0:
            raise ValueError("Send `inspections: [...]` — a batch with no rows writes nothing.")
        return v


class SearchSyncStartRequest(RequestModel):
    trigger: str = "user"


class SearchSyncUpdateRequest(RequestModel):
    days_done: int | None = None
    rows_stored: int | None = None
    pages_inspected: int | None = None
    property: str | None = None
    status: Literal["completed", "failed", "cancelled"] | None = None
    error: str | None = None
    notes: list[Any] | None = None


class SearchSyncRecord(EntityModel):
    keep_null = frozenset({"finishedAt", "error"})

    id: str
    site_id: str
    status: str
    trigger: str
    property: str | None = None
    started_at: JsDateTime | None = None
    finished_at: JsDateTime | None = None
    heartbeat_at: JsDateTime | None = None
    days_total: int
    days_done: int
    rows_stored: int
    pages_inspected: int
    first_day: date | None = None
    last_day: date | None = None
    error: str | None = None
    notes: list[Any]
    created_at: JsDateTime
    updated_at: JsDateTime


class SearchCoverageRecord(EntityModel):
    first_day: str | None
    last_day: str | None
    days_stored: int
    impressions_28d: int


class SearchTotals(EntityModel):
    clicks: int
    impressions: int
    ctr: float | None
    position: float | None


class SearchDailyPoint(EntityModel):
    day: str
    page: str | None
    clicks: int
    impressions: int
    position: float | None


class GooglePreferredCanonical(EntityModel):
    url: str
    google_canonical: str | None
    coverage_state: str | None


class IndexationSummary(EntityModel):
    counts: dict[str, int]
    never_checked: int
    google_prefers: list[GooglePreferredCanonical]


class SearchPageRollupRow(EntityModel):
    page: str
    page_id: str | None
    title: str | None
    inlinks: int | None
    index_state: str | None
    coverage_state: str | None
    google_canonical: str | None
    last_crawl_time: str | None
    index_checked_at: str | None
    top_query: str | None
    clicks: int
    prev_clicks: int
    impressions: int
    position: float | None
    prev_position: float | None
    weekly: list[int]


class SearchPageRollup(EntityModel):
    total: int
    rows: list[SearchPageRollupRow]


class SearchQueryRollupRow(EntityModel):
    query: str
    page: str | None
    page_id: str | None
    inlinks: int | None
    clicks: int
    prev_clicks: int
    impressions: int
    position: float | None
    prev_position: float | None


class SearchQueryRollup(EntityModel):
    total: int
    rows: list[SearchQueryRollupRow]


class SearchMover(EntityModel):
    kind: str
    key: str
    clicks: int
    prev_clicks: int
    position: float | None
    prev_position: float | None


class SearchMovers(EntityModel):
    up: list[SearchMover]
    down: list[SearchMover]


class SearchSyncResponse(EntityModel):
    keep_null = frozenset({"finishedAt", "error"})

    id: str
    site_id: str
    status: str
    trigger: str
    property: str | None = None
    started_at: JsDateTime | None = None
    finished_at: JsDateTime | None = None
    heartbeat_at: JsDateTime | None = None
    days_total: int
    days_done: int
    rows_stored: int
    pages_inspected: int
    first_day: date | None = None
    last_day: date | None = None
    error: str | None = None
    notes: list[Any]
    created_at: JsDateTime
    updated_at: JsDateTime


class SearchPropertyResponse(EntityModel):
    property: str


class SearchRowsIngestResponse(EntityModel):
    days: int
    rows: int


class SearchInspectionsIngestResponse(EntityModel):
    applied: int


class SearchInspectionTargetsResponse(EntityModel):
    urls: list[str]


class SearchOverviewResponse(EntityModel):
    connected: bool
    property: str | None
    has_data: bool
    operating_blind: bool
    first_day: str | None = None
    last_day: str | None = None
    days_stored: int | None = None
    current: SearchTotals | None = None
    previous: SearchTotals | None = None
    weekly_clicks: list[int] | None = None
    indexation: dict[str, int] | None = None
    never_checked: int | None = None
    google_prefers: list[GooglePreferredCanonical] | None = None
    content_quality_verdict: str | None = None
    sync: SearchSyncResponse | None = None
    active: SearchSyncResponse | None = None


class SearchSeriesPoint(EntityModel):
    day: str
    clicks: int
    impressions: int
    ctr: float | None
    position: float | None


class SearchSeriesGroup(EntityModel):
    page: str | None
    points: list[SearchSeriesPoint]


class SearchSeriesResponse(EntityModel):
    has_data: bool
    last_day: str | None
    days: int
    series: list[SearchSeriesGroup]
    current: SearchTotals | None = None
    previous: SearchTotals | None = None


class SearchPagesResponse(EntityModel):
    rows: list[SearchPageRollupRow]
    total: int
    last_day: str | None
    days: int | None = None


class SearchPageDetailResponse(EntityModel):
    page: str
    queries: list[SearchQueryRollupRow]
    last_day: str | None
    days: int | None = None
    has_data: bool


class SearchQueriesResponse(EntityModel):
    rows: list[SearchQueryRollupRow]
    total: int
    last_day: str | None
    days: int | None = None


class SearchChangesResponse(EntityModel):
    up: list[SearchMover]
    down: list[SearchMover]
    last_day: str | None
    days: int | None = None
    has_data: bool


class SearchSyncJobsResponse(EntityModel):
    latest: SearchSyncResponse | None
    active: SearchSyncResponse | None


class SearchSyncStartResponse(EntityModel):
    started: bool
    sync: SearchSyncResponse | None
    reason: str | None = None


class SearchSyncClaimResponse(EntityModel):
    sync: SearchSyncResponse
    property: str | None
    domain: str
    start_day: str
    end_day: str
    resume_from: str | None
    days_total: int
