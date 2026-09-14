import re
from typing import Any

from pydantic import Field, computed_field, field_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_SLUG_CHARS = 64
MAX_QUESTION_CHARS = 300
MAX_PLAN_CHARS = 8000


def _slug(value: Any) -> str:
    slug = ("" if value is None else str(value)).strip().lower()
    if not SLUG_RE.match(slug) or len(slug) > MAX_SLUG_CHARS:
        raise ValueError(
            f"slug must be lowercase words joined by hyphens, {MAX_SLUG_CHARS} chars or fewer."
        )
    return slug


def _text(value: Any, field: str, limit: int) -> str:
    text = ("" if value is None else str(value)).strip()
    if not text:
        raise ValueError(f"{field} is required.")
    if len(text) > limit:
        raise ValueError(f"{field} is {len(text)} characters — keep it under {limit}.")
    return text


class AgentPlanCreateRequest(RequestModel):
    slug: str
    question: str
    plan: str

    @field_validator("slug", mode="before")
    @classmethod
    def _validate_slug(cls, v: Any) -> str:
        return _slug(v)

    @field_validator("question", mode="before")
    @classmethod
    def _validate_question(cls, v: Any) -> str:
        return _text(v, "question", MAX_QUESTION_CHARS)

    @field_validator("plan", mode="before")
    @classmethod
    def _validate_plan(cls, v: Any) -> str:
        return _text(v, "plan", MAX_PLAN_CHARS)


class AgentPlanUpdateRequest(RequestModel):
    slug: str | None = None
    question: str | None = None
    plan: str | None = None

    @field_validator("slug", mode="before")
    @classmethod
    def _validate_slug(cls, v: Any) -> str | None:
        return None if v is None else _slug(v)

    @field_validator("question", mode="before")
    @classmethod
    def _validate_question(cls, v: Any) -> str | None:
        return None if v is None else _text(v, "question", MAX_QUESTION_CHARS)

    @field_validator("plan", mode="before")
    @classmethod
    def _validate_plan(cls, v: Any) -> str | None:
        return None if v is None else _text(v, "plan", MAX_PLAN_CHARS)

    def changes(self) -> dict[str, str]:
        return self.model_dump(exclude_none=True)


class AgentPlanRecord(EntityModel):
    id: str
    user_id: str | None
    slug: str
    question: str
    plan: str
    created_at: JsDateTime
    updated_at: JsDateTime

    @computed_field
    @property
    def builtin(self) -> bool:
        return self.user_id is None


class AgentPlanSyncResult(EntityModel):
    synced: int
    pruned: int


class AgentPlanResponse(EntityModel):
    id: str
    slug: str
    question: str
    plan: str
    builtin: bool
    created_at: JsDateTime
    updated_at: JsDateTime


class AgentPlanListItemResponse(EntityModel):
    id: str
    slug: str
    question: str
    builtin: bool
    created_at: JsDateTime
    updated_at: JsDateTime


class AgentPlanDeleteResponse(EntityModel):
    id: str
    deleted: bool = Field(default=True)


class AgentPlanMatchResponse(EntityModel):
    slug: str
    question: str


class AgentPlanPlanResponse(EntityModel):
    slug: str
    question: str
    plan: str


class AgentPlanFindResponse(EntityModel):
    matches: list[AgentPlanMatchResponse]
    n: int
