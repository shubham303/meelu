from datetime import datetime
from typing import Any

from pydantic import Field

from src.core.schemas import EntityModel, JsDateTime, RequestModel

CAMPAIGN_STATUSES = ("active", "paused", "archived")
RUN_STATUSES = ("running", "done", "stopped", "error")
LEAD_STAGES = ("found", "qualified", "shortlisted")
LEAD_SORTS = ("fit", "newest")


class CampaignCreateRequest(RequestModel):
    name: str
    audience: str
    status: str = "active"
    sources: list[str] = Field(default_factory=list)
    schedule: str | None = None


class CampaignPatchRequest(RequestModel):
    name: str | None = None
    status: str | None = None
    audience: str | None = None
    sources: list[str] | None = None
    schedule: str | None = None

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class RunCreateRequest(RequestModel):
    campaign_id: str


class RunUpdateRequest(RequestModel):
    status: str | None = None
    finished_at: datetime | None = None
    found: int | None = None
    qualified: int | None = None
    skipped_known: int | None = None
    source_stats: dict[str, Any] | None = None
    error: str | None = None

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class LeadUpsertItem(RequestModel):
    name: str
    company: str | None = None
    role: str | None = None
    email: str | None = None
    email_verified: bool = False
    website: str | None = None
    source: str | None = None
    source_url: str | None = None
    channel_handles: dict[str, str] = Field(default_factory=dict)
    fit_score: float | None = None
    fit_reason: str | None = None
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    stage: str | None = None
    note: str | None = None


class LeadsBulkRequest(RequestModel):
    run_id: str | None = None
    campaign_id: str | None = None
    leads: list[LeadUpsertItem]


class LeadCreateRequest(LeadUpsertItem):
    campaign_id: str | None = None


class LeadPatchRequest(RequestModel):
    stage: str | None = None
    name: str | None = None
    company: str | None = None
    role: str | None = None
    email: str | None = None
    email_verified: bool | None = None
    website: str | None = None
    note: str | None = None
    fit_score: float | None = None
    fit_reason: str | None = None
    evidence: list[dict[str, Any]] | None = None
    channel_handles: dict[str, str] | None = None

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class LeadFilters(RequestModel):
    stage: str | None = None
    campaign_id: str | None = None
    source: str | None = None
    q: str | None = None
    has_email: bool | None = None
    min_fit: float | None = None
    sort: str | None = None


class CampaignResponse(EntityModel):
    id: str
    site_id: str
    name: str
    status: str
    audience: str
    sources: list[str]
    schedule: str | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class RunResponse(EntityModel):
    id: str
    site_id: str
    campaign_id: str
    status: str
    started_at: JsDateTime
    finished_at: JsDateTime | None = None
    found: int
    qualified: int
    skipped_known: int
    source_stats: dict[str, Any]
    error: str | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class LeadResponse(EntityModel):
    id: str
    site_id: str
    campaign_id: str | None = None
    run_id: str | None = None
    name: str
    company: str | None = None
    role: str | None = None
    email: str | None = None
    email_verified: bool
    website: str | None = None
    source: str | None = None
    source_url: str | None = None
    channel_handles: dict[str, str]
    fit_score: float | None = None
    fit_reason: str | None = None
    evidence: list[dict[str, Any]]
    stage: str
    stage_changed_at: JsDateTime | None = None
    note: str | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class BulkLeadsResponse(EntityModel):
    inserted: int
    skipped: int


class DeleteResponse(EntityModel):
    id: str


class StageCounts(EntityModel):
    found: int
    qualified: int
    shortlisted: int


class CampaignFunnel(EntityModel):
    id: str
    name: str
    status: str
    qualified: int
    shortlisted: int


class SummaryResponse(EntityModel):
    stages: StageCounts
    last_run: RunResponse | None = None
    campaigns: list[CampaignFunnel]
