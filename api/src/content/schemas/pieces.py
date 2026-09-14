from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from src.content.numbers import number_or_null
from src.content.schemas.channels import PostingWindow
from src.core.schemas import EntityModel, JsDateTime, RequestModel

PIECE_STATUSES = ("draft", "blocked", "scheduled", "posted", "failed")
MEDIA_SOURCES = ("none", "upload", "unsplash")


def _status(value: Any) -> str:
    status = str(value)
    if status not in PIECE_STATUSES:
        raise ValueError(f"Invalid status. Allowed values: {', '.join(PIECE_STATUSES)}.")
    return status


def _required_text(value: Any, name: str) -> str:
    text = ("" if value is None else str(value)).strip()
    if not text:
        raise ValueError(f"{name} is required.")
    return text


class PieceCheck(EntityModel):
    code: str
    level: str
    message: str


class ContentPieceMediaRequest(RequestModel):
    media_source: str | None = None
    media_url: str | None = None
    media_alt: str | None = None
    media_width: int | None = None
    media_height: int | None = None
    media_credit_name: str | None = None
    media_credit_url: str | None = None
    media_upload_id: str | None = None

    @field_validator("media_source", mode="before")
    @classmethod
    def _validate_media_source(cls, v: Any) -> str | None:
        if v is None:
            return None
        if v not in MEDIA_SOURCES:
            raise ValueError(f"Invalid mediaSource. Allowed values: {', '.join(MEDIA_SOURCES)}.")
        return v

    @field_validator("media_width", "media_height", mode="before")
    @classmethod
    def _validate_dimension(cls, v: Any) -> int | None:
        return number_or_null(v)

    @field_validator("media_alt", "media_credit_name", "media_credit_url", mode="before")
    @classmethod
    def _strip(cls, v: Any) -> str | None:
        return v.strip() if isinstance(v, str) else None

    @field_validator("media_url", "media_upload_id", mode="before")
    @classmethod
    def _stringify(cls, v: Any) -> str | None:
        return None if v is None else str(v)

    def has(self, field: str) -> bool:
        return field in self.model_fields_set


class ContentPieceCreateRequest(ContentPieceMediaRequest):
    title: str | None = None
    body_markdown: str | None = None
    channel_key: str | None = None
    status: str | None = None
    scheduled_at: datetime | None = None
    posted_url: str | None = None
    source_page_id: str | None = None
    clone_from_piece_id: str | None = None

    @field_validator("title", mode="before")
    @classmethod
    def _validate_title(cls, v: Any) -> str | None:
        return None if v is None else _required_text(v, "title")

    @field_validator("channel_key", mode="before")
    @classmethod
    def _validate_channel(cls, v: Any) -> str | None:
        return None if v is None else _required_text(v, "channelKey")

    @field_validator("body_markdown", "posted_url", mode="before")
    @classmethod
    def _validate_text(cls, v: Any) -> str | None:
        return None if v is None else str(v)

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, v: Any) -> str | None:
        return None if v is None else _status(v)


class ContentPieceUpdateRequest(ContentPieceMediaRequest):
    title: str | None = None
    body_markdown: str | None = None
    status: str | None = None
    scheduled_at: datetime | None = None
    posted_url: str | None = None
    posted_at: datetime | None = None
    external_post_id: str | None = None
    failure: str | None = None
    source_page_id: str | None = None

    @field_validator("title", mode="before")
    @classmethod
    def _validate_title(cls, v: Any) -> str | None:
        return None if v is None else _required_text(v, "title")

    @field_validator("body_markdown", mode="before")
    @classmethod
    def _validate_body(cls, v: Any) -> str | None:
        return None if v is None else str(v)

    @field_validator("status", mode="before")
    @classmethod
    def _validate_status(cls, v: Any) -> str | None:
        return None if v is None else _status(v)

    @field_validator("posted_url", mode="before")
    @classmethod
    def _validate_posted_url(cls, v: Any) -> str | None:
        if not v:
            return None
        return str(v).strip() or None


class ContentPieceRecord(EntityModel):
    id: str
    site_id: str
    title: str
    body_markdown: str
    channel_key: str
    status: str
    word_count: int
    checks: list[PieceCheck]
    scheduled_at: JsDateTime | None
    posted_at: JsDateTime | None
    posted_url: str | None
    external_post_id: str | None
    failure: str | None
    created_by: str
    media_source: str
    media_url: str | None
    media_alt: str | None
    media_width: int | None
    media_height: int | None
    media_credit_name: str | None
    media_credit_url: str | None
    media_upload_id: str | None
    source_page_id: str | None
    parent_piece_id: str | None
    created_at: JsDateTime
    updated_at: JsDateTime


class PieceMediaResult(EntityModel):
    media_source: str = "none"
    media_url: str | None = None
    media_alt: str | None = None
    media_width: int | None = None
    media_height: int | None = None
    media_credit_name: str | None = None
    media_credit_url: str | None = None
    media_upload_id: str | None = None


class ContentPieceCountsResponse(EntityModel):
    by_status: dict[str, int]


class ContentPieceMarkdownResult(EntityModel):
    markdown: str


class ContentPieceResponse(ContentPieceRecord):
    pass


class ContentPieceListItemResponse(EntityModel):
    id: str
    site_id: str
    title: str
    channel_key: str
    status: str
    word_count: int
    checks: list[PieceCheck]
    scheduled_at: JsDateTime | None
    posted_at: JsDateTime | None
    posted_url: str | None
    failure: str | None
    media_source: str
    media_url: str | None
    parent_piece_id: str | None
    created_at: JsDateTime
    updated_at: JsDateTime


class ContentPieceSummaryResponse(EntityModel):
    id: str
    title: str
    channel_key: str
    status: str
    checks: list[PieceCheck]
    scheduled_at: JsDateTime | None
    word_count: int
    parent_piece_id: str | None


class ContentPieceDeleteResponse(EntityModel):
    id: str
    deleted: bool = Field(default=True)


class TakenSlot(EntityModel):
    scheduled_at: JsDateTime
    title: str
    status: str


class ContentFreeSlotsResponse(EntityModel):
    channel_key: str
    timezone: str
    min_gap_hours: int
    posting_windows: list[PostingWindow]
    from_: JsDateTime = Field(alias="from")
    to: JsDateTime
    free: list[JsDateTime]
    taken: list[TakenSlot]
