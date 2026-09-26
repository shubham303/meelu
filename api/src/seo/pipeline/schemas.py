from typing import Any

from pydantic import Field, field_validator

from src.core.schemas import EntityModel, RequestModel
from src.seo.common import fields


class ReconcileResult(EntityModel):
    done: int = 0
    stale: int = 0
    pending_precompute: bool = False


class ScreenResult(EntityModel):
    screened: int = 0
    passed: int = 0
    llm_rejected: int = 0
    failed: int = 0
    stopped: str | None = None


class ReviewResult(EntityModel):
    reviewed: int = 0
    llm_rejected: int = 0
    failed: int = 0
    needs_serp: list[str] = Field(default_factory=list)


class ReviewItem(EntityModel):
    id: str
    state: dict[str, Any]


class ReviewBatch(EntityModel):
    instructions: str
    schema_: dict[str, Any] = Field(alias="schema")
    items: list[ReviewItem]
    needs_serp: list[str] = Field(default_factory=list)


class Verdict(RequestModel):
    id: str
    verdict: str
    suggestion: str | None = None


class VerdictRequest(RequestModel):
    verdicts: list[Verdict] = Field(default_factory=list)


class RankResult(EntityModel):
    kept: int = 0
    llm_rejected: int = 0


class ScreenRequest(RequestModel):
    job_id: str
    ids: list[str] | None = None
    question: str | None = None
    limit: int = 200


class ReviewInputsRequest(RequestModel):
    job_id: str
    prompt: str = Field(default="", validate_default=True)
    ids: list[str] | None = None
    limit: int = 200

    @field_validator("prompt", mode="before")
    @classmethod
    def _prompt(cls, value: Any) -> str:
        return fields.prompt(value)


class RankRequest(RequestModel):
    job_id: str
    budget_add: int = 10
    budget_edit: int = 20
    budget_delete: int = 5
