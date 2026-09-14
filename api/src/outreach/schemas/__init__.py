from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel

CAMPAIGN_STATUSES = ("running", "done", "failed")
PROSPECT_STATUSES = ("found", "contacted", "replied", "won", "rejected")
CONVERSATION_STATUSES = ("draft", "sent", "received")
MAX_REQUESTED_COUNT = 100


def _text(value: Any, field: str) -> str:
    text = ("" if value is None else str(value)).strip()
    if not text:
        raise ValueError(f"{field} is required.")
    return text


def _status(value: Any, allowed: tuple[str, ...]) -> str:
    if value not in allowed:
        raise ValueError(f"Invalid status. Allowed values: {', '.join(allowed)}.")
    return value


def _whole_number(value: Any) -> int:
    number = None
    if not isinstance(value, bool):
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = None
    if number is None or number != number or number in (float("inf"), float("-inf")):
        raise ValueError(
            f"requestedCount must be a whole number between 1 and {MAX_REQUESTED_COUNT}."
        )
    count = int(number // 1)
    if count < 1 or count > MAX_REQUESTED_COUNT:
        raise ValueError(
            f"requestedCount must be a whole number between 1 and {MAX_REQUESTED_COUNT}."
        )
    return count


def _message_id(raw: Any) -> str | None:
    value = raw.strip() if isinstance(raw, str) else ""
    value = value.removeprefix("<")
    value = value.removesuffix(">")
    return value or None


class OutreachProjectCreateRequest(RequestModel):
    name: str
    prospect_profile: str
    goal: str | None = None
    prompt: str | None = None
    search_criteria: str | None = None
    email_tone: str | None = None
    value_prop: str | None = None
    cta: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> str:
        return _text(v, "name")

    @field_validator("prospect_profile", mode="before")
    @classmethod
    def _validate_profile(cls, v: Any) -> str:
        return _text(v, "prospectProfile")


class OutreachProjectUpdateRequest(RequestModel):
    name: str | None = None
    prospect_profile: str | None = None
    goal: str | None = None
    prompt: str | None = None
    search_criteria: str | None = None
    email_tone: str | None = None
    value_prop: str | None = None
    cta: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> str | None:
        return None if v is None else _text(v, "name")

    @field_validator("prospect_profile", mode="before")
    @classmethod
    def _validate_profile(cls, v: Any) -> str | None:
        return None if v is None else _text(v, "prospectProfile")

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class OutreachProjectRecord(EntityModel):
    id: str
    user_id: str
    site_id: str
    name: str
    goal: str | None
    prompt: str | None
    prospect_profile: str
    search_criteria: str | None
    email_tone: str | None
    value_prop: str | None
    cta: str | None
    created_at: JsDateTime
    updated_at: JsDateTime


class OutreachProjectResponse(EntityModel):
    id: str
    site_id: str
    name: str
    goal: str | None
    prompt: str | None
    prospect_profile: str
    search_criteria: str | None
    email_tone: str | None
    value_prop: str | None
    cta: str | None
    created_at: JsDateTime
    updated_at: JsDateTime


class OutreachProjectListItemResponse(OutreachProjectResponse):
    pass


class OutreachProjectDeleteResponse(EntityModel):
    id: str
    deleted: bool = Field(default=True)


class CampaignCreateRequest(RequestModel):
    project_id: str
    requested_count: int

    @field_validator("project_id", mode="before")
    @classmethod
    def _validate_project(cls, v: Any) -> str:
        return _text(v, "projectId")

    @field_validator("requested_count", mode="before")
    @classmethod
    def _validate_count(cls, v: Any) -> int:
        return _whole_number(v)


class CampaignUpdateRequest(RequestModel):
    status: str | None = None
    summary: str | None = None

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, v: Any) -> str | None:
        return None if v is None else _status(v, CAMPAIGN_STATUSES)

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class CampaignRecord(EntityModel):
    id: str
    user_id: str
    site_id: str
    project_id: str
    requested_count: int
    status: str
    summary: str | None
    finished_at: JsDateTime | None
    created_at: JsDateTime
    updated_at: JsDateTime
    found: int = 0


class CampaignProspectCount(EntityModel):
    campaign_id: str
    found: int


class CampaignResponse(EntityModel):
    id: str
    site_id: str
    project_id: str
    requested_count: int
    status: str
    summary: str | None
    finished_at: JsDateTime | None
    found: int
    created_at: JsDateTime
    updated_at: JsDateTime


class CampaignListItemResponse(CampaignResponse):
    pass


class CampaignDeleteResponse(EntityModel):
    id: str
    deleted: bool = Field(default=True)


class ProspectCreateRequest(RequestModel):
    campaign_id: str
    name: str
    company: str | None = None
    role: str | None = None
    email: str | None = None
    website: str | None = None
    source_url: str | None = None
    fit_reason: str | None = None
    status: str = "found"

    @field_validator("campaign_id", mode="before")
    @classmethod
    def _validate_campaign(cls, v: Any) -> str:
        return _text(v, "campaignId")

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> str:
        return _text(v, "name")

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, v: Any) -> str:
        return "found" if v is None else _status(v, PROSPECT_STATUSES)


class ProspectBulkCreateRequest(RequestModel):
    prospects: list[ProspectCreateRequest]


class ProspectUpdateRequest(RequestModel):
    name: str | None = None
    company: str | None = None
    role: str | None = None
    email: str | None = None
    website: str | None = None
    source_url: str | None = None
    fit_reason: str | None = None
    status: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> str | None:
        return None if v is None else _text(v, "name")

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, v: Any) -> str | None:
        return None if v is None else _status(v, PROSPECT_STATUSES)

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class ProspectRecord(EntityModel):
    id: str
    user_id: str
    site_id: str
    campaign_id: str
    name: str
    company: str | None
    role: str | None
    email: str | None
    website: str | None
    source_url: str | None
    fit_reason: str | None
    status: str
    dedupe_keys: list[str]
    created_at: JsDateTime
    updated_at: JsDateTime


class ProspectResponse(EntityModel):
    id: str
    site_id: str
    campaign_id: str
    name: str
    company: str | None
    role: str | None
    email: str | None
    website: str | None
    source_url: str | None
    fit_reason: str | None
    status: str
    dedupe_keys: list[str]
    created_at: JsDateTime
    updated_at: JsDateTime


class ProspectListItemResponse(ProspectResponse):
    pass


class ProspectDeleteResponse(EntityModel):
    id: str
    deleted: bool = Field(default=True)


class ProspectSkipped(EntityModel):
    name: str
    reason: str


class ProspectBulkCreateResult(EntityModel):
    created: list[ProspectRecord]
    skipped: list[ProspectSkipped]


class ProspectBulkCreateResponse(EntityModel):
    created: list[ProspectResponse]
    skipped: list[ProspectSkipped]


class KnownProspectItem(EntityModel):
    id: str
    name: str
    company: str | None
    email: str | None
    website: str | None
    status: str
    campaign_id: str
    dedupe_keys: list[str]


class KnownProspectsResponse(EntityModel):
    project_id: str
    project_name: str
    count: int
    exclude_emails: list[str]
    exclude_domains: list[str]
    exclude_companies: list[str]
    prospects: list[KnownProspectItem]


class ConversationCreateRequest(RequestModel):
    prospect_id: str
    subject: str
    body: str
    status: str = "draft"
    from_: str | None = Field(default=None, alias="from")
    to: str | None = None
    cc: str | None = None
    bcc: str | None = None
    message_id: str | None = None
    thread_ref: str | None = None
    occurred_at: datetime | None = None

    @field_validator("prospect_id", mode="before")
    @classmethod
    def _validate_prospect(cls, v: Any) -> str:
        return _text(v, "prospectId")

    @field_validator("subject", mode="before")
    @classmethod
    def _validate_subject(cls, v: Any) -> str:
        return _text(v, "subject")

    @field_validator("body", mode="before")
    @classmethod
    def _validate_body(cls, v: Any) -> str:
        return _text(v, "body")

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, v: Any) -> str:
        return "draft" if v is None else _status(v, CONVERSATION_STATUSES)

    @field_validator("message_id", "thread_ref", mode="before")
    @classmethod
    def _validate_message_ids(cls, v: Any) -> str | None:
        return _message_id(v)


class ConversationSyncMessage(RequestModel):
    prospect_id: str
    message_id: str | None = None
    subject: str | None = None
    body: str | None = None
    from_: str | None = Field(default=None, alias="from")
    to: str | None = None
    cc: str | None = None
    bcc: str | None = None
    thread_ref: str | None = None
    occurred_at: datetime | None = None

    @field_validator("prospect_id", mode="before")
    @classmethod
    def _validate_prospect(cls, v: Any) -> str:
        return _text(v, "prospectId")

    @field_validator("message_id", "thread_ref", mode="before")
    @classmethod
    def _validate_message_ids(cls, v: Any) -> str | None:
        return _message_id(v)


class ConversationSyncRequest(RequestModel):
    messages: list[ConversationSyncMessage]


class ConversationUpdateRequest(RequestModel):
    status: str | None = None
    from_: str | None = Field(default=None, alias="from")
    to: str | None = None
    cc: str | None = None
    bcc: str | None = None
    subject: str | None = None
    body: str | None = None
    message_id: str | None = None
    thread_ref: str | None = None

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, v: Any) -> str | None:
        return None if v is None else _status(v, CONVERSATION_STATUSES)

    @field_validator("subject", mode="before")
    @classmethod
    def _validate_subject(cls, v: Any) -> str | None:
        return None if v is None else _text(v, "subject")

    @field_validator("body", mode="before")
    @classmethod
    def _validate_body(cls, v: Any) -> str | None:
        return None if v is None else _text(v, "body")

    @field_validator("message_id", "thread_ref", mode="before")
    @classmethod
    def _validate_message_ids(cls, v: Any) -> str | None:
        return _message_id(v)

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class ConversationRecord(EntityModel):
    id: str
    user_id: str
    site_id: str
    prospect_id: str
    status: str
    from_: str | None = Field(default=None, alias="from")
    to: str | None
    cc: str | None
    bcc: str | None
    subject: str
    body: str
    message_id: str | None
    thread_ref: str | None
    created_at: JsDateTime
    updated_at: JsDateTime


class ConversationResponse(EntityModel):
    id: str
    site_id: str
    prospect_id: str
    status: str
    from_: str | None = Field(default=None, alias="from")
    to: str | None
    cc: str | None
    bcc: str | None
    subject: str
    body: str
    message_id: str | None
    thread_ref: str | None
    created_at: JsDateTime
    updated_at: JsDateTime


class ConversationListItemResponse(ConversationResponse):
    pass


class ConversationDeleteResponse(EntityModel):
    id: str
    deleted: bool = Field(default=True)


class ConversationSyncResult(EntityModel):
    added: list[ConversationRecord]
    skipped: int


class ConversationSyncResponse(EntityModel):
    added: list[ConversationResponse]
    skipped: int


class OutreachCounts(EntityModel):
    projects: int
    runs: int
    active_runs: int
    prospects: int
    drafts: int
    sent: int
    replies: int
