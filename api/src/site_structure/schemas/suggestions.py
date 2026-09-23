from typing import Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel
from src.site_structure.schemas import fields


class LinkSuggestionRecord(EntityModel):
    id: str
    site_id: str
    job_id: str
    from_page_id: str
    from_chunk_id: str | None = None
    to_page_id: str
    action: str
    state: str
    suggestion: str
    search_score: float | None = None
    confidence: float | None = None
    score: float | None = None
    created_at: JsDateTime
    updated_at: JsDateTime
    from_url: str | None = None
    to_url: str | None = None
    from_chunk_heading: str | None = None
    from_chunk_ordinal: int | None = None


class LinkSuggestionResponse(LinkSuggestionRecord):
    pass


class LinkSuggestionDeleteResponse(EntityModel):
    id: str
    deleted: bool = Field(default=True)


class LinkSuggestionFilter(BaseModel):
    state: str | None = "ready"
    action: str | None = None
    job_id: str | None = None
    from_page_id: str | None = None
    to_page_id: str | None = None
    page_id: str | None = None
    url: str | None = None


class NewLinkSuggestion(BaseModel):
    job_id: str
    from_page_id: str
    to_page_id: str
    from_chunk_id: str | None = None
    action: str = "create"
    suggestion: str
    search_score: float | None = None
    state: str = "draft"


class LinkSuggestionChanges(BaseModel):
    state: str | None = None
    suggestion: str | None = None
    from_chunk_id: str | None = None
    confidence: float | None = None
    score: float | None = None

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class LinkSuggestionCreateRequest(RequestModel):
    job_id: str = Field(default="", validate_default=True)
    from_page_id: str | None = None
    from_url: str | None = None
    to_page_id: str | None = None
    to_url: str | None = None
    from_chunk_id: str | None = None
    action: str = "create"
    suggestion: str = Field(default="", validate_default=True)
    search_score: float | None = None
    state: str = "draft"

    @field_validator("job_id", mode="before")
    @classmethod
    def _job(cls, value: Any) -> str:
        if fields.blank(value):
            raise ValueError("A suggestion belongs to a job: send jobId.")
        return str(value).strip()

    @field_validator("action", mode="before")
    @classmethod
    def _action(cls, value: Any) -> str:
        return "create" if fields.blank(value) else fields.action(value)

    @field_validator("suggestion", mode="before")
    @classmethod
    def _suggestion(cls, value: Any) -> str:
        return fields.suggestion(value)

    @field_validator("state", mode="before")
    @classmethod
    def _state(cls, value: Any) -> str:
        return "draft" if fields.blank(value) else fields.state(value)

    @field_validator(
        "from_page_id", "from_url", "to_page_id", "to_url", "from_chunk_id", mode="before"
    )
    @classmethod
    def _optional_text(cls, value: Any) -> str | None:
        return None if fields.blank(value) else str(value).strip()

    def to_new(self, from_page_id: str, to_page_id: str) -> NewLinkSuggestion:
        return NewLinkSuggestion(
            job_id=self.job_id,
            from_page_id=from_page_id,
            to_page_id=to_page_id,
            from_chunk_id=self.from_chunk_id,
            action=self.action,
            suggestion=self.suggestion,
            search_score=self.search_score,
            state=self.state,
        )


class LinkSuggestionUpdateRequest(RequestModel):
    state: str | None = None
    suggestion: str | None = None
    from_chunk_id: str | None = None

    @field_validator("state", mode="before")
    @classmethod
    def _state(cls, value: Any) -> str:
        if fields.blank(value):
            raise ValueError("A state cannot be blank.")
        return fields.state(value)

    @field_validator("suggestion", mode="before")
    @classmethod
    def _suggestion(cls, value: Any) -> str:
        return fields.suggestion(value)

    @field_validator("from_chunk_id", mode="before")
    @classmethod
    def _chunk(cls, value: Any) -> str | None:
        return None if fields.blank(value) else str(value).strip()

    @model_validator(mode="after")
    def _something_to_change(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Nothing to change. Send state, suggestion or fromChunkId.")
        return self

    def to_changes(self) -> LinkSuggestionChanges:
        changes = LinkSuggestionChanges()
        if self.state is not None:
            changes.state = self.state
        if self.suggestion is not None:
            changes.suggestion = self.suggestion
        if "from_chunk_id" in self.model_fields_set:
            changes.from_chunk_id = self.from_chunk_id
        return changes


class LinkSuggestionSummaryResponse(EntityModel):
    draft: int = 0
    ready: int = 0
    llm_rejected: int = 0
    user_rejected: int = 0
    done: int = 0
    stale: int = 0


class ScreenRequest(RequestModel):
    job_id: str | None = None
    ids: list[str] | None = None
    limit: int = Field(default=200, ge=1, le=1000)
    question: str | None = None


class ScreeningInput(BaseModel):
    id: str
    action: str
    suggestion: str
    from_url: str
    from_title: str | None
    from_content_hash: str | None
    from_text: str
    anchor: str | None = None
    to_url: str
    to_title: str | None
    to_meta_description: str | None
    to_h1: list[str]
    to_kind: str
    to_content_hash: str | None


class ScreenResult(EntityModel):
    screened: int = 0
    passed: int = 0
    llm_rejected: int = 0
    failed: int = 0
    stopped: str | None = None


class ReviewRequest(RequestModel):
    prompt: str = Field(default="", validate_default=True)
    job_id: str | None = None
    ids: list[str] | None = None
    limit: int = Field(default=200, ge=1, le=1000)

    @field_validator("prompt", mode="before")
    @classmethod
    def _prompt(cls, value: Any) -> str:
        return fields.prompt(value)


class ReviewResult(EntityModel):
    reviewed: int = 0
    ready: int = 0
    llm_rejected: int = 0
    failed: int = 0
    stopped: str | None = None


class RankRequest(RequestModel):
    max_per_target: int | None = Field(default=None, ge=1)
    target_discount: float = Field(default=1.0, ge=0.0, le=3.0)


class RankResult(EntityModel):
    scored: int = 0
    kept: int = 0
    llm_rejected: int = 0


class RemovalsRequest(RequestModel):
    job_id: str = Field(default="", validate_default=True)
    source_table: str = Field(default="", validate_default=True)

    @field_validator("job_id", mode="before")
    @classmethod
    def _job(cls, value: Any) -> str:
        if fields.blank(value):
            raise ValueError("Send the jobId the suggestions belong to.")
        return str(value).strip()

    @field_validator("source_table", mode="before")
    @classmethod
    def _table(cls, value: Any) -> str:
        return fields.workspace_table(value)


class RemovalsResult(EntityModel):
    read: int = 0
    inserted: int = 0
    skipped: int = 0
    not_body_links: int = 0
    last_inlink: int = 0
    to_hub_or_home: int = 0


class WorkspaceEdge(BaseModel):
    from_page_id: str
    to_page_id: str
    reason: str | None = None


class EdgeFacts(BaseModel):
    from_page_id: str
    to_page_id: str
    region: str
    anchor: str | None
    to_url: str
    to_inlinks: int
    to_is_hub: bool


class MentionsRequest(RequestModel):
    job_id: str = Field(default="", validate_default=True)
    to_ids: list[str] = Field(default_factory=list)
    phrases: list[str] = Field(default_factory=list)
    limit_per_target: int = Field(default=50, ge=1, le=500)

    @field_validator("job_id", mode="before")
    @classmethod
    def _job(cls, value: Any) -> str:
        if fields.blank(value):
            raise ValueError("Send the jobId the suggestions belong to.")
        return str(value).strip()

    @field_validator("to_ids", "phrases", mode="before")
    @classmethod
    def _non_empty(cls, value: Any) -> list[str]:
        items = [str(v).strip() for v in (value or []) if not fields.blank(v)]
        if not items:
            raise ValueError("Give at least one item.")
        return items


class MentionsResult(EntityModel):
    inserted: int = 0
    skipped: int = 0
    targets_without_match: list[str] = Field(default_factory=list)


class HierarchyPage(BaseModel):
    id: str
    url: str
    kind: str
    page_type: str | None


class HierarchyRequest(RequestModel):
    job_id: str = Field(default="", validate_default=True)

    @field_validator("job_id", mode="before")
    @classmethod
    def _job(cls, value: Any) -> str:
        if fields.blank(value):
            raise ValueError("Send the jobId the suggestions belong to.")
        return str(value).strip()


class HierarchyResult(EntityModel):
    inserted: int = 0
    skipped: int = 0
    home_found: bool = False
    hubs: int = 0
