from typing import Any

from pydantic import Field, field_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel
from src.seo.common import fields


class SeoJobRecord(EntityModel):
    id: str
    site_id: str
    prompt: str
    status: str
    vendor_calls: int
    vendor_micros: int
    vendor_ceiling_micros: int
    created_at: JsDateTime
    updated_at: JsDateTime


class SeoJobCreateRequest(RequestModel):
    prompt: str = Field(default="", validate_default=True)

    @field_validator("prompt", mode="before")
    @classmethod
    def _prompt(cls, value: Any) -> str:
        return fields.prompt(value)


class SeoJobUpdateRequest(RequestModel):
    status: str = Field(default="", validate_default=True)

    @field_validator("status", mode="before")
    @classmethod
    def _status(cls, value: Any) -> str:
        return fields.status(value)
