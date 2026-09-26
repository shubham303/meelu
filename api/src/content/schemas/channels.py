from typing import Any, ClassVar

from pydantic import computed_field, field_validator

from src.content.platform_seeds import SEEDS_BY_KEY
from src.core.schemas import EntityModel, JsDateTime, RequestModel

MAX_RULES = 60
MAX_RULE_LENGTH = 500


class SiteChannelUpdateRequest(RequestModel):
    enabled: bool | None = None
    rules: list[str] | None = None

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

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class SiteChannelRecord(EntityModel):
    id: str
    site_id: str
    channel_key: str
    enabled: bool
    rules: list[str]
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
    keep_null: ClassVar[frozenset[str]] = frozenset({"maxLinks", "maxHashtags"})

    id: str
    site_id: str
    channel_key: str
    enabled: bool
    rules: list[str]
    created_at: JsDateTime
    updated_at: JsDateTime
    label: str
    compose_url: str
    character_limit: int
    requires_media: bool
    max_links: int | None
    max_hashtags: int | None
    max_media: int
