from typing import Any

from pydantic import Field, field_validator

from src.core.schemas import EntityModel, RequestModel
from src.seo.common import fields
from src.seo.page_suggestions.schemas import CreateResult


class GapPagesRequest(RequestModel):
    job_id: str
    keyword_ids: list[str] | None = None
    min_volume: int = 50
    max_difficulty: int = 60


class TopicPagesRequest(RequestModel):
    job_id: str
    topic: str = Field(default="", validate_default=True)
    source_table: str | None = None
    ideas_per_seed: int = 30
    dry_run: bool = False

    @field_validator("topic", mode="before")
    @classmethod
    def _topic(cls, value: Any) -> str:
        cleaned = fields.keyword(value)
        if not cleaned:
            raise ValueError("A topic is needed.")
        return cleaned


class TopicPagesResult(EntityModel):
    suggestions: CreateResult
    collected: dict[str, Any]
