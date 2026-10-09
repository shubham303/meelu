from typing import Literal

from pydantic import Field

from src.core.schemas import EntityModel, JsDateTime, RequestModel
from src.scratchpad.constants import MAX_BATCH_SIZE

RowStatus = Literal["pending", "processing", "done", "failed"]
SearchableStatus = Literal["pending", "done", "failed"]


class ScratchpadMetrics(EntityModel):
    total: int = 0
    pending: int = 0
    processing: int = 0
    done: int = 0
    failed: int = 0


class ScratchpadRecord(EntityModel):
    id: str
    user_id: str
    tool_name: str
    created_at: JsDateTime
    updated_at: JsDateTime


class ScratchpadRowRecord(EntityModel):
    scratchpad_id: str
    row_id: int
    text: str
    text_hash: str
    status: RowStatus
    status_updated_at: JsDateTime
    attempt_count: int
    priority: int
    result: str | None = None
    error_reason: str | None = None


class NewRow(EntityModel):
    row_id: int
    text: str
    text_hash: str
    priority: int


class RowView(EntityModel):
    row_id: int
    text: str
    priority: int
    attempt_count: int
    status: RowStatus


class FailedRowView(EntityModel):
    row_id: int
    text: str
    attempt_count: int
    error_reason: str | None = None
    result: str | None = None


class ScratchpadCreateRequest(RequestModel):
    tool_name: str = Field(min_length=1)
    items: list[str]
    priorities: list[int] | None = None


class ScratchpadAppendRequest(RequestModel):
    items: list[str]
    priorities: list[int] | None = None


class RowStatusUpdate(RequestModel):
    row_id: int
    status: str
    result: str | None = None
    error_reason: str | None = None


class StatusUpdateRequest(RequestModel):
    updates: list[RowStatusUpdate] = Field(min_length=1)


class NextRequest(RequestModel):
    n: int = Field(default=10, ge=1)


class ClaimRequest(RequestModel):
    row_ids: list[int] = Field(min_length=1, max_length=MAX_BATCH_SIZE)


class ScratchpadCreated(EntityModel):
    scratchpad_id: str
    total_rows: int
    duplicates_skipped: int
    sample: str | None = None


class RowsAppended(EntityModel):
    added: int
    duplicates_skipped: int
    metrics: ScratchpadMetrics


class ScratchpadInfo(EntityModel):
    id: str
    tool_name: str
    created_at: JsDateTime
    updated_at: JsDateTime
    metrics: ScratchpadMetrics


class RowOutcome(EntityModel):
    row_id: int
    ok: bool
    status: RowStatus | None = None
    error: str | None = None


class StatusUpdateResult(EntityModel):
    outcomes: list[RowOutcome]
    metrics: ScratchpadMetrics


class NextResult(EntityModel):
    rows: list[RowView]
    metrics: ScratchpadMetrics
    message: str


class UnclaimedRow(EntityModel):
    row_id: int
    reason: str


class ClaimResult(EntityModel):
    rows: list[RowView]
    not_claimed: list[UnclaimedRow]
    metrics: ScratchpadMetrics


class FailedRowsResult(EntityModel):
    rows: list[FailedRowView]
    total: int
    metrics: ScratchpadMetrics


class SearchResult(EntityModel):
    rows: list[RowView]
    total: int
    metrics: ScratchpadMetrics


class ScratchpadDeleted(EntityModel):
    id: str
    deleted: bool = True


class SpilledOutput(EntityModel):
    scratchpad_id: str
    total_rows: int
    duplicates_skipped: int
    sample: str | None = None
    guidance: str


class CleanupResult(EntityModel):
    reset: int
    failed: int
    deleted: int
