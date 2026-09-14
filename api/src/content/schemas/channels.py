import math
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import computed_field, field_validator

from src.content.platform_seeds import SEEDS_BY_KEY
from src.core.schemas import EntityModel, JsDateTime, RequestModel

MAX_RULES = 60
MAX_RULE_LENGTH = 500
MAX_GAP_HOURS = 24 * 30


class PostingWindow(RequestModel):
    days: list[int]
    time: str

    @field_validator("days")
    @classmethod
    def _validate_days(cls, v: list[int]) -> list[int]:
        if not v or any(d < 0 or d > 6 for d in v):
            raise ValueError("Each posting window needs days as weekday numbers 0–6.")
        return sorted(set(v))

    @field_validator("time")
    @classmethod
    def _validate_time(cls, v: str) -> str:
        bad = ValueError("Each posting window needs a time like 09:00.")
        if len(v) != 5 or v[2] != ":":
            raise bad
        try:
            hour, minute = int(v[:2]), int(v[3:])
        except ValueError:
            raise bad
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise bad
        return v


def valid_timezone(value: Any) -> str:
    if value is None or value == "":
        return "UTC"
    name = str(value)
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, KeyError):
        raise ValueError(f'"{name}" is not a valid IANA timezone.')
    return name


class SiteChannelUpdateRequest(RequestModel):
    enabled: bool | None = None
    rules: list[str] | None = None
    timezone: str | None = None
    posting_windows: list[PostingWindow] | None = None
    min_gap_hours: int | None = None

    @field_validator("rules")
    @classmethod
    def _validate_rules(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        rules: list[str] = []
        for item in v:
            line = " ".join(item.split())
            if not line:
                continue
            if len(line) > MAX_RULE_LENGTH:
                raise ValueError(f"Each rule must be {MAX_RULE_LENGTH} characters or fewer.")
            rules.append(line)
        if len(rules) > MAX_RULES:
            raise ValueError(f"At most {MAX_RULES} rules per channel.")
        return rules

    @field_validator("timezone", mode="before")
    @classmethod
    def _validate_timezone(cls, v: Any) -> str | None:
        return None if v is None else valid_timezone(v)

    @field_validator("min_gap_hours", mode="before")
    @classmethod
    def _validate_gap(cls, v: Any) -> int | None:
        if v is None or v == "":
            return None
        try:
            n = float(v)
        except (TypeError, ValueError):
            raise ValueError(f"minGapHours must be a number between 0 and {MAX_GAP_HOURS}.")
        if not math.isfinite(n) or n < 0 or n > MAX_GAP_HOURS:
            raise ValueError(f"minGapHours must be a number between 0 and {MAX_GAP_HOURS}.")
        return int(n + 0.5)

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class SiteChannelRecord(EntityModel):
    id: str
    site_id: str
    channel_key: str
    enabled: bool
    rules: list[str]
    timezone: str
    posting_windows: list[PostingWindow]
    min_gap_hours: int
    created_at: JsDateTime
    updated_at: JsDateTime

    @computed_field
    @property
    def label(self) -> str:
        return SEEDS_BY_KEY[self.channel_key].label

    @computed_field
    @property
    def compose_url(self) -> str:
        return SEEDS_BY_KEY[self.channel_key].compose_url

    @computed_field
    @property
    def character_limit(self) -> int:
        return SEEDS_BY_KEY[self.channel_key].character_limit

    @computed_field
    @property
    def requires_media(self) -> bool:
        return SEEDS_BY_KEY[self.channel_key].requires_media

    @computed_field
    @property
    def max_links(self) -> int | None:
        return SEEDS_BY_KEY[self.channel_key].max_links

    @computed_field
    @property
    def max_hashtags(self) -> int | None:
        return SEEDS_BY_KEY[self.channel_key].max_hashtags

    @computed_field
    @property
    def max_media(self) -> int:
        return SEEDS_BY_KEY[self.channel_key].max_media


class SiteChannelResponse(EntityModel):
    id: str
    site_id: str
    channel_key: str
    enabled: bool
    rules: list[str]
    timezone: str
    posting_windows: list[PostingWindow]
    min_gap_hours: int
    created_at: JsDateTime
    updated_at: JsDateTime
    label: str
    compose_url: str
    character_limit: int
    requires_media: bool
    max_links: int | None
    max_hashtags: int | None
    max_media: int
