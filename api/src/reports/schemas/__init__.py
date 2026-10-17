import re
from typing import Any, Literal

from pydantic import Field, field_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel

REPORT_DESKS = ("analytics", "seo", "technical-seo")
MAX_HTML_BYTES = 8 * 1024 * 1024

ReportDesk = Literal["analytics", "seo", "technical-seo"]

EXTERNAL_REF_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"<\s*(script|iframe|frame|frameset|object|embed|link|base|form|video|audio|source|track|applet|portal)\b",
            re.IGNORECASE,
        ),
        "an element that can load or send",
    ),
    (re.compile(r"http-equiv", re.IGNORECASE), "http-equiv (meta refresh/CSP override)"),
    (
        re.compile(
            r"\b(?:src|srcset|href|poster|formaction|background|xlink:href|ping|data)\s*=\s*(?:\"|'|&quot;)?\s*(?:https?:)?//",
            re.IGNORECASE,
        ),
        "an attribute referencing another origin",
    ),
    (
        re.compile(r"url\(\s*(?:\"|'|&quot;)?\s*(?:https?:)?//", re.IGNORECASE),
        "a CSS url() to another origin",
    ),
    (
        re.compile(r"image-set\(\s*(?:\"|'|&quot;)?\s*(?:https?:)?//", re.IGNORECASE),
        "a CSS image-set() to another origin",
    ),
    (re.compile(r"@import", re.IGNORECASE), "a CSS @import"),
]


def _html(value: Any) -> str:
    if not isinstance(value, str) or value.strip() == "":
        raise ValueError("`html` must be a non-empty string.")
    if len(value.encode("utf-8")) > MAX_HTML_BYTES:
        raise ValueError(
            "Report HTML exceeds 8MB. Keep reports self-contained but lean — no embedded "
            "raw datasets or base64 images."
        )
    for pattern, what in EXTERNAL_REF_PATTERNS:
        if pattern.search(value):
            raise ValueError(
                f"The HTML must be fully self-contained (inline CSS/SVG only) — it contains "
                f"{what}. Use the diagram templates verbatim; never hand-write markup that "
                f"references the network."
            )
    return value


def _required_text(value: Any, field: str) -> str:
    text = ("" if value is None else str(value)).strip()
    if not text:
        raise ValueError(f"`{field}` is required.")
    return text


def _desk(value: Any) -> str:
    desk = str(value)
    if desk not in REPORT_DESKS:
        raise ValueError(f'Invalid desk "{desk}". Allowed values: {", ".join(REPORT_DESKS)}.')
    return desk


class ReportCreateRequest(RequestModel):
    desk: str
    title: str
    html: str
    created_by: Literal["user", "agent"] = "agent"

    @field_validator("desk", mode="before")
    @classmethod
    def _validate_desk(cls, v: Any) -> str:
        return _desk(v)

    @field_validator("title", mode="before")
    @classmethod
    def _validate_title(cls, v: Any) -> str:
        return _required_text(v, "title")

    @field_validator("html", mode="before")
    @classmethod
    def _validate_html(cls, v: Any) -> str:
        return _html(v)

    @field_validator("created_by", mode="before")
    @classmethod
    def _validate_created_by(cls, v: Any) -> str:
        return "user" if v == "user" else "agent"


class ReportUpdateRequest(RequestModel):
    title: str | None = None
    html: str | None = None

    @field_validator("title", mode="before")
    @classmethod
    def _validate_title(cls, v: Any) -> str | None:
        return None if v is None else _required_text(v, "title")

    @field_validator("html", mode="before")
    @classmethod
    def _validate_html(cls, v: Any) -> str | None:
        return None if v is None else _html(v)

    def changes(self) -> dict[str, str]:
        return self.model_dump(exclude_none=True)


class ReportRecord(EntityModel):
    id: str
    user_id: str
    site_id: str
    desk: str
    title: str
    html: str
    created_by: str
    created_at: JsDateTime
    updated_at: JsDateTime


class ReportSummaryRecord(EntityModel):
    id: str
    user_id: str
    site_id: str
    desk: str
    title: str
    created_by: str
    html_bytes: int
    created_at: JsDateTime
    updated_at: JsDateTime

    @classmethod
    def from_report(cls, report: ReportRecord) -> "ReportSummaryRecord":
        return cls(
            id=report.id,
            user_id=report.user_id,
            site_id=report.site_id,
            desk=report.desk,
            title=report.title,
            created_by=report.created_by,
            html_bytes=len(report.html.encode("utf-8")),
            created_at=report.created_at,
            updated_at=report.updated_at,
        )


class ReportResponse(EntityModel):
    id: str
    site_id: str
    desk: str
    title: str
    html: str
    created_by: str
    created_at: JsDateTime
    updated_at: JsDateTime


class ReportSummaryResponse(EntityModel):
    id: str
    site_id: str
    desk: str
    title: str
    created_by: str
    html_bytes: int
    created_at: JsDateTime
    updated_at: JsDateTime


class ReportDeleteResponse(EntityModel):
    id: str
    deleted: bool = Field(default=True)
