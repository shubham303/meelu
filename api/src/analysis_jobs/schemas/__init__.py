from typing import Any, ClassVar

from pydantic import Field, field_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel

MAX_TOPICS = 50
MAX_STRINGS = 100
MAX_ERROR_CHARS = 500
MIN_STALE_MS = 60_000


def _strings(raw: Any, cap: int) -> list[str]:
    if not isinstance(raw, list):
        return []
    values = [str(v if v is not None else "").strip() for v in raw]
    return [v for v in values if v][:cap]


class AnalysisTopic(EntityModel):
    topic: str
    section: str | None = None


def _topics(raw: Any) -> list[AnalysisTopic]:
    if not isinstance(raw, list):
        return []
    topics: list[AnalysisTopic] = []
    for t in raw:
        if isinstance(t, str):
            topic, section = t.strip(), None
        elif isinstance(t, dict) and isinstance(t.get("topic"), str):
            topic = str(t["topic"]).strip()
            raw_section = t.get("section")
            section = (
                raw_section.strip()
                if isinstance(raw_section, str) and raw_section.strip() != ""
                else None
            )
        else:
            continue
        if topic:
            topics.append(AnalysisTopic(topic=topic, section=section))
    return topics[:MAX_TOPICS]


class AnalysisJobOpenRequest(RequestModel):
    trigger: str = "api"

    @field_validator("trigger", mode="before")
    @classmethod
    def _validate_trigger(cls, v: Any) -> str:
        return v if isinstance(v, str) and v else "api"


class AnalysisJobReapRequest(RequestModel):
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


class AnalysisJobUpdateRequest(RequestModel):
    status: str | None = None
    heartbeat: bool | None = None
    reason: str | None = None
    error: str | None = None
    processed: int | None = None
    skipped_unchanged: int | None = None
    skipped_similar: int | None = None
    failed: int | None = None

    @field_validator("error", mode="before")
    @classmethod
    def _validate_error(cls, v: Any) -> str | None:
        return v[:MAX_ERROR_CHARS] if isinstance(v, str) else None

    @field_validator("processed", "skipped_unchanged", "skipped_similar", "failed", mode="before")
    @classmethod
    def _validate_counter(cls, v: Any) -> int | None:
        if isinstance(v, bool) or v is None:
            return None
        try:
            return int(float(v))
        except (TypeError, ValueError):
            return None

    def counters(self) -> dict[str, int]:
        return self.model_dump(
            include={"processed", "skipped_unchanged", "skipped_similar", "failed"},
            exclude_none=True,
        )


class PageAnalysisCreateRequest(RequestModel):
    page_id: str
    topics: list[AnalysisTopic] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    questions_answered: list[str] = Field(default_factory=list)
    analyzed_from_hash: str | None = None
    analyzed_text: str | None = None
    model: str | None = None
    refresh_only: bool = False

    @field_validator("page_id", mode="before")
    @classmethod
    def _validate_page_id(cls, v: Any) -> str:
        page_id = ("" if v is None else str(v)).strip()
        if not page_id:
            raise ValueError("pageId is required.")
        return page_id

    @field_validator("topics", mode="before")
    @classmethod
    def _validate_topics(cls, v: Any) -> list[AnalysisTopic]:
        return _topics(v)

    @field_validator("keywords", "questions_answered", mode="before")
    @classmethod
    def _validate_strings(cls, v: Any) -> list[str]:
        return _strings(v, MAX_STRINGS)

    @field_validator("analyzed_from_hash", "model", mode="before")
    @classmethod
    def _validate_optional_text(cls, v: Any) -> str | None:
        return v if isinstance(v, str) and v != "" else None

    @field_validator("analyzed_text", mode="before")
    @classmethod
    def _validate_analyzed_text(cls, v: Any) -> str | None:
        return v if isinstance(v, str) else None

    @field_validator("refresh_only", mode="before")
    @classmethod
    def _validate_refresh_only(cls, v: Any) -> bool:
        return v is True


class AnalysisJobRecord(EntityModel):
    keep_null: ClassVar[frozenset[str]] = frozenset({"finishedAt", "error"})

    id: str
    user_id: str
    site_id: str
    status: str
    trigger: str
    started_at: JsDateTime | None = None
    finished_at: JsDateTime | None = None
    heartbeat_at: JsDateTime | None = None
    total: int
    processed: int
    skipped_unchanged: int
    skipped_similar: int
    failed: int
    error: str | None = None
    stop_reason: str | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class PageAnalysisRecord(EntityModel):
    id: str
    user_id: str
    site_id: str
    page_id: str
    topics: list[Any]
    keywords: list[str]
    questions_answered: list[str]
    analyzed_from_hash: str | None = None
    analyzed_text: str | None = None
    model: str | None = None
    analyzed_at: JsDateTime
    created_at: JsDateTime
    updated_at: JsDateTime


class AnalysisCandidateRecord(EntityModel):
    page_id: str
    url: str
    content_hash: str | None = None
    analyzed_from_hash: str | None = None


class AnalysisCountsRecord(EntityModel):
    analyzed: int
    eligible: int


class AnalysisTargetRecord(EntityModel):
    site_id: str
    domain: str


class AnalysisJobStartResult(EntityModel):
    started: bool
    job: AnalysisJobRecord | None = None
    reason: str | None = None


class AnalysisJobClaimResult(EntityModel):
    job: AnalysisJobRecord
    target: AnalysisTargetRecord
    pages: list[AnalysisCandidateRecord]


class AnalysisJobBeatResult(EntityModel):
    stop: bool


class AnalysisJobStatusRecord(EntityModel):
    site_id: str
    job_id: str | None = None
    state: str
    active: bool
    trigger: str | None = None
    started_at: JsDateTime | None = None
    finished_at: JsDateTime | None = None
    total: int = 0
    processed: int = 0
    skipped_unchanged: int = 0
    skipped_similar: int = 0
    failed: int = 0
    error: str | None = None
    stop_reason: str | None = None
    analyzed_pages: int
    eligible_pages: int


class AnalysisJobResponse(EntityModel):
    keep_null: ClassVar[frozenset[str]] = frozenset({"finishedAt", "error"})

    id: str
    site_id: str
    status: str
    trigger: str
    started_at: JsDateTime | None = None
    finished_at: JsDateTime | None = None
    heartbeat_at: JsDateTime | None = None
    total: int
    processed: int
    skipped_unchanged: int
    skipped_similar: int
    failed: int
    error: str | None = None
    stop_reason: str | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class PageAnalysisResponse(EntityModel):
    id: str
    site_id: str
    page_id: str
    topics: list[Any]
    keywords: list[str]
    questions_answered: list[str]
    analyzed_from_hash: str | None = None
    analyzed_text: str | None = None
    model: str | None = None
    analyzed_at: JsDateTime
    created_at: JsDateTime
    updated_at: JsDateTime


class AnalysisJobStatusResponse(EntityModel):
    status: AnalysisJobStatusRecord


class AnalysisJobStartResponse(EntityModel):
    started: bool
    job: AnalysisJobResponse | None = None
    reason: str | None = None


class AnalysisJobReapResponse(EntityModel):
    reaped: int
    jobs: list[AnalysisJobResponse]


class AnalysisJobBeatResponse(EntityModel):
    stop: bool


class AnalysisJobClaimResponse(EntityModel):
    job: AnalysisJobResponse
    target: AnalysisTargetRecord
    pages: list[AnalysisCandidateRecord]
