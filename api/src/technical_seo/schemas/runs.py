from datetime import UTC, datetime
from typing import Any, ClassVar, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel
from src.technical_seo.schemas import fields


class AuditRunRecord(EntityModel):
    id: str
    site_id: str
    trigger: str
    rules_run: int
    site_issues_found: int
    page_issues_found: int
    finished_at: JsDateTime | None = None
    reviewed_at: JsDateTime | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class AuditRunResponse(EntityModel):
    keep_null: ClassVar[frozenset[str]] = frozenset({"finishedAt"})

    id: str
    site_id: str
    trigger: str
    rules_run: int
    site_issues_found: int
    page_issues_found: int
    finished_at: JsDateTime | None = None
    reviewed_at: JsDateTime | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class AuditRunListItemResponse(AuditRunResponse):
    pass


class AuditRunDeleteResponse(EntityModel):
    id: str
    deleted: bool = Field(default=True)


class AuditRunFilter(BaseModel):
    trigger: str | None = None
    reviewed: bool | None = None


class AuditRunChanges(BaseModel):
    trigger: str | None = None
    rules_run: int | None = None
    site_issues_found: int | None = None
    page_issues_found: int | None = None
    finished_at: datetime | None = None
    reviewed_at: datetime | None = None

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class AuditStartRequest(RequestModel):
    trigger: str = Field(default="user", validate_default=True)

    @field_validator("trigger", mode="before")
    @classmethod
    def _trigger(cls, value: Any) -> str:
        return fields.trigger(value)


class AuditRunUpdateRequest(RequestModel):
    trigger: str | None = None
    reviewed: bool | None = None

    @field_validator("trigger", mode="before")
    @classmethod
    def _trigger(cls, value: Any) -> str:
        return fields.trigger(value)

    @model_validator(mode="after")
    def _something_to_change(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Nothing to change. Send reviewed or trigger.")
        return self

    def to_changes(self) -> AuditRunChanges:
        changes = AuditRunChanges()
        if "trigger" in self.model_fields_set and self.trigger is not None:
            changes.trigger = self.trigger
        if "reviewed" in self.model_fields_set:
            changes.reviewed_at = datetime.now(UTC) if self.reviewed else None
        return changes
