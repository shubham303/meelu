import hashlib
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.scratchpad.constants import (
    CHAR_THRESHOLD,
    MAX_ATTEMPTS,
    MAX_BATCH_SIZE,
    MAX_ROW_CHARS_RETURNED,
    ROW_COUNT_THRESHOLD,
    STUCK_AFTER_MINUTES,
    TTL_HOURS,
)
from src.scratchpad.repository import scratchpad_rows, scratchpads
from src.scratchpad.schemas import (
    ClaimResult,
    CleanupResult,
    FailedRowsResult,
    FailedRowView,
    NewRow,
    NextResult,
    RowOutcome,
    RowsAppended,
    RowStatusUpdate,
    RowView,
    ScratchpadCreated,
    ScratchpadDeleted,
    ScratchpadInfo,
    ScratchpadMetrics,
    ScratchpadRecord,
    ScratchpadRowRecord,
    SearchResult,
    SpilledOutput,
    StatusUpdateResult,
    UnclaimedRow,
)

STATUSES = ("pending", "processing", "done", "failed")
VISIBLE_STATUSES = ("pending", "done", "failed")
ALLOWED_TRANSITIONS = frozenset(
    {
        ("processing", "done"),
        ("processing", "failed"),
        ("processing", "pending"),
        ("failed", "pending"),
    }
)
TIMED_OUT_REASON = f"timed out after {MAX_ATTEMPTS} attempts"
EXPLAINER = f"""\
A scratchpad is a temporary work queue where a tool writes a large result instead \
of returning it into your context. The tool hands you a scratchpad_id, a row \
count and one sample row; each row is self-describing text.

How to work through one:
1. scratchpad_next claims a batch of pending rows (highest priority first, at most \
{MAX_BATCH_SIZE}) and marks them processing so no other agent gets them.
2. Handle each row yourself or hand it to a subagent; scratchpad_search finds rows \
by keyword and scratchpad_claim claims specific ones.
3. Record every claimed row with scratchpad_update_status: done (optionally with a \
result), failed with an error_reason, or pending to give it back.
4. Repeat until scratchpad_next says all items are processed. If it says rows are \
still processing, other agents are working; check scratchpad_metrics later.
5. scratchpad_get_failed lists failures; set a failed row to pending to retry it.

Only tools create scratchpads and add rows; you read, claim and update them. A \
scratchpad is working memory for this run, not a saved result: it expires \
{TTL_HOURS} hours after its last change, and a row left processing for \
{STUCK_AFTER_MINUTES} minutes returns to pending (failed after {MAX_ATTEMPTS} \
attempts). Delete it with scratchpad_delete when you are done."""


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def truncated(text: str) -> str:
    cut = len(text) - MAX_ROW_CHARS_RETURNED
    if cut <= 0:
        return text
    return f"{text[:MAX_ROW_CHARS_RETURNED]}\n[… {cut} more characters truncated]"


def needs_scratchpad(items: list[str]) -> bool:
    return len(items) > ROW_COUNT_THRESHOLD or sum(len(i) for i in items) > CHAR_THRESHOLD


def not_found(scratchpad_id: str) -> HTTPException:
    return HTTPException(
        404,
        f"Scratchpad {scratchpad_id} not found; it may have expired. "
        "Re-run the tool that created it if the data is still needed.",
    )


def row_view(row: ScratchpadRowRecord) -> RowView:
    return RowView(
        row_id=row.row_id,
        text=truncated(row.text),
        priority=row.priority,
        attempt_count=row.attempt_count,
        status=row.status,
    )


def claim_order(rows: list[ScratchpadRowRecord]) -> list[ScratchpadRowRecord]:
    return sorted(rows, key=lambda r: (-r.priority, r.row_id))


def unclaimable_reason(status: str) -> str:
    if status == "processing":
        return "already being processed by another agent"
    if status == "done":
        return "already done"
    return "failed; set it to pending with scratchpad_update_status to retry, then claim it"


def transition_error(row_id: int, current: str, target: str) -> str:
    if target == "processing":
        return (
            f"Row {row_id}: rows become processing only by claiming them; "
            "use scratchpad_next or scratchpad_claim."
        )
    if current == "pending":
        return f"Row {row_id} is pending, not claimed. Claim it with scratchpad_claim first."
    if current == "done":
        return f"Row {row_id} is already done; done rows cannot change."
    if current == "failed":
        return f"Row {row_id} is failed. Set it to pending to retry it, then claim it again."
    return f"Row {row_id} cannot move from {current} to {target}."


class ScratchpadService:
    async def create_scratchpad(
        self,
        db: AsyncSession,
        user_id: str,
        tool_name: str,
        items: list[str],
        priorities: list[int] | None = None,
    ) -> ScratchpadCreated:
        self._check_priorities(items, priorities)
        now = datetime.now(UTC)
        pad = await scratchpads.create(db, user_id, tool_name, now)
        added, skipped = await self._insert(db, pad.id, items, priorities, now)
        first = await scratchpad_rows.first(db, pad.id)
        return ScratchpadCreated(
            scratchpad_id=pad.id,
            total_rows=added,
            duplicates_skipped=skipped,
            sample=None if first is None else truncated(first.text),
        )

    async def spill(
        self,
        db: AsyncSession,
        user_id: str,
        tool_name: str,
        items: list[str],
        priorities: list[int] | None = None,
    ) -> SpilledOutput:
        created = await self.create_scratchpad(db, user_id, tool_name, items, priorities)
        return SpilledOutput(
            scratchpad_id=created.scratchpad_id,
            total_rows=created.total_rows,
            duplicates_skipped=created.duplicates_skipped,
            sample=created.sample,
            guidance=(
                f"Output stored in scratchpad {created.scratchpad_id} "
                f"({created.total_rows} items). Use scratchpad_next to process in batches "
                "and scratchpad_update_status to record each item's outcome."
            ),
        )

    async def append_rows(
        self,
        db: AsyncSession,
        user_id: str,
        scratchpad_id: str,
        items: list[str],
        priorities: list[int] | None = None,
    ) -> RowsAppended:
        self._check_priorities(items, priorities)
        await self._locked(db, user_id, scratchpad_id)
        now = datetime.now(UTC)
        added, skipped = await self._insert(db, scratchpad_id, items, priorities, now)
        if added:
            await scratchpads.touch(db, scratchpad_id, now)
        return RowsAppended(
            added=added,
            duplicates_skipped=skipped,
            metrics=await self.metrics(db, scratchpad_id),
        )

    async def delete_scratchpad(
        self, db: AsyncSession, user_id: str, scratchpad_id: str, force: bool = False
    ) -> ScratchpadDeleted:
        await self._locked(db, user_id, scratchpad_id)
        if not force:
            m = await self.metrics(db, scratchpad_id)
            if m.done != m.total:
                raise HTTPException(
                    409,
                    f"Scratchpad {scratchpad_id} still has unfinished rows "
                    f"(total {m.total}: {m.pending} pending, {m.processing} processing, "
                    f"{m.done} done, {m.failed} failed). Set force=true only if you are "
                    "sure these unfinished rows should be discarded.",
                )
        await scratchpads.delete(db, scratchpad_id)
        return ScratchpadDeleted(id=scratchpad_id)

    async def update_status(
        self,
        db: AsyncSession,
        user_id: str,
        scratchpad_id: str,
        updates: list[RowStatusUpdate],
    ) -> StatusUpdateResult:
        await self._locked(db, user_id, scratchpad_id)
        now = datetime.now(UTC)
        rows = await scratchpad_rows.get_many(db, scratchpad_id, list({u.row_id for u in updates}))
        current = {r.row_id: r.status for r in rows}
        outcomes: list[RowOutcome] = []
        changed = False
        for u in updates:
            error = self._rejection(u, current.get(u.row_id))
            if error is not None:
                outcomes.append(RowOutcome(row_id=u.row_id, ok=False, error=error))
                continue
            values: dict = {"status": u.status, "status_updated_at": now}
            if u.result is not None:
                values["result"] = u.result
            values["error_reason"] = u.error_reason.strip() if u.status == "failed" else None
            await scratchpad_rows.update(db, scratchpad_id, u.row_id, values)
            current[u.row_id] = u.status
            changed = True
            outcomes.append(RowOutcome(row_id=u.row_id, ok=True, status=u.status))
        if changed:
            await scratchpads.touch(db, scratchpad_id, now)
        return StatusUpdateResult(outcomes=outcomes, metrics=await self.metrics(db, scratchpad_id))

    async def get_metrics(
        self, db: AsyncSession, user_id: str, scratchpad_id: str
    ) -> ScratchpadMetrics:
        await self._existing(db, user_id, scratchpad_id)
        return await self.metrics(db, scratchpad_id)

    async def next(
        self, db: AsyncSession, user_id: str, scratchpad_id: str, n: int = 10
    ) -> NextResult:
        await self._locked(db, user_id, scratchpad_id)
        now = datetime.now(UTC)
        wanted = await scratchpad_rows.pending_ids(
            db, scratchpad_id, max(1, min(n, MAX_BATCH_SIZE))
        )
        claimed = claim_order(await scratchpad_rows.mark_processing(db, scratchpad_id, wanted, now))
        if claimed:
            await scratchpads.touch(db, scratchpad_id, now)
        m = await self.metrics(db, scratchpad_id)
        return NextResult(
            rows=[row_view(r) for r in claimed],
            metrics=m,
            message=self._next_message(len(claimed), m),
        )

    async def claim_rows(
        self, db: AsyncSession, user_id: str, scratchpad_id: str, row_ids: list[int]
    ) -> ClaimResult:
        requested = list(dict.fromkeys(row_ids))
        if len(requested) > MAX_BATCH_SIZE:
            raise HTTPException(
                400, f"Claim at most {MAX_BATCH_SIZE} rows per call; split the request."
            )
        await self._locked(db, user_id, scratchpad_id)
        now = datetime.now(UTC)
        found = {r.row_id: r for r in await scratchpad_rows.get_many(db, scratchpad_id, requested)}
        not_claimed: list[UnclaimedRow] = []
        claimable: list[int] = []
        for row_id in requested:
            row = found.get(row_id)
            if row is None:
                not_claimed.append(UnclaimedRow(row_id=row_id, reason="not found"))
            elif row.status != "pending":
                not_claimed.append(
                    UnclaimedRow(row_id=row_id, reason=unclaimable_reason(row.status))
                )
            else:
                claimable.append(row_id)
        claimed = claim_order(
            await scratchpad_rows.mark_processing(db, scratchpad_id, claimable, now)
        )
        if claimed:
            await scratchpads.touch(db, scratchpad_id, now)
        return ClaimResult(
            rows=[row_view(r) for r in claimed],
            not_claimed=not_claimed,
            metrics=await self.metrics(db, scratchpad_id),
        )

    async def get_scratchpad(
        self, db: AsyncSession, user_id: str, scratchpad_id: str
    ) -> ScratchpadInfo:
        pad = await self._existing(db, user_id, scratchpad_id)
        return ScratchpadInfo(
            id=pad.id,
            tool_name=pad.tool_name,
            created_at=pad.created_at,
            updated_at=pad.updated_at,
            metrics=await self.metrics(db, scratchpad_id),
        )

    async def get_failed(
        self,
        db: AsyncSession,
        user_id: str,
        scratchpad_id: str,
        offset: int = 0,
        limit: int = 10,
    ) -> FailedRowsResult:
        await self._existing(db, user_id, scratchpad_id)
        rows = await scratchpad_rows.page_by_status(
            db, scratchpad_id, "failed", max(0, offset), max(1, min(limit, MAX_BATCH_SIZE))
        )
        m = await self.metrics(db, scratchpad_id)
        return FailedRowsResult(
            rows=[
                FailedRowView(
                    row_id=r.row_id,
                    text=truncated(r.text),
                    attempt_count=r.attempt_count,
                    error_reason=r.error_reason,
                    result=r.result,
                )
                for r in rows
            ],
            total=m.failed,
            metrics=m,
        )

    async def search(
        self,
        db: AsyncSession,
        user_id: str,
        scratchpad_id: str,
        query: str,
        status: str | None = None,
        offset: int = 0,
        limit: int = 10,
    ) -> SearchResult:
        q = query.strip()
        if not q:
            raise HTTPException(400, "Pass a keyword to search for.")
        if status == "processing":
            raise HTTPException(
                400,
                "Rows being processed are never returned. Search pending, done or failed "
                "rows, or check scratchpad_metrics for the processing count.",
            )
        if status is not None and status not in VISIBLE_STATUSES:
            raise HTTPException(400, f"Unknown status '{status}'. Use pending, done or failed.")
        await self._existing(db, user_id, scratchpad_id)
        rows, total = await scratchpad_rows.search(
            db,
            scratchpad_id,
            f"%{self._escape_like(q)}%",
            [status] if status else list(VISIBLE_STATUSES),
            max(0, offset),
            max(1, min(limit, MAX_BATCH_SIZE)),
        )
        return SearchResult(
            rows=[row_view(r) for r in rows],
            total=total,
            metrics=await self.metrics(db, scratchpad_id),
        )

    def explain(self) -> str:
        return EXPLAINER

    async def cleanup(self, db: AsyncSession) -> CleanupResult:
        now = datetime.now(UTC)
        stuck_before = now - timedelta(minutes=STUCK_AFTER_MINUTES)
        reset = await scratchpad_rows.requeue_stuck(db, stuck_before, MAX_ATTEMPTS, now)
        failed = await scratchpad_rows.fail_stuck(
            db, stuck_before, MAX_ATTEMPTS, TIMED_OUT_REASON, now
        )
        deleted = await scratchpads.delete_updated_before(db, now - timedelta(hours=TTL_HOURS))
        return CleanupResult(reset=reset, failed=failed, deleted=deleted)

    async def metrics(self, db: AsyncSession, scratchpad_id: str) -> ScratchpadMetrics:
        counts = await scratchpad_rows.status_counts(db, scratchpad_id)
        return ScratchpadMetrics(total=sum(counts.values()), **counts)

    async def _existing(
        self, db: AsyncSession, user_id: str, scratchpad_id: str
    ) -> ScratchpadRecord:
        pad = await scratchpads.get(db, user_id, scratchpad_id)
        if pad is None:
            raise not_found(scratchpad_id)
        return pad

    async def _locked(self, db: AsyncSession, user_id: str, scratchpad_id: str) -> ScratchpadRecord:
        pad = await scratchpads.lock(db, user_id, scratchpad_id)
        if pad is None:
            raise not_found(scratchpad_id)
        return pad

    async def _insert(
        self,
        db: AsyncSession,
        scratchpad_id: str,
        items: list[str],
        priorities: list[int] | None,
        now: datetime,
    ) -> tuple[int, int]:
        hashes = [text_hash(i) for i in items]
        seen = await scratchpad_rows.existing_hashes(db, scratchpad_id, list(set(hashes)))
        next_id = await scratchpad_rows.max_row_id(db, scratchpad_id) + 1
        rows: list[NewRow] = []
        for index, (item, digest) in enumerate(zip(items, hashes, strict=True)):
            if digest in seen:
                continue
            seen.add(digest)
            rows.append(
                NewRow(
                    row_id=next_id + len(rows),
                    text=item,
                    text_hash=digest,
                    priority=priorities[index] if priorities else 0,
                )
            )
        if rows:
            await scratchpad_rows.insert(db, scratchpad_id, rows, now)
        return len(rows), len(items) - len(rows)

    def _check_priorities(self, items: list[str], priorities: list[int] | None) -> None:
        if priorities is not None and len(priorities) != len(items):
            raise HTTPException(
                400,
                f"Got {len(priorities)} priorities for {len(items)} items; "
                "pass one priority per item or none at all.",
            )

    def _rejection(self, u: RowStatusUpdate, current: str | None) -> str | None:
        if current is None:
            return f"Row {u.row_id} does not exist in this scratchpad."
        if u.status not in STATUSES:
            return f"Row {u.row_id}: unknown status '{u.status}'. Use pending, done or failed."
        if u.status == "failed" and not (u.error_reason or "").strip():
            return f"Row {u.row_id}: marking a row failed needs an error_reason saying why."
        if (current, u.status) not in ALLOWED_TRANSITIONS:
            return transition_error(u.row_id, current, u.status)
        return None

    def _next_message(self, claimed: int, m: ScratchpadMetrics) -> str:
        if claimed:
            return (
                f"Claimed {claimed} rows; {m.pending} still pending. Record each outcome "
                "with scratchpad_update_status."
            )
        if m.processing:
            return (
                f"No pending rows, but {m.processing} are still processing; other agents "
                "are still working. Check scratchpad_metrics later."
            )
        return f"All items processed: {m.done} done, {m.failed} failed."

    def _escape_like(self, q: str) -> str:
        return q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


scratchpad_service = ScratchpadService()
