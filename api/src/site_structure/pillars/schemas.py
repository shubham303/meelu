from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel
from src.site_structure.constants import (
    PILLAR_BUDGET,
    PILLAR_MIN_COHESION,
    PILLAR_MIN_SIZE,
    VISIBLE_STATES,
    PillarAction,
    SuggestionState,
)
from src.site_structure.pipeline.review import VERDICTS
from src.site_structure.pipeline.schemas import review_prompt, workspace_table
from src.site_structure.schemas.fields import blank, choice

MAX_SUGGESTION_CHARS = 4_000

MAX_TOPIC_CHARS = 200

MIN_MEMBERS = 2


class PillarSortBy(StrEnum):
    SCORE = "score"
    SEARCH_SCORE = "searchScore"
    CONFIDENCE = "confidence"
    CREATED_AT = "createdAt"
    UPDATED_AT = "updatedAt"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class PillarMember(EntityModel):
    id: str
    url: str
    title: str | None = None


class PillarPageSuggestionRecord(EntityModel):
    id: str
    site_id: str
    job_id: str
    action: PillarAction
    topic: str
    member_page_ids: list[str]
    covering_page_id: str | None = None
    state: SuggestionState
    suggestion: str
    search_score: float | None = None
    confidence: float | None = None
    score: float | None = None
    created_at: JsDateTime
    updated_at: JsDateTime
    covering_url: str | None = None
    members: list[PillarMember] = Field(default_factory=list)


class PillarPageSuggestionFilter(BaseModel):
    states: frozenset[SuggestionState] | None = VISIBLE_STATES
    action: PillarAction | None = None
    job_id: str | None = None
    page_id: str | None = None
    sort_by: PillarSortBy = PillarSortBy.SCORE
    sort_order: SortOrder = SortOrder.DESC


class NewPillarPageSuggestion(BaseModel):
    job_id: str
    action: PillarAction = PillarAction.CREATE
    topic: str
    member_page_ids: list[str]
    covering_page_id: str | None = None
    suggestion: str
    search_score: float | None = None
    state: SuggestionState = SuggestionState.DRAFT


class PillarPageSuggestionChanges(BaseModel):
    state: SuggestionState | None = None
    topic: str | None = None
    suggestion: str | None = None
    confidence: float | None = None
    score: float | None = None

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


def _suggestion_text(value: Any) -> str:
    text = str(value if value is not None else "").strip()
    if not text:
        raise ValueError("A suggestion needs a description.")
    return text[:MAX_SUGGESTION_CHARS]


def _topic_text(value: Any) -> str:
    text = str(value if value is not None else "").strip()
    if not text:
        raise ValueError("A pillar needs a topic.")
    return text[:MAX_TOPIC_CHARS]


class PillarPageSuggestionCreateRequest(RequestModel):
    job_id: str = Field(default="", validate_default=True)
    action: PillarAction = PillarAction.CREATE
    topic: str = Field(default="", validate_default=True)
    member_page_ids: list[str] = Field(default_factory=list, validate_default=True)
    covering_page_id: str | None = None
    suggestion: str = Field(default="", validate_default=True)
    search_score: float | None = None
    state: SuggestionState = SuggestionState.DRAFT

    @field_validator("job_id", mode="before")
    @classmethod
    def _job(cls, value: Any) -> str:
        if blank(value):
            raise ValueError("A suggestion belongs to a job: send jobId.")
        return str(value).strip()

    @field_validator("action", mode="before")
    @classmethod
    def _action(cls, value: Any) -> PillarAction:
        return PillarAction.CREATE if blank(value) else choice(PillarAction, value, "action")

    @field_validator("state", mode="before")
    @classmethod
    def _state(cls, value: Any) -> SuggestionState:
        return SuggestionState.DRAFT if blank(value) else choice(SuggestionState, value, "state")

    @field_validator("topic", mode="before")
    @classmethod
    def _topic(cls, value: Any) -> str:
        return _topic_text(value)

    @field_validator("suggestion", mode="before")
    @classmethod
    def _suggestion(cls, value: Any) -> str:
        return _suggestion_text(value)

    @field_validator("member_page_ids", mode="before")
    @classmethod
    def _members(cls, value: Any) -> list[str]:
        ids = sorted({str(v).strip() for v in value or [] if not blank(v)})
        if len(ids) < MIN_MEMBERS:
            raise ValueError(f"A pillar groups at least {MIN_MEMBERS} pages: send memberPageIds.")
        return ids

    @field_validator("covering_page_id", mode="before")
    @classmethod
    def _covering(cls, value: Any) -> str | None:
        return None if blank(value) else str(value).strip()

    @model_validator(mode="after")
    def _covering_matches_action(self) -> Self:
        if self.action is PillarAction.EXPAND and not self.covering_page_id:
            raise ValueError('An "expand" suggestion names the page to grow: send coveringPageId.')
        if self.action is PillarAction.CREATE and self.covering_page_id:
            raise ValueError('A "create" suggestion is for a new page: drop coveringPageId.')
        return self

    def to_new(self) -> NewPillarPageSuggestion:
        return NewPillarPageSuggestion(
            job_id=self.job_id,
            action=self.action,
            topic=self.topic,
            member_page_ids=self.member_page_ids,
            covering_page_id=self.covering_page_id,
            suggestion=self.suggestion,
            search_score=self.search_score,
            state=self.state,
        )


class PillarPageSuggestionUpdateRequest(RequestModel):
    state: SuggestionState | None = None
    topic: str | None = None
    suggestion: str | None = None

    @field_validator("state", mode="before")
    @classmethod
    def _state(cls, value: Any) -> SuggestionState:
        if blank(value):
            raise ValueError("A state cannot be blank.")
        return choice(SuggestionState, value, "state")

    @field_validator("topic", mode="before")
    @classmethod
    def _topic(cls, value: Any) -> str:
        return _topic_text(value)

    @field_validator("suggestion", mode="before")
    @classmethod
    def _suggestion(cls, value: Any) -> str:
        return _suggestion_text(value)

    @model_validator(mode="after")
    def _something_to_change(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Nothing to change. Send state, topic or suggestion.")
        return self

    def to_changes(self) -> PillarPageSuggestionChanges:
        return PillarPageSuggestionChanges(
            **{key: getattr(self, key) for key in self.model_fields_set}
        )


class PillarPageSuggestionDeleteResponse(EntityModel):
    id: str
    deleted: bool = True


class PillarPageSuggestionSummaryResponse(EntityModel):
    draft: int = 0
    screening_rejected: int = 0
    screening_approved: int = 0
    review_approved: int = 0
    review_rejected: int = 0
    user_rejected: int = 0


class ReconcileResult(EntityModel):
    removed: int = 0


class PillarsRequest(RequestModel):
    job_id: str = Field(default="", validate_default=True)
    source_table: str | None = None
    min_size: int = Field(default=PILLAR_MIN_SIZE, ge=2, le=200)
    min_cohesion: float = Field(default=PILLAR_MIN_COHESION, ge=0.0, le=1.0)

    @field_validator("job_id", mode="before")
    @classmethod
    def _job(cls, value: Any) -> str:
        if blank(value):
            raise ValueError("Send the jobId the suggestions belong to.")
        return str(value).strip()

    @field_validator("source_table", mode="before")
    @classmethod
    def _table(cls, value: Any) -> str | None:
        return None if blank(value) else workspace_table(value)


class PillarsResult(EntityModel):
    groups: int = 0
    inserted: int = 0
    too_small: int = 0
    too_loose: int = 0
    covered: int = 0
    structural_pages: int = 0
    mixed_types: int = 0
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
        return review_prompt(value)


class PillarVerdict(RequestModel):
    id: str
    verdict: SuggestionState
    title: str | None = None
    suggestion: str | None = None

    @field_validator("verdict", mode="before")
    @classmethod
    def _verdict(cls, value: Any) -> SuggestionState:
        verdict = choice(SuggestionState, value, "verdict")
        if verdict not in VERDICTS:
            raise ValueError(f"A verdict is one of: {', '.join(VERDICTS)}.")
        return verdict


class PillarVerdictRequest(RequestModel):
    verdicts: list[PillarVerdict] = Field(default_factory=list)


class PillarRankRequest(RequestModel):
    budget: int = Field(default=PILLAR_BUDGET, ge=1, le=50)


class PillarReviewInput(BaseModel):
    id: str
    action: PillarAction
    topic: str
    suggestion: str
    search_score: float | None
    covering_url: str | None
    covering_title: str | None
    covering_details: str | None
    members: list[dict[str, Any]]
