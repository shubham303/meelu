from typing import Any, ClassVar

from pydantic import Field, field_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel

MAX_ERROR_CHARS = 500
MAX_SAMPLES = 10
MAX_HOSTS = 50
MAX_STRINGS = 100
MIN_STALE_MS = 60_000

RENDER_SCOPES = ("sample", "all")
USER_AGENT_PROFILES = ("googlebot", "generic", "ai_bot")
RENDER_DEVICES = ("desktop", "mobile")


def _strings(raw: Any, cap: int) -> list[str]:
    if not isinstance(raw, list):
        return []
    values = [str(v if v is not None else "").strip() for v in raw]
    return [v for v in values if v][:cap]


def _samples(raw: Any) -> list[Any]:
    if not isinstance(raw, list):
        return []
    return [s for s in raw if isinstance(s, (dict, str))][:MAX_SAMPLES]


def _count(v: Any) -> int:
    if isinstance(v, bool) or v is None:
        return 0
    try:
        return max(0, int(float(v)))
    except (TypeError, ValueError):
        return 0


def _optional_int(v: Any) -> int | None:
    if isinstance(v, bool) or v is None:
        return None
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _optional_text(v: Any) -> str | None:
    return v if isinstance(v, str) and v != "" else None


def _device(v: Any) -> str:
    return v if v in RENDER_DEVICES else "desktop"


class RenderJobOpenRequest(RequestModel):
    trigger: str = "api"
    scope: str = "sample"
    device: str = "desktop"
    user_agent_profile: str = "googlebot"

    @field_validator("device", mode="before")
    @classmethod
    def _validate_device(cls, v: Any) -> str:
        return _device(v)

    @field_validator("trigger", mode="before")
    @classmethod
    def _validate_trigger(cls, v: Any) -> str:
        return v if isinstance(v, str) and v else "api"

    @field_validator("scope", mode="before")
    @classmethod
    def _validate_scope(cls, v: Any) -> str:
        return v if v in RENDER_SCOPES else "sample"

    @field_validator("user_agent_profile", mode="before")
    @classmethod
    def _validate_profile(cls, v: Any) -> str:
        return v if v in USER_AGENT_PROFILES else "googlebot"


class RenderJobReapRequest(RequestModel):
    stale_ms: float | None = None

    @field_validator("stale_ms", mode="before")
    @classmethod
    def _validate_stale_ms(cls, v: Any) -> float | None:
        if isinstance(v, bool) or not isinstance(v, (int, float, str)):
            return None
        try:
            n = float(v)
        except ValueError:
            return None
        if n == 0 or n >= MIN_STALE_MS:
            return n
        return None


class RenderJobUpdateRequest(RequestModel):
    status: str | None = None
    heartbeat: bool | None = None
    reason: str | None = None
    error: str | None = None
    rendered: int | None = None
    failed: int | None = None

    @field_validator("error", mode="before")
    @classmethod
    def _validate_error(cls, v: Any) -> str | None:
        return v[:MAX_ERROR_CHARS] if isinstance(v, str) else None

    @field_validator("rendered", "failed", mode="before")
    @classmethod
    def _validate_counter(cls, v: Any) -> int | None:
        return _optional_int(v)

    def counters(self) -> dict[str, int]:
        return self.model_dump(include={"rendered", "failed"}, exclude_none=True)


class PageRenderCreateRequest(RequestModel):
    page_id: str
    device: str = "desktop"
    render_error: str | None = None
    user_agent_profile: str = "googlebot"
    rendered_from_hash: str | None = None
    final_url: str | None = None
    title: str | None = None
    meta_description: str | None = None
    canonical: str | None = None
    h1: list[str] = Field(default_factory=list)
    robots_directives: str | None = None
    word_count: int = 0
    internal_links: int = 0
    schema_types: list[str] = Field(default_factory=list)
    content_hash: str | None = None
    console_errors: int = 0
    console_samples: list[Any] = Field(default_factory=list)
    failed_requests: int = 0
    failed_samples: list[Any] = Field(default_factory=list)
    blocked_assets: int = 0
    blocked_samples: list[Any] = Field(default_factory=list)
    js_bytes: int = 0
    total_bytes: int = 0
    request_count: int = 0
    third_party_hosts: list[str] = Field(default_factory=list)
    hidden_word_count: int | None = None
    hidden_internal_links: int | None = None
    viewport_overflow_px: int | None = None
    small_tap_targets: int | None = None
    html_path: str | None = None

    @field_validator("page_id", mode="before")
    @classmethod
    def _validate_page_id(cls, v: Any) -> str:
        page_id = ("" if v is None else str(v)).strip()
        if not page_id:
            raise ValueError("pageId is required.")
        return page_id

    @field_validator("device", mode="before")
    @classmethod
    def _validate_device(cls, v: Any) -> str:
        return _device(v)

    @field_validator(
        "hidden_word_count",
        "hidden_internal_links",
        "viewport_overflow_px",
        "small_tap_targets",
        mode="before",
    )
    @classmethod
    def _validate_mobile_count(cls, v: Any) -> int | None:
        n = _optional_int(v)
        return None if n is None or n < 0 else n

    @field_validator("user_agent_profile", mode="before")
    @classmethod
    def _validate_profile(cls, v: Any) -> str:
        return v if v in USER_AGENT_PROFILES else "googlebot"

    @field_validator("render_error", mode="before")
    @classmethod
    def _validate_render_error(cls, v: Any) -> str | None:
        return v[:MAX_ERROR_CHARS] if isinstance(v, str) and v != "" else None

    @field_validator(
        "rendered_from_hash",
        "final_url",
        "title",
        "meta_description",
        "canonical",
        "robots_directives",
        "content_hash",
        "html_path",
        mode="before",
    )
    @classmethod
    def _validate_optional_text(cls, v: Any) -> str | None:
        return _optional_text(v)

    @field_validator("h1", "schema_types", mode="before")
    @classmethod
    def _validate_strings(cls, v: Any) -> list[str]:
        return _strings(v, MAX_STRINGS)

    @field_validator("third_party_hosts", mode="before")
    @classmethod
    def _validate_hosts(cls, v: Any) -> list[str]:
        return _strings(v, MAX_HOSTS)

    @field_validator("console_samples", "failed_samples", "blocked_samples", mode="before")
    @classmethod
    def _validate_samples(cls, v: Any) -> list[Any]:
        return _samples(v)

    @field_validator(
        "word_count",
        "internal_links",
        "console_errors",
        "failed_requests",
        "blocked_assets",
        "js_bytes",
        "total_bytes",
        "request_count",
        mode="before",
    )
    @classmethod
    def _validate_count(cls, v: Any) -> int:
        return _count(v)

    def values(self) -> dict[str, Any]:
        return self.model_dump(exclude={"page_id", "device"})


class RenderJobRecord(EntityModel):
    keep_null: ClassVar[frozenset[str]] = frozenset({"finishedAt", "error"})

    id: str
    user_id: str
    site_id: str
    status: str
    trigger: str
    scope: str
    device: str
    user_agent_profile: str
    started_at: JsDateTime | None = None
    finished_at: JsDateTime | None = None
    heartbeat_at: JsDateTime | None = None
    total: int
    rendered: int
    failed: int
    error: str | None = None
    stop_reason: str | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class PageRenderRecord(EntityModel):
    id: str
    site_id: str
    page_id: str
    device: str
    rendered_at: JsDateTime
    render_error: str | None = None
    user_agent_profile: str
    rendered_from_hash: str | None = None
    final_url: str | None = None
    title: str | None = None
    meta_description: str | None = None
    canonical: str | None = None
    h1: list[str]
    robots_directives: str | None = None
    word_count: int
    internal_links: int
    schema_types: list[str]
    content_hash: str | None = None
    console_errors: int
    console_samples: list[Any]
    failed_requests: int
    failed_samples: list[Any]
    blocked_assets: int
    blocked_samples: list[Any]
    js_bytes: int
    total_bytes: int
    request_count: int
    third_party_hosts: list[str]
    hidden_word_count: int | None = None
    hidden_internal_links: int | None = None
    viewport_overflow_px: int | None = None
    small_tap_targets: int | None = None
    html_path: str | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class RenderCandidateRecord(EntityModel):
    page_id: str
    url: str
    kind: str
    content_hash: str | None = None
    rendered_from_hash: str | None = None


class RenderCountsRecord(EntityModel):
    rendered: int
    eligible: int
    pending: int
    last_rendered_at: JsDateTime | None = None


class RenderTargetRecord(EntityModel):
    site_id: str
    domain: str
    robots_txt: str | None = None


class RenderJobStartResult(EntityModel):
    started: bool
    job: RenderJobRecord | None = None
    reason: str | None = None


class RenderJobClaimResult(EntityModel):
    job: RenderJobRecord
    target: RenderTargetRecord
    pages: list[RenderCandidateRecord]


class RenderJobBeatResult(EntityModel):
    stop: bool


class RenderJobStatusRecord(EntityModel):
    site_id: str
    job_id: str | None = None
    state: str
    active: bool
    device: str
    trigger: str | None = None
    scope: str | None = None
    user_agent_profile: str | None = None
    started_at: JsDateTime | None = None
    finished_at: JsDateTime | None = None
    total: int = 0
    rendered: int = 0
    failed: int = 0
    error: str | None = None
    stop_reason: str | None = None
    rendered_pages: int
    eligible_pages: int
    pending_pages: int
    last_rendered_at: JsDateTime | None = None


class RenderJobResponse(EntityModel):
    keep_null: ClassVar[frozenset[str]] = frozenset({"finishedAt", "error"})

    id: str
    site_id: str
    status: str
    trigger: str
    scope: str
    device: str
    user_agent_profile: str
    started_at: JsDateTime | None = None
    finished_at: JsDateTime | None = None
    heartbeat_at: JsDateTime | None = None
    total: int
    rendered: int
    failed: int
    error: str | None = None
    stop_reason: str | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class PageRenderResponse(PageRenderRecord):
    pass


class RenderJobStatusResponse(EntityModel):
    status: RenderJobStatusRecord


class RenderJobStartResponse(EntityModel):
    started: bool
    job: RenderJobResponse | None = None
    reason: str | None = None


class RenderJobReapResponse(EntityModel):
    reaped: int
    jobs: list[RenderJobResponse]


class RenderJobBeatResponse(EntityModel):
    stop: bool


class RenderJobClaimResponse(EntityModel):
    job: RenderJobResponse
    target: RenderTargetRecord
    pages: list[RenderCandidateRecord]
