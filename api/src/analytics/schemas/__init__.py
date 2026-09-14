import re
from typing import Any, Literal

from pydantic import Field, field_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel

MAX_HTML_BYTES = 8 * 1024 * 1024

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


def _file_path(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ValueError("`filePath` must be a string.")
    path = value.strip().replace("\\", "/")
    if path == "":
        return None
    if path.startswith("/") or re.match(r"^[A-Za-z]:", path):
        raise ValueError(
            "`filePath` is relative to the analytics data directory on the user's machine — "
            "pass the part below it, not an absolute path."
        )
    if any(part == ".." for part in path.split("/")):
        raise ValueError("`filePath` may not step outside the analytics data directory.")
    return path


def _required_text(value: Any, field: str) -> str:
    text = ("" if value is None else str(value)).strip()
    if not text:
        raise ValueError(f"`{field}` is required.")
    return text


def _blank_to_none(value: Any) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


class AnalyticsSessionCreateRequest(RequestModel):
    title: str | None = None
    about: str = ""
    session_key: str | None = None

    @field_validator("title", mode="before")
    @classmethod
    def _validate_title(cls, v: Any) -> str | None:
        return _blank_to_none(None if v is None else str(v).strip())

    @field_validator("about", mode="before")
    @classmethod
    def _validate_about(cls, v: Any) -> str:
        return v if isinstance(v, str) else ""

    @field_validator("session_key", mode="before")
    @classmethod
    def _validate_session_key(cls, v: Any) -> str | None:
        return _blank_to_none(v)


class AnalyticsSessionUpdateRequest(RequestModel):
    title: str | None = None
    about: str | None = None
    session_key: str | None = Field(default=None)

    @field_validator("session_key", mode="before")
    @classmethod
    def _validate_session_key(cls, v: Any) -> str | None:
        return _blank_to_none(v)

    def changes(self) -> dict[str, Any]:
        values = self.model_dump(exclude_unset=True)
        return {k: v for k, v in values.items() if v is not None or k == "session_key"}


class AnalyticsSourceCreateRequest(RequestModel):
    name: str
    file_path: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> str:
        return _required_text(v, "name")

    @field_validator("file_path", mode="before")
    @classmethod
    def _validate_file_path(cls, v: Any) -> str | None:
        return _file_path(v)


class AnalyticsReportCreateRequest(RequestModel):
    title: str
    html: str
    session_id: str | None = None
    created_by: Literal["user", "agent"] = "agent"

    @field_validator("title", mode="before")
    @classmethod
    def _validate_title(cls, v: Any) -> str:
        return _required_text(v, "title")

    @field_validator("html", mode="before")
    @classmethod
    def _validate_html(cls, v: Any) -> str:
        return _html(v)

    @field_validator("session_id", mode="before")
    @classmethod
    def _validate_session_id(cls, v: Any) -> str | None:
        return _blank_to_none(None if v is None else str(v).strip())

    @field_validator("created_by", mode="before")
    @classmethod
    def _validate_created_by(cls, v: Any) -> str:
        return "user" if v == "user" else "agent"


class AnalyticsReportUpdateRequest(RequestModel):
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


class AnalyticsSessionRecord(EntityModel):
    id: str
    user_id: str
    site_id: str
    title: str
    about: str
    session_key: str | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class AnalyticsSourceRecord(EntityModel):
    id: str
    user_id: str
    site_id: str
    session_id: str
    name: str
    file_path: str | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class AnalyticsReportRecord(EntityModel):
    id: str
    user_id: str
    site_id: str
    session_id: str | None = None
    title: str
    html: str
    created_by: str
    created_at: JsDateTime
    updated_at: JsDateTime


class AnalyticsReportSummaryRecord(EntityModel):
    id: str
    user_id: str
    site_id: str
    session_id: str | None = None
    title: str
    created_by: str
    html_bytes: int
    created_at: JsDateTime
    updated_at: JsDateTime

    @classmethod
    def from_report(cls, report: AnalyticsReportRecord) -> "AnalyticsReportSummaryRecord":
        return cls(
            id=report.id,
            user_id=report.user_id,
            site_id=report.site_id,
            session_id=report.session_id,
            title=report.title,
            created_by=report.created_by,
            html_bytes=len(report.html.encode("utf-8")),
            created_at=report.created_at,
            updated_at=report.updated_at,
        )


class AnalyticsSessionResponse(EntityModel):
    id: str
    site_id: str
    title: str
    about: str
    session_key: str | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class AnalyticsSessionListItemResponse(AnalyticsSessionResponse):
    pass


class AnalyticsSessionDeleteResponse(EntityModel):
    id: str
    deleted: bool = Field(default=True)


class AnalyticsSourceResponse(EntityModel):
    id: str
    site_id: str
    session_id: str
    name: str
    file_path: str | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class AnalyticsSourceListItemResponse(AnalyticsSourceResponse):
    pass


class AnalyticsSourceDeleteResponse(EntityModel):
    id: str
    deleted: bool = Field(default=True)


class AnalyticsReportResponse(EntityModel):
    id: str
    site_id: str
    session_id: str | None = None
    title: str
    html: str
    created_by: str
    created_at: JsDateTime
    updated_at: JsDateTime


class AnalyticsReportSummaryResponse(EntityModel):
    id: str
    site_id: str
    session_id: str | None = None
    title: str
    created_by: str
    html_bytes: int
    created_at: JsDateTime
    updated_at: JsDateTime


class AnalyticsReportListItemResponse(AnalyticsReportSummaryResponse):
    pass


class AnalyticsReportDeleteResponse(EntityModel):
    id: str
    deleted: bool = Field(default=True)


class AnalyticsWorkspaceResult(EntityModel):
    sessions: list[AnalyticsSessionRecord]
    sources: list[AnalyticsSourceRecord]
    reports: list[AnalyticsReportSummaryRecord]


class AnalyticsWorkspaceResponse(EntityModel):
    sessions: list[AnalyticsSessionResponse]
    sources: list[AnalyticsSourceResponse]
    reports: list[AnalyticsReportSummaryResponse]
