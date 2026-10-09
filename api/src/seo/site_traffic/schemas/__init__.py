from datetime import date
from typing import Any, Literal

from pydantic import ConfigDict, field_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel
from src.seo.site_traffic.reports import TRAFFIC_REPORTS

MAX_ROWS_PER_BATCH = 20_000

SYNC_END_STATUSES = ("completed", "failed", "cancelled")

RollupKind = Literal["channel", "source", "event", "country", "device", "os", "browser"]
LandingSort = Literal["sessions", "keyEvents", "revenue", "delta"]
ContentSort = Literal["views", "users", "keyEvents", "delta"]


class TrafficSyncRecord(EntityModel):
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
    first_day: date | None = None
    last_day: date | None = None
    error: str | None = None
    notes: list[Any]
    created_at: JsDateTime
    updated_at: JsDateTime


class TrafficSyncResponse(TrafficSyncRecord):
    pass


class TrafficSyncJobsResponse(EntityModel):
    latest: TrafficSyncResponse | None
    active: TrafficSyncResponse | None


class TrafficSyncStartRequest(RequestModel):
    trigger: str | None = None


class TrafficSyncStartResult(EntityModel):
    started: bool
    sync: TrafficSyncRecord | None
    reason: str | None = None


class TrafficSyncStartResponse(EntityModel):
    started: bool
    sync: TrafficSyncResponse | None
    reason: str | None = None


class TrafficSyncUpdateRequest(RequestModel):
    days_done: int | None = None
    rows_stored: int | None = None
    property: str | None = None
    status: str | None = None
    error: str | None = None
    notes: list[Any] | None = None

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, v: Any) -> str | None:
        if v is None or v == "":
            return None
        if not isinstance(v, str) or v not in SYNC_END_STATUSES:
            raise ValueError("status must be completed, failed or cancelled.")
        return v


class TrafficSyncClaimResult(EntityModel):
    sync: TrafficSyncRecord
    property: str | None
    domain: str
    start_day: str
    end_day: str
    resume_from: str | None
    days_total: int


class TrafficSyncClaimResponse(EntityModel):
    sync: TrafficSyncResponse
    property: str | None
    domain: str
    start_day: str
    end_day: str
    resume_from: str | None
    days_total: int


class TrafficPropertyResponse(EntityModel):
    property: str | None
    domain: str


class TrafficPropertyUpdateRequest(RequestModel):
    property: str

    @field_validator("property", mode="before")
    @classmethod
    def _validate_property(cls, v: Any) -> str:
        clean = ("" if v is None else str(v)).strip()
        if not clean:
            raise ValueError(
                "property is required — the Analytics property this website reports on."
            )
        return clean


class TrafficPropertyUpdateResponse(EntityModel):
    property: str


class TrafficRowsIngestRequest(RequestModel):
    report: str
    rows: list[dict[str, Any]]

    @field_validator("report", mode="before")
    @classmethod
    def _validate_report(cls, v: Any) -> str:
        if v not in TRAFFIC_REPORTS:
            raise ValueError(f"report must be one of: {', '.join(TRAFFIC_REPORTS)}.")
        return v

    @field_validator("rows", mode="before")
    @classmethod
    def _validate_rows(cls, v: Any) -> list[Any]:
        rows = v if isinstance(v, list) else []
        if len(rows) == 0:
            raise ValueError("Send `rows: [...]` — a batch with no rows writes nothing.")
        if len(rows) > MAX_ROWS_PER_BATCH:
            raise ValueError(
                f"At most {MAX_ROWS_PER_BATCH} rows per batch — post the report in pages."
            )
        return [r if isinstance(r, dict) else {} for r in rows]


class TrafficRowsIngestResponse(EntityModel):
    stored: int


class TrafficReportRow(EntityModel):
    model_config = ConfigDict(
        alias_generator=None, populate_by_name=True, from_attributes=True, extra="allow"
    )

    day: str


class TrafficReportRowsResult(EntityModel):
    rows: list[TrafficReportRow]
    total: int


class TrafficRowsExportResponse(EntityModel):
    report: str
    rows: list[TrafficReportRow]
    total: int


class TrafficDayRange(EntityModel):
    first_day: str | None
    last_day: str | None
    days_stored: int
    sessions_28d: int


class TrafficTotals(EntityModel):
    users: int = 0
    new_users: int = 0
    sessions: int = 0
    engaged_sessions: int = 0
    page_views: int = 0
    engagement_seconds: float = 0
    key_events: float = 0
    revenue: float = 0


class TrafficChannelTotals(EntityModel):
    sessions: int = 0
    engaged_sessions: int = 0
    key_events: float = 0
    revenue: float = 0


class TrafficTotalsComparison(EntityModel):
    current: TrafficTotals
    previous: TrafficTotals


class TrafficChannelComparison(EntityModel):
    current: TrafficChannelTotals
    previous: TrafficChannelTotals


class TrafficRollupRow(EntityModel):
    key: list[str]
    sessions: int
    prev_sessions: int
    users: int
    engaged_sessions: int
    key_events: float
    revenue: float


class TrafficRollupResult(EntityModel):
    rows: list[TrafficRollupRow]
    total: int


class TrafficOverviewResponse(EntityModel):
    connected: bool
    property: str | None
    has_data: bool
    days: int
    first_day: str | None
    last_day: str | None
    days_stored: int
    totals: TrafficTotalsComparison
    organic: TrafficChannelComparison
    channels: list[TrafficRollupRow]
    sync: TrafficSyncRecord | None
    active: TrafficSyncRecord | None


class TrafficSeriesPoint(EntityModel):
    day: str
    users: int
    sessions: int
    engaged_sessions: int
    page_views: int
    key_events: float
    revenue: float
    organic_sessions: int


class TrafficSeriesResponse(EntityModel):
    days: int
    last_day: str | None
    points: list[TrafficSeriesPoint]


class TrafficBreakdownResponse(EntityModel):
    by: str
    days: int
    last_day: str | None
    rows: list[TrafficRollupRow]
    total: int


class TrafficLandingPageRow(EntityModel):
    landing_page: str
    page_id: str | None
    url: str | None
    title: str | None
    sessions: int
    prev_sessions: int
    engaged_sessions: int
    key_events: float
    prev_key_events: float
    revenue: float
    prev_revenue: float


class TrafficLandingPagesResult(EntityModel):
    rows: list[TrafficLandingPageRow]
    total: int


class TrafficLandingPagesResponse(EntityModel):
    pages: list[TrafficLandingPageRow]
    total: int
    last_day: str | None
    days: int


class TrafficContentPageRow(EntityModel):
    page_path: str
    views: int
    prev_views: int
    users: int
    engagement_seconds: float
    key_events: float


class TrafficContentPagesResult(EntityModel):
    rows: list[TrafficContentPageRow]
    total: int


class TrafficContentPagesResponse(EntityModel):
    pages: list[TrafficContentPageRow]
    total: int
    last_day: str | None
    days: int
