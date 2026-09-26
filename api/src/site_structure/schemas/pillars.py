from typing import Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel
from src.site_structure.constants import (
    PILLAR_BUDGET,
    PILLAR_MIN_COHESION,
    PILLAR_MIN_SIZE,
)
from src.site_structure.schemas import fields


class PillarMember(BaseModel):
    id: str
    url: str
    title: str | None = None


class PillarPageSuggestionRecord(EntityModel):
    id: str
    site_id: str
    job_id: str
    action: str
    topic: str
    member_page_ids: list[str]
    covering_page_id: str | None = None
    state: str
    suggestion: str
    search_score: float | None = None
    confidence: float | None = None
    score: float | None = None
    created_at: JsDateTime
    updated_at: JsDateTime
    covering_url: str | None = None
    members: list[PillarMember] = Field(default_factory=list)


class PillarPageSuggestionResponse(PillarPageSuggestionRecord):
    pass


class PillarPageSuggestionDeleteResponse(EntityModel):
    id: str
    deleted: bool = Field(default=True)


class PillarPageSuggestionFilter(BaseModel):
    state: str | None = "ready"
    action: str | None = None
    job_id: str | None = None
    sort_by: str = "score"
    sort_order: str = "desc"


class NewPillarPageSuggestion(BaseModel):
    job_id: str
    action: str = "create"
    topic: str
    member_page_ids: list[str]
    covering_page_id: str | None = None
    suggestion: str
    search_score: float | None = None
    state: str = "draft"


class PillarPageSuggestionChanges(BaseModel):
    state: str | None = None
    topic: str | None = None
    suggestion: str | None = None
    confidence: float | None = None
    score: float | None = None

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class PillarPageSuggestionUpdateRequest(RequestModel):
    state: str | None = None
    topic: str | None = None
    suggestion: str | None = None

    @field_validator("state", mode="before")
    @classmethod
    def _state(cls, value: Any) -> str:
        if fields.blank(value):
            raise ValueError("A state cannot be blank.")
        return fields.state(value)

    @field_validator("topic", "suggestion", mode="before")
    @classmethod
    def _text(cls, value: Any) -> str:
        return fields.suggestion(value)

    @model_validator(mode="after")
    def _something_to_change(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Nothing to change. Send state, topic or suggestion.")
        return self

    def to_changes(self) -> PillarPageSuggestionChanges:
        changes = PillarPageSuggestionChanges()
        for key in ("state", "topic", "suggestion"):
            value = getattr(self, key)
            if value is not None:
                setattr(changes, key, value)
        return changes


class PillarPageSuggestionSummaryResponse(EntityModel):
    draft: int = 0
    ready: int = 0
    llm_rejected: int = 0
    user_rejected: int = 0
    done: int = 0
    stale: int = 0


class PillarsRequest(RequestModel):
    job_id: str = Field(default="", validate_default=True)
    source_table: str | None = None
    min_size: int = Field(default=PILLAR_MIN_SIZE, ge=2, le=200)
    min_cohesion: float = Field(default=PILLAR_MIN_COHESION, ge=0.0, le=1.0)

    @field_validator("job_id", mode="before")
    @classmethod
    def _job(cls, value: Any) -> str:
        if fields.blank(value):
            raise ValueError("Send the jobId the suggestions belong to.")
        return str(value).strip()

    @field_validator("source_table", mode="before")
    @classmethod
    def _table(cls, value: Any) -> str | None:
        return None if fields.blank(value) else fields.workspace_table(value)


class PillarsResult(EntityModel):
    groups: int = 0
    inserted: int = 0
    too_small: int = 0
    too_loose: int = 0
    covered: int = 0
    structural: int = 0
    overlaps_open: int = 0
    overlaps_rejected: int = 0


class WorkspaceGroup(BaseModel):
    key: str
    topic: str | None = None
    page_ids: list[str] = Field(default_factory=list)


class PillarScreenRequest(RequestModel):
    job_id: str | None = None
    ids: list[str] | None = None
    limit: int = Field(default=100, ge=1, le=500)


class PillarReviewInputsRequest(RequestModel):
    prompt: str = Field(default="", validate_default=True)
    job_id: str | None = None
    ids: list[str] | None = None
    limit: int = Field(default=100, ge=1, le=500)

    @field_validator("prompt", mode="before")
    @classmethod
    def _prompt(cls, value: Any) -> str:
        return fields.prompt(value)


class PillarVerdict(RequestModel):
    id: str
    verdict: str
    title: str | None = None
    suggestion: str | None = None


class PillarVerdictRequest(RequestModel):
    verdicts: list[PillarVerdict] = Field(default_factory=list)


class PillarRankRequest(RequestModel):
    budget: int = Field(default=PILLAR_BUDGET, ge=1, le=50)


class PillarReviewInput(BaseModel):
    id: str
    action: str
    topic: str
    suggestion: str
    search_score: float | None
    covering_url: str | None
    covering_title: str | None
    members: list[dict[str, Any]]
