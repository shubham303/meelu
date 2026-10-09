import re
from typing import Any

from pydantic import Field, field_validator

from src.content.numbers import number_or_null
from src.core.schemas import EntityModel, JsDateTime, RequestModel

SLUG_RE = re.compile(r"/?[a-z0-9]+(?:-[a-z0-9]+)*(?:/[a-z0-9]+(?:-[a-z0-9]+)*)*/?")
MEDIA_SOURCES = ("none", "upload", "unsplash")


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


class ContentPiecePageFields(ContentPieceMediaRequest):
    h1: str | None = None
    meta_description: str | None = None
    slug: str | None = None
    target_keyword: str | None = None
    body_markdown: str | None = None
    source_page_id: str | None = None

    @field_validator("h1", "meta_description", mode="before")
    @classmethod
    def _one_line(cls, v: Any) -> str | None:
        return None if v is None else " ".join(str(v).split())

    @field_validator("target_keyword", mode="before")
    @classmethod
    def _keyword(cls, v: Any) -> str | None:
        if v is None:
            return None
        return " ".join(str(v).split()).lower() or None

    @field_validator("slug", mode="before")
    @classmethod
    def _slug(cls, v: Any) -> str | None:
        if v is None:
            return None
        text = str(v).strip().lower()
        if not text:
            return None
        if not SLUG_RE.fullmatch(text):
            raise ValueError(
                "slug must be a URL path of lowercase letters, digits and hyphens, "
                "such as /blog/espresso-grind-size."
            )
        return "/" + text.strip("/")

    @field_validator("body_markdown", mode="before")
    @classmethod
    def _body(cls, v: Any) -> str | None:
        return None if v is None else str(v)


class ContentPieceCreateRequest(ContentPiecePageFields):
    title: str = Field(default="", validate_default=True)

    @field_validator("title", mode="before")
    @classmethod
    def _validate_title(cls, v: Any) -> str:
        return _required_text(v, "title")


class ContentPieceUpdateRequest(ContentPiecePageFields):
    title: str | None = None

    @field_validator("title", mode="before")
    @classmethod
    def _validate_title(cls, v: Any) -> str | None:
        return None if v is None else _required_text(v, "title")


class ContentPieceRecord(EntityModel):
    id: str
    site_id: str
    title: str
    h1: str
    meta_description: str
    slug: str | None
    target_keyword: str | None
    body_markdown: str
    word_count: int
    checks: list[PieceCheck]
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


class ContentPieceMarkdownResult(EntityModel):
    markdown: str


class ContentPieceResponse(ContentPieceRecord):
    pass


class ContentPieceListItemResponse(EntityModel):
    id: str
    site_id: str
    title: str
    slug: str | None
    target_keyword: str | None
    word_count: int
    checks: list[PieceCheck]
    media_source: str
    media_url: str | None
    created_at: JsDateTime
    updated_at: JsDateTime


class ContentPieceSummaryResponse(EntityModel):
    id: str
    title: str
    slug: str | None
    checks: list[PieceCheck]
    word_count: int


class ContentPieceDeleteResponse(EntityModel):
    id: str
    deleted: bool = Field(default=True)
