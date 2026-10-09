from src.agent.context import current
from src.agent.server import tool
from src.core.database import unit_of_work
from src.scratchpad.schemas import (
    ClaimResult,
    FailedRowsResult,
    NextResult,
    RowStatusUpdate,
    ScratchpadDeleted,
    ScratchpadInfo,
    ScratchpadMetrics,
    SearchResult,
    StatusUpdateResult,
)
from src.scratchpad.service import scratchpad_service


@tool()
def what_is_scratchpad() -> str:
    """Explains scratchpads: where tools park large results so you read them in
    batches instead of all at once. Call it before working through one."""
    return scratchpad_service.explain()


@tool()
async def scratchpad_next(scratchpad_id: str, n: int = 10) -> NextResult:
    """Claim the next n pending rows of a scratchpad (highest priority first, max 50).
    Record every claimed row's outcome with scratchpad_update_status."""
    ctx = current()
    async with unit_of_work() as db:
        return await scratchpad_service.next(db, ctx.user_id, scratchpad_id, n)


@tool()
async def scratchpad_claim(scratchpad_id: str, row_ids: list[int]) -> ClaimResult:
    """Claim specific pending rows by row_id, e.g. after scratchpad_search or to hand
    rows to a subagent. Reports rows that could not be claimed and why."""
    ctx = current()
    async with unit_of_work() as db:
        return await scratchpad_service.claim_rows(db, ctx.user_id, scratchpad_id, row_ids)


@tool()
async def scratchpad_update_status(
    scratchpad_id: str, updates: list[RowStatusUpdate]
) -> StatusUpdateResult:
    """Record outcomes for claimed rows: done, failed (needs error_reason) or pending
    to release one; failed rows go back to pending to retry. Each update succeeds or
    fails on its own."""
    ctx = current()
    async with unit_of_work() as db:
        return await scratchpad_service.update_status(db, ctx.user_id, scratchpad_id, updates)


@tool()
async def scratchpad_metrics(scratchpad_id: str) -> ScratchpadMetrics:
    """Row counts of a scratchpad by status."""
    ctx = current()
    async with unit_of_work() as db:
        return await scratchpad_service.get_metrics(db, ctx.user_id, scratchpad_id)


@tool()
async def scratchpad_get_failed(
    scratchpad_id: str, offset: int = 0, limit: int = 10
) -> FailedRowsResult:
    """Failed rows of a scratchpad with their error_reason and attempt_count."""
    ctx = current()
    async with unit_of_work() as db:
        return await scratchpad_service.get_failed(db, ctx.user_id, scratchpad_id, offset, limit)


@tool()
async def scratchpad_search(
    scratchpad_id: str,
    query: str,
    status: str | None = None,
    offset: int = 0,
    limit: int = 10,
) -> SearchResult:
    """Case-insensitive keyword search over a scratchpad's rows, optionally by status
    (pending, done, failed). Read-only: claim matches with scratchpad_claim."""
    ctx = current()
    async with unit_of_work() as db:
        return await scratchpad_service.search(
            db, ctx.user_id, scratchpad_id, query, status, offset, limit
        )


@tool()
async def scratchpad_info(scratchpad_id: str) -> ScratchpadInfo:
    """A scratchpad's producing tool, timestamps and row counts."""
    ctx = current()
    async with unit_of_work() as db:
        return await scratchpad_service.get_scratchpad(db, ctx.user_id, scratchpad_id)


@tool()
async def scratchpad_delete(scratchpad_id: str, force: bool = False) -> ScratchpadDeleted:
    """Delete a scratchpad once every row is done. force=true discards unfinished rows;
    use it only when you are sure."""
    ctx = current()
    async with unit_of_work() as db:
        return await scratchpad_service.delete_scratchpad(db, ctx.user_id, scratchpad_id, force)
