from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel
from src.site_structure.constants import VISIBLE_STATES, SuggestionState
from src.site_structure.pipeline.review import VERDICTS
from src.site_structure.pipeline.schemas import review_prompt, workspace_table
from src.site_structure.schemas.fields import blank, choice

MAX_SUGGESTION_CHARS = 4_000


class LinkAction(StrEnum):
    CREATE = "create"
    DELETE = "delete"


class LinkSortBy(StrEnum):
    SCORE = "score"
    SEARCH_SCORE = "searchScore"
    CONFIDENCE = "confidence"
    CREATED_AT = "createdAt"
    UPDATED_AT = "updatedAt"


class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"


class LinkSuggestionRecord(EntityModel):
    id: str
    site_id: str
    job_id: str
    from_page_id: str
    from_chunk_id: str | None = None
    to_page_id: str
    action: LinkAction
    state: SuggestionState
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
    from_chunk_text: str | None = None
    anchor: str | None = None


class LinkSuggestionFilter(BaseModel):
    states: frozenset[SuggestionState] | None = VISIBLE_STATES
    action: LinkAction | None = None
    job_id: str | None = None
    from_page_id: str | None = None
    to_page_id: str | None = None
    page_id: str | None = None
    from_url: str | None = None
    to_url: str | None = None
    url: str | None = None
    sort_by: LinkSortBy = LinkSortBy.SCORE
    sort_order: SortOrder = SortOrder.DESC


class NewLinkSuggestion(BaseModel):
    job_id: str
    from_page_id: str
    to_page_id: str
    from_chunk_id: str | None = None
    action: LinkAction = LinkAction.CREATE
    suggestion: str
    search_score: float | None = None
    state: SuggestionState = SuggestionState.DRAFT


class LinkSuggestionChanges(BaseModel):
    state: SuggestionState | None = None
    suggestion: str | None = None
    from_chunk_id: str | None = None
    confidence: float | None = None
    score: float | None = None

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


def _suggestion_text(value: Any) -> str:
    text = str(value if value is not None else "").strip()
    if not text:
        raise ValueError("A suggestion needs a description.")
    return text[:MAX_SUGGESTION_CHARS]


class LinkSuggestionCreateRequest(RequestModel):
    job_id: str = Field(default="", validate_default=True)
    from_page_id: str | None = None
    from_url: str | None = None
    to_page_id: str | None = None
    to_url: str | None = None
    from_chunk_id: str | None = None
    action: LinkAction = LinkAction.CREATE
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
    def _action(cls, value: Any) -> LinkAction:
        return LinkAction.CREATE if blank(value) else choice(LinkAction, value, "action")

    @field_validator("state", mode="before")
    @classmethod
    def _state(cls, value: Any) -> SuggestionState:
        return SuggestionState.DRAFT if blank(value) else choice(SuggestionState, value, "state")

    @field_validator("suggestion", mode="before")
    @classmethod
    def _suggestion(cls, value: Any) -> str:
        return _suggestion_text(value)

    @field_validator(
        "from_page_id", "from_url", "to_page_id", "to_url", "from_chunk_id", mode="before"
    )
    @classmethod
    def _optional_text(cls, value: Any) -> str | None:
        return None if blank(value) else str(value).strip()

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
    state: SuggestionState | None = None
    suggestion: str | None = None
    from_chunk_id: str | None = None

    @field_validator("state", mode="before")
    @classmethod
    def _state(cls, value: Any) -> SuggestionState:
        if blank(value):
            raise ValueError("A state cannot be blank.")
        return choice(SuggestionState, value, "state")

    @field_validator("suggestion", mode="before")
    @classmethod
    def _suggestion(cls, value: Any) -> str:
        return _suggestion_text(value)

    @field_validator("from_chunk_id", mode="before")
    @classmethod
    def _chunk(cls, value: Any) -> str | None:
        return None if blank(value) else str(value).strip()

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


class LinkSuggestionDeleteResponse(EntityModel):
    id: str
    deleted: bool = True


class LinkSuggestionSummaryResponse(EntityModel):
    draft: int = 0
    screening_rejected: int = 0
    screening_approved: int = 0
    review_approved: int = 0
    review_rejected: int = 0
    user_rejected: int = 0


class HierarchyPage(BaseModel):
    id: str
    url: str
    is_home: bool
    page_type: str | None


class HierarchyRequest(RequestModel):
    job_id: str = Field(default="", validate_default=True)

    @field_validator("job_id", mode="before")
    @classmethod
    def _job(cls, value: Any) -> str:
        if blank(value):
            raise ValueError("Send the jobId the suggestions belong to.")
        return str(value).strip()


class HierarchyResult(EntityModel):
    inserted: int = 0
    skipped: int = 0
    home_found: bool = False
    hubs: int = 0


class ReconcileResult(EntityModel):
    removed: int = 0


def _job_id(value: Any) -> str:
    if blank(value):
        raise ValueError("Send the jobId the suggestions belong to.")
    return str(value).strip()


class MentionTarget(RequestModel):
    to_id: str = Field(default="", validate_default=True)
    phrases: list[str] = Field(default_factory=list, validate_default=True)

    @field_validator("to_id", mode="before")
    @classmethod
    def _to_id(cls, value: Any) -> str:
        if blank(value):
            raise ValueError("Send the toId of the target page.")
        return str(value).strip()

    @field_validator("phrases", mode="before")
    @classmethod
    def _phrases(cls, value: Any) -> list[str]:
        items = list(dict.fromkeys(str(v).strip() for v in (value or []) if not blank(v)))
        if not items:
            raise ValueError("Give each target at least one phrase.")
        return items


class MentionsRequest(RequestModel):
    job_id: str = Field(default="", validate_default=True)
    targets: list[MentionTarget] = Field(default_factory=list, validate_default=True)
    limit_per_target: int = Field(default=50, ge=1, le=500)

    @field_validator("job_id", mode="before")
    @classmethod
    def _job(cls, value: Any) -> str:
        return _job_id(value)

    @field_validator("targets")
    @classmethod
    def _targets(cls, value: list[MentionTarget]) -> list[MentionTarget]:
        if not value:
            raise ValueError("Give at least one target.")
        ids = [t.to_id for t in value]
        if len(set(ids)) != len(ids):
            raise ValueError("Give each target page once, with all its phrases.")
        return value


class MentionsResult(EntityModel):
    inserted: int = 0
    skipped: int = 0
    targets_without_match: list[str] = Field(default_factory=list)


class RemovalsRequest(RequestModel):
    job_id: str = Field(default="", validate_default=True)
    source_table: str = Field(default="", validate_default=True)

    @field_validator("job_id", mode="before")
    @classmethod
    def _job(cls, value: Any) -> str:
        return _job_id(value)

    @field_validator("source_table", mode="before")
    @classmethod
    def _table(cls, value: Any) -> str:
        return workspace_table(value)


class RemovalsResult(EntityModel):
    read: int = 0
    inserted: int = 0
    skipped: int = 0
    not_body_links: int = 0
    last_inlink: int = 0
    to_hub_or_home: int = 0


class PairsRequest(RequestModel):
    job_id: str = Field(default="", validate_default=True)
    source_table: str = Field(default="", validate_default=True)
    min_similarity: float | None = Field(default=None, ge=0.0, le=1.0)
    per_source: int = Field(default=3, ge=1, le=15)

    @field_validator("job_id", mode="before")
    @classmethod
    def _job(cls, value: Any) -> str:
        return _job_id(value)

    @field_validator("source_table", mode="before")
    @classmethod
    def _table(cls, value: Any) -> str:
        return workspace_table(value)


class PairsResult(EntityModel):
    read: int = 0
    not_live: int = 0
    already_linked: int = 0
    already_suggested: int = 0
    not_embedded: int = 0
    below_threshold: int = 0
    over_source_cap: int = 0
    inserted: int = 0
    skipped: int = 0
    min_similarity: float = 0.0


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


class ScreenRequest(RequestModel):
    job_id: str | None = None
    ids: list[str] | None = None
    limit: int = Field(default=200, ge=1, le=1000)
    question: str | None = None


class ScreeningInput(BaseModel):
    id: str
    action: LinkAction
    suggestion: str
    from_page_id: str
    to_page_id: str
    from_url: str
    from_title: str | None
    from_content_hash: str | None
    from_text: str
    from_details: str
    anchor: str | None = None
    to_url: str
    to_title: str | None
    to_meta_description: str | None
    to_h1: list[str]
    to_details: str
    to_content_hash: str | None


class ReviewInputsRequest(RequestModel):
    prompt: str = Field(default="", validate_default=True)
    job_id: str | None = None
    ids: list[str] | None = None
    limit: int = Field(default=200, ge=1, le=1000)

    @field_validator("prompt", mode="before")
    @classmethod
    def _prompt(cls, value: Any) -> str:
        return review_prompt(value)


class Verdict(RequestModel):
    id: str
    verdict: SuggestionState

    @field_validator("verdict", mode="before")
    @classmethod
    def _verdict(cls, value: Any) -> SuggestionState:
        verdict = choice(SuggestionState, value, "verdict")
        if verdict not in VERDICTS:
            raise ValueError(f"A verdict is one of: {', '.join(VERDICTS)}.")
        return verdict


class VerdictRequest(RequestModel):
    verdicts: list[Verdict] = Field(default_factory=list)


class RankRequest(RequestModel):
    max_per_target: int | None = Field(default=None, ge=1)
    target_discount: float = Field(default=1.0, ge=0.0, le=3.0)
