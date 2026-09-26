from typing import Any

from pydantic import field_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel
from src.seo.common import fields


class SiteStateRecord(EntityModel):
    id: str
    site_id: str
    location_code: int
    language_code: str
    brand_terms: list[str]
    precompute_requested_at: JsDateTime | None
    rollup_at: JsDateTime | None
    embedded_at: JsDateTime | None
    ctr_curve: dict[str, Any]


class SiteStateUpdateRequest(RequestModel):
    location_code: int | None = None
    language_code: str | None = None
    brand_terms: list[str] | None = None

    @field_validator("brand_terms", mode="before")
    @classmethod
    def _brand_terms(cls, value: Any) -> list[str] | None:
        return None if value is None else fields.brand_terms(value)

    @field_validator("language_code", mode="before")
    @classmethod
    def _language(cls, value: Any) -> str | None:
        return None if value is None else str(value).strip().lower()[:8]
