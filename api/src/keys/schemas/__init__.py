from typing import Any

from pydantic import Field, field_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel

DEFAULT_KEY_NAME = "MCP key"


class ApiKeyCreateRequest(RequestModel):
    name: str = DEFAULT_KEY_NAME

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> str:
        name = ("" if v is None else str(v)).strip()
        return name or DEFAULT_KEY_NAME


class ApiKeyRecord(EntityModel):
    id: str
    user_id: str
    name: str
    preview: str
    last_used_at: JsDateTime | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class ApiKeyCreateResult(EntityModel):
    key: ApiKeyRecord
    raw: str


class ApiKeyOwner(EntityModel):
    user_id: str


class ApiKeyResponse(EntityModel):
    keep_null = frozenset({"lastUsedAt"})

    id: str
    name: str
    preview: str
    last_used_at: JsDateTime | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class ApiKeyListItemResponse(ApiKeyResponse):
    pass


class ApiKeyCreatedResponse(ApiKeyResponse):
    key: str


class ApiKeyDeleteResponse(EntityModel):
    id: str
    deleted: bool = Field(default=True)
