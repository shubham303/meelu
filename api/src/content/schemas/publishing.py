from typing import Any

from pydantic import Field, field_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel


class SocialAccountRecord(EntityModel):
    id: str
    user_id: str
    site_id: str
    provider: str
    external_account_id: str
    created_at: JsDateTime
    updated_at: JsDateTime


class SocialAccountResponse(EntityModel):
    id: str
    provider: str
    external_account_id: str


class SocialAccountUpsertRequest(RequestModel):
    provider: str
    external_account_id: str

    @field_validator("provider", "external_account_id", mode="before")
    @classmethod
    def _non_empty(cls, v: Any) -> str:
        value = ("" if v is None else str(v)).strip()
        if not value:
            raise ValueError("provider and externalAccountId must be non-empty strings.")
        return value


class SocialChannelsSyncRequest(RequestModel):
    platforms: list[str] = Field(default_factory=list)

    @field_validator("platforms", mode="before")
    @classmethod
    def _validate_platforms(cls, v: Any) -> list[str]:
        if not isinstance(v, list):
            return []
        return [str(p).strip() for p in v if str(p).strip()]


class SocialChannelsSyncResponse(EntityModel):
    synced: bool = Field(default=True)


class SocialAccountDeleteResponse(EntityModel):
    deleted: bool = Field(default=True)
