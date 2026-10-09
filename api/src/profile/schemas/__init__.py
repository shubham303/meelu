from typing import Any
from zoneinfo import ZoneInfo

from pydantic import Field, field_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel

LEGACY_ALIASES = {
    "Asia/Calcutta": "Asia/Kolkata",
    "Asia/Saigon": "Asia/Ho_Chi_Minh",
    "Asia/Katmandu": "Asia/Kathmandu",
    "Asia/Rangoon": "Asia/Yangon",
    "Europe/Kiev": "Europe/Kyiv",
    "America/Buenos_Aires": "America/Argentina/Buenos_Aires",
}


def _timezone(value: Any) -> str | None:
    if value is None or value == "":
        return value
    if not isinstance(value, str):
        raise ValueError("timezone must be a string.")
    parses = True
    try:
        ZoneInfo(value)
    except Exception:
        parses = False
    if parses and value in LEGACY_ALIASES:
        return LEGACY_ALIASES[value]
    if not parses or not ("/" in value or value.upper() == "UTC"):
        raise ValueError(
            f'"{value}" is not an IANA timezone. Use an Area/Location name such as '
            f'"Asia/Kolkata", "Europe/London" or "America/New_York" — abbreviations '
            f'like "IST" or "EST" are ambiguous and are rejected.'
        )
    return value


class ProfileCreateRequest(RequestModel):
    full_name: str | None = None
    role: str | None = None
    company: str | None = None
    timezone: str | None = None
    signature: str | None = None
    bio: str | None = None
    writing_voice: str | None = None
    linkedin_url: str | None = None
    x_url: str | None = None
    website_url: str | None = None

    @field_validator("timezone", mode="before")
    @classmethod
    def _validate_timezone(cls, v: Any) -> str | None:
        return _timezone(v)

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class ProfileUpdateRequest(ProfileCreateRequest):
    pass


class ProfileRecord(EntityModel):
    id: str
    user_id: str
    full_name: str
    role: str | None = None
    company: str | None = None
    timezone: str | None = None
    signature: str | None = None
    bio: str | None = None
    writing_voice: str | None = None
    linkedin_url: str | None = None
    x_url: str | None = None
    website_url: str | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class ProfileResponse(EntityModel):
    id: str
    full_name: str
    role: str | None = None
    company: str | None = None
    timezone: str | None = None
    signature: str | None = None
    bio: str | None = None
    writing_voice: str | None = None
    linkedin_url: str | None = None
    x_url: str | None = None
    website_url: str | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class ProfileDeleteResponse(EntityModel):
    id: str
    deleted: bool = Field(default=True)


class UserRecord(EntityModel):
    id: str
    email: str
    name: str | None
    image: str | None
    auth_id: str | None
    is_active: bool
    is_superuser: bool
    is_verified: bool
