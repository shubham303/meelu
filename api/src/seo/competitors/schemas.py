from typing import Any

from pydantic import field_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel
from src.seo.common import fields


class CompetitorRecord(EntityModel):
    id: str
    domain: str
    brand_terms: list[str]
    first_source: str
    intersections: int | None
    avg_position: float | None
    state: str
    fetched_at: JsDateTime | None


class CompetitorUpdateRequest(RequestModel):
    state: str | None = None
    brand_terms: list[str] | None = None

    @field_validator("state", mode="before")
    @classmethod
    def _state(cls, value: Any) -> str | None:
        return None if value is None else fields.competitor_state(value)

    @field_validator("brand_terms", mode="before")
    @classmethod
    def _brand_terms(cls, value: Any) -> list[str] | None:
        return None if value is None else fields.brand_terms(value)
