from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel
from src.site_structure.constants import SuggestionState
from src.site_structure.schemas.fields import blank, choice

MAX_SUGGESTION_CHARS = 4_000


class LinkAction(StrEnum):
    CREATE = "create"
    DELETE = "delete"


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


class LinkSuggestionFilter(BaseModel):
    state: SuggestionState | None = SuggestionState.READY
    action: LinkAction | None = None
    job_id: str | None = None
    from_page_id: str | None = None
    to_page_id: str | None = None
    page_id: str | None = None
    from_url: str | None = None
    to_url: str | None = None


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


class LinkSuggestionSummaryResponse(EntityModel):
    draft: int = 0
    ready: int = 0
    llm_rejected: int = 0
    user_rejected: int = 0
    done: int = 0
    stale: int = 0


class ReconcileResult(EntityModel):
    done: int = 0
    stale: int = 0
