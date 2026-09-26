from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel
from src.site_structure.schemas.fields import choice

MAX_PROMPT_CHARS = 20_000


class JobStatus(StrEnum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class StructureJobRecord(EntityModel):
    id: str
    site_id: str
    prompt: str
    status: JobStatus
    created_at: JsDateTime
    updated_at: JsDateTime


class StructureJobCreateRequest(RequestModel):
    prompt: str = Field(default="", validate_default=True)

    @field_validator("prompt", mode="before")
    @classmethod
    def _prompt(cls, value: Any) -> str:
        text = str(value if value is not None else "").strip()
        if not text:
            raise ValueError("A job needs the prompt it runs.")
        return text[:MAX_PROMPT_CHARS]


class StructureJobUpdateRequest(RequestModel):
    status: JobStatus = Field(default=JobStatus.COMPLETED, validate_default=True)

    @field_validator("status", mode="before")
    @classmethod
    def _status(cls, value: Any) -> JobStatus:
        return choice(JobStatus, str(value).upper(), "status")
