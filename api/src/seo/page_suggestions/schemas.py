from typing import Any

from pydantic import Field, field_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel
from src.seo.common import fields


class PageSuggestionRecord(EntityModel):
    id: str
    job_id: str
    action: str
    page_id: str | None
    topic_key: str
    cluster_id: str | None
    pair_id: str | None
    merge_into_page_id: str | None
    strategies: list[str]
    suggestion: str
    evidence: dict[str, Any]
    coverage_at_creation: float | None
    impressions_at_creation: int | None
    target_position: float | None
    state: str
    search_score: float | None
    confidence: float | None
    score: float | None
    verified_at: JsDateTime | None
    created_at: JsDateTime
    updated_at: JsDateTime


class PageSuggestionFilter(EntityModel):
    state: str | None = None
    action: str | None = None
    job_id: str | None = None
    page_id: str | None = None
    topic_key: str | None = None


class PageSuggestionSummary(EntityModel):
    add: dict[str, int] = {}
    edit: dict[str, int] = {}
    delete: dict[str, int] = {}


class NewPageSuggestion(EntityModel):
    action: str
    topic_key: str
    page_id: str | None = None
    cluster_id: str | None = None
    merge_into_page_id: str | None = None
    keyword_ids: list[str] = Field(default_factory=list)
    strategy: str
    suggestion: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    search_score: float | None = None
    target_position: float | None = None
    state: str = "draft"
    pair_with: int | None = None


class Collision(EntityModel):
    id: str
    state: str
    strategies: list[str]


class CreateResult(EntityModel):
    drafts: int = 0
    ids: list[str] = Field(default_factory=list)
    collided: list[Collision] = Field(default_factory=list)
    filtered: dict[str, int] = Field(default_factory=dict)


class SavePageSuggestionRequest(RequestModel):
    job_id: str
    action: str = Field(default="", validate_default=True)
    topic_key: str = Field(default="", validate_default=True)
    page_id: str | None = None
    merge_into_page_id: str | None = None
    keyword_ids: list[str] = Field(default_factory=list)
    terms: list[str] = Field(default_factory=list)
    suggestion: str = Field(default="", validate_default=True)
    evidence: dict[str, Any] = Field(default_factory=dict)

    @field_validator("action", mode="before")
    @classmethod
    def _action(cls, value: Any) -> str:
        return fields.action(value)

    @field_validator("topic_key", mode="before")
    @classmethod
    def _topic_key(cls, value: Any) -> str:
        cleaned = fields.keyword(value)
        if not cleaned:
            raise ValueError("A suggestion needs a topic key.")
        return cleaned

    @field_validator("suggestion", mode="before")
    @classmethod
    def _suggestion(cls, value: Any) -> str:
        return fields.suggestion(value)

    @field_validator("terms", mode="before")
    @classmethod
    def _terms(cls, value: Any) -> list[str]:
        return fields.keywords(value)
