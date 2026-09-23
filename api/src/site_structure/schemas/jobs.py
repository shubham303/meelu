from typing import Any

from pydantic import Field, field_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel
from src.site_structure.schemas import fields


class StructureJobRecord(EntityModel):
    id: str
    site_id: str
    prompt: str
    status: str
    created_at: JsDateTime
    updated_at: JsDateTime


class StructureJobResponse(StructureJobRecord):
    pass


class StructureJobCreateRequest(RequestModel):
    prompt: str = Field(default="", validate_default=True)

    @field_validator("prompt", mode="before")
    @classmethod
    def _prompt(cls, value: Any) -> str:
        return fields.prompt(value)


class StructureJobUpdateRequest(RequestModel):
    status: str = Field(default="", validate_default=True)

    @field_validator("status", mode="before")
    @classmethod
    def _status(cls, value: Any) -> str:
        return fields.status(value)


class ReconcileResult(EntityModel):
    done: int = 0
    stale: int = 0
