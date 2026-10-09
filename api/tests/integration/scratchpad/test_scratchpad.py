import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import update

from src.agent.context import AgentContext, reset_context, set_context
from src.core.database import unit_of_work
from src.scratchpad import tools
from src.scratchpad.constants import (
    CHAR_THRESHOLD,
    MAX_ATTEMPTS,
    MAX_BATCH_SIZE,
    MAX_ROW_CHARS_RETURNED,
    ROW_COUNT_THRESHOLD,
    STUCK_AFTER_MINUTES,
    TTL_HOURS,
)
from src.scratchpad.models.scratchpad import Scratchpad
from src.scratchpad.models.scratchpad_row import ScratchpadRow
from src.scratchpad.repository import scratchpad_rows
from src.scratchpad.schemas import RowStatusUpdate
from src.scratchpad.service import needs_scratchpad, scratchpad_service

BASE = "/api/v1/scratchpads"


async def create(user_id, items, priorities=None, tool_name="test_tool"):
    async with unit_of_work() as db:
        return await scratchpad_service.create_scratchpad(db, user_id, tool_name, items, priorities)


async def next_rows(user_id, pad_id, n=10):
    async with unit_of_work() as db:
        return await scratchpad_service.next(db, user_id, pad_id, n)


async def claim(user_id, pad_id, row_ids):
    async with unit_of_work() as db:
        return await scratchpad_service.claim_rows(db, user_id, pad_id, row_ids)


async def set_status(user_id, pad_id, *updates):
    async with unit_of_work() as db:
        return await scratchpad_service.update_status(
            db, user_id, pad_id, [RowStatusUpdate(**u) for u in updates]
        )


async def statuses(pad_id):
    async with unit_of_work() as db:
        rows = await scratchpad_rows.get_many(db, pad_id, list(range(1, 1000)))
    return {r.row_id: r for r in rows}


async def test_create_skips_duplicates_and_returns_one_sample(user_id):
    created = await create(user_id, ["a", "b", "a", "c", "b"])
    assert created.total_rows == 3
    assert created.duplicates_skipped == 2
    assert created.sample == "a"
    rows = await statuses(created.scratchpad_id)
    assert [rows[i].text for i in sorted(rows)] == ["a", "b", "c"]
    assert all(r.status == "pending" and r.attempt_count == 0 for r in rows.values())


async def test_append_continues_sequence_and_skips_existing(user_id):
    created = await create(user_id, ["a", "b"])
    async with unit_of_work() as db:
        appended = await scratchpad_service.append_rows(
            db, user_id, created.scratchpad_id, ["b", "c", "d", "c"]
        )
    assert appended.added == 2
    assert appended.duplicates_skipped == 2
    assert appended.metrics.total == 4 and appended.metrics.pending == 4
    rows = await statuses(created.scratchpad_id)
    assert {i: r.text for i, r in rows.items()} == {1: "a", 2: "b", 3: "c", 4: "d"}


async def test_same_text_allowed_in_different_scratchpads(user_id):
    one = await create(user_id, ["shared"])
    two = await create(user_id, ["shared"])
    assert one.total_rows == two.total_rows == 1
    assert one.scratchpad_id != two.scratchpad_id


async def test_priorities_must_match_items(user_id):
    with pytest.raises(HTTPException) as exc:
        await create(user_id, ["a", "b"], [1])
    assert exc.value.status_code == 400


async def test_next_orders_by_priority_then_row_id(user_id):
    created = await create(user_id, ["p0-a", "p5-a", "p0-b", "p5-b", "p9"], [0, 5, 0, 5, 9])
    result = await next_rows(user_id, created.scratchpad_id, n=4)
    assert [r.text for r in result.rows] == ["p9", "p5-a", "p5-b", "p0-a"]
    assert all(r.status == "processing" and r.attempt_count == 1 for r in result.rows)
    assert result.metrics.processing == 4 and result.metrics.pending == 1


async def test_next_caps_batch_and_truncates_text(user_id):
    long = "x" * (MAX_ROW_CHARS_RETURNED + 123)
    created = await create(user_id, [long] + [f"row {i}" for i in range(MAX_BATCH_SIZE + 5)])
    result = await next_rows(user_id, created.scratchpad_id, n=500)
    assert len(result.rows) == MAX_BATCH_SIZE
    first = result.rows[0].text
    assert first.startswith("x" * MAX_ROW_CHARS_RETURNED)
    assert "123 more characters truncated" in first


async def test_next_distinguishes_still_processing_from_all_processed(user_id):
    created = await create(user_id, ["a", "b"])
    pad = created.scratchpad_id
    await next_rows(user_id, pad, n=2)

    waiting = await next_rows(user_id, pad)
    assert waiting.rows == []
    assert "still processing" in waiting.message
    assert "All items processed" not in waiting.message

    await set_status(
        user_id,
        pad,
        {"row_id": 1, "status": "done", "result": "ok"},
        {"row_id": 2, "status": "failed", "error_reason": "page 404"},
    )
    finished = await next_rows(user_id, pad)
    assert finished.rows == []
    assert finished.message == "All items processed: 1 done, 1 failed."


async def test_concurrent_next_never_returns_the_same_row(user_id):
    created = await create(user_id, [f"item {i}" for i in range(60)])
    results = await asyncio.gather(
        *(next_rows(user_id, created.scratchpad_id, n=7) for _ in range(12))
    )
    claimed = [r.row_id for res in results for r in res.rows]
    assert len(claimed) == len(set(claimed)) == 60


async def test_lock_is_per_scratchpad(user_id):
    a = await create(user_id, ["a1", "a2"])
    b = await create(user_id, ["b1"])

    async with unit_of_work() as db:
        await scratchpad_service.next(db, user_id, a.scratchpad_id, n=1)

        other = await asyncio.wait_for(next_rows(user_id, b.scratchpad_id), timeout=5)
        assert [r.text for r in other.rows] == ["b1"]

        same = asyncio.create_task(next_rows(user_id, a.scratchpad_id))
        await asyncio.sleep(0.5)
        assert not same.done()

    queued = await asyncio.wait_for(same, timeout=5)
    assert [r.text for r in queued.rows] == ["a2"]


async def test_status_transitions_apply_valid_and_report_invalid(user_id):
    created = await create(user_id, ["r1", "r2", "r3", "r4", "r5"])
    pad = created.scratchpad_id
    await claim(user_id, pad, [1, 2, 3, 4])

    result = await set_status(
        user_id,
        pad,
        {"row_id": 1, "status": "done", "result": "summary"},
        {"row_id": 2, "status": "failed", "error_reason": "timeout"},
        {"row_id": 3, "status": "pending"},
        {"row_id": 4, "status": "failed"},
        {"row_id": 5, "status": "done"},
        {"row_id": 5, "status": "processing"},
        {"row_id": 99, "status": "done"},
        {"row_id": 4, "status": "archived"},
    )
    outcomes = [(o.row_id, o.ok) for o in result.outcomes]
    assert outcomes == [
        (1, True),
        (2, True),
        (3, True),
        (4, False),
        (5, False),
        (5, False),
        (99, False),
        (4, False),
    ]
    errors = [o.error for o in result.outcomes if not o.ok]
    assert "error_reason" in errors[0]
    assert "pending, not claimed" in errors[1]
    assert "only by claiming" in errors[2]
    assert "does not exist" in errors[3]
    assert "unknown status" in errors[4]
    assert result.metrics.model_dump() == {
        "total": 5,
        "pending": 2,
        "processing": 1,
        "done": 1,
        "failed": 1,
    }

    rows = await statuses(pad)
    assert rows[1].result == "summary" and rows[1].error_reason is None
    assert rows[2].error_reason == "timeout"

    again = await set_status(
        user_id,
        pad,
        {"row_id": 1, "status": "pending"},
        {"row_id": 2, "status": "done"},
        {"row_id": 2, "status": "pending"},
    )
    assert [(o.row_id, o.ok) for o in again.outcomes] == [(1, False), (2, False), (2, True)]
    assert "already done" in again.outcomes[0].error
    assert "pending to retry" in again.outcomes[1].error
    rows = await statuses(pad)
    assert rows[2].status == "pending" and rows[2].error_reason is None


async def test_claim_rows_partial_and_never_returns_processing(user_id):
    created = await create(user_id, ["c1", "c2", "c3", "c4"])
    pad = created.scratchpad_id
    first = await claim(user_id, pad, [2])
    assert [r.text for r in first.rows] == ["c2"]
    await claim(user_id, pad, [3])
    await set_status(user_id, pad, {"row_id": 3, "status": "done"})

    result = await claim(user_id, pad, [1, 2, 3, 42, 1])
    assert [r.row_id for r in result.rows] == [1]
    reasons = {u.row_id: u.reason for u in result.not_claimed}
    assert set(reasons) == {2, 3, 42}
    assert "being processed" in reasons[2]
    assert reasons[3] == "already done"
    assert reasons[42] == "not found"
    dumped = result.model_dump_json()
    assert "c2" not in dumped


async def test_search_is_read_only_and_hides_processing(user_id):
    created = await create(
        user_id, ["Apple pie", "apple tart", "banana", "APPLE_100%"], [0, 1, 0, 0]
    )
    pad = created.scratchpad_id
    await claim(user_id, pad, [1])

    async with unit_of_work() as db:
        found = await scratchpad_service.search(db, user_id, pad, "apple")
    assert [r.text for r in found.rows] == ["apple tart", "APPLE_100%"]
    assert found.total == 2
    assert found.metrics.processing == 1

    async with unit_of_work() as db:
        literal = await scratchpad_service.search(db, user_id, pad, "_100%")
        assert [r.text for r in literal.rows] == ["APPLE_100%"]
        with pytest.raises(HTTPException) as exc:
            await scratchpad_service.search(db, user_id, pad, "apple", status="processing")
        assert exc.value.status_code == 400
        none_done = await scratchpad_service.search(db, user_id, pad, "apple", status="done")
        assert none_done.rows == [] and none_done.total == 0

    rows = await statuses(pad)
    assert rows[2].status == "pending" and rows[2].attempt_count == 0


async def test_get_failed_lists_reasons(user_id):
    created = await create(user_id, ["f1", "f2", "f3"])
    pad = created.scratchpad_id
    await next_rows(user_id, pad, n=3)
    await set_status(
        user_id,
        pad,
        {"row_id": 1, "status": "failed", "error_reason": "bad url"},
        {"row_id": 3, "status": "failed", "error_reason": "blocked"},
    )
    async with unit_of_work() as db:
        failed = await scratchpad_service.get_failed(db, user_id, pad, offset=1, limit=5)
    assert failed.total == 2
    assert [(r.row_id, r.error_reason, r.attempt_count) for r in failed.rows] == [(3, "blocked", 1)]


async def test_cleanup_requeues_fails_and_expires(user_id):
    created = await create(user_id, ["s1", "s2", "s3"])
    pad = created.scratchpad_id
    await next_rows(user_id, pad, n=3)
    stale = datetime.now(UTC) - timedelta(minutes=STUCK_AFTER_MINUTES + 1)
    async with unit_of_work() as db:
        await db.execute(
            update(ScratchpadRow)
            .where(ScratchpadRow.scratchpad_id == pad, ScratchpadRow.row_id.in_([1, 2]))
            .values(status_updated_at=stale)
        )
        await db.execute(
            update(ScratchpadRow)
            .where(ScratchpadRow.scratchpad_id == pad, ScratchpadRow.row_id == 2)
            .values(attempt_count=MAX_ATTEMPTS)
        )

    expired = await create(user_id, ["old"])
    async with unit_of_work() as db:
        await db.execute(
            update(Scratchpad)
            .where(Scratchpad.id == expired.scratchpad_id)
            .values(updated_at=datetime.now(UTC) - timedelta(hours=TTL_HOURS + 1))
        )

    async with unit_of_work() as db:
        result = await scratchpad_service.cleanup(db)
    assert result.reset >= 1 and result.failed >= 1 and result.deleted >= 1

    rows = await statuses(pad)
    assert rows[1].status == "pending"
    assert rows[2].status == "failed"
    assert rows[2].error_reason == f"timed out after {MAX_ATTEMPTS} attempts"
    assert rows[3].status == "processing"

    async with unit_of_work() as db:
        with pytest.raises(HTTPException) as exc:
            await scratchpad_service.get_scratchpad(db, user_id, expired.scratchpad_id)
    assert exc.value.status_code == 404
    assert "may have expired" in exc.value.detail
    assert await statuses(expired.scratchpad_id) == {}


async def test_delete_needs_force_while_rows_are_unfinished(user_id):
    created = await create(user_id, ["d1", "d2"])
    pad = created.scratchpad_id
    async with unit_of_work() as db:
        with pytest.raises(HTTPException) as exc:
            await scratchpad_service.delete_scratchpad(db, user_id, pad)
    assert exc.value.status_code == 409
    assert "Set force=true only if you are sure" in exc.value.detail
    assert "2 pending" in exc.value.detail

    done = await create(user_id, ["e1"])
    await next_rows(user_id, done.scratchpad_id)
    await set_status(user_id, done.scratchpad_id, {"row_id": 1, "status": "done"})
    async with unit_of_work() as db:
        await scratchpad_service.delete_scratchpad(db, user_id, done.scratchpad_id)
        await scratchpad_service.delete_scratchpad(db, user_id, pad, force=True)
    assert await statuses(pad) == {}
    assert await statuses(done.scratchpad_id) == {}


async def test_scratchpads_are_private_to_their_owner(client, user_id):
    created = await create(user_id, ["mine"])
    async with unit_of_work() as db:
        with pytest.raises(HTTPException) as exc:
            await scratchpad_service.next(db, "someone_else", created.scratchpad_id)
    assert exc.value.status_code == 404


def test_what_is_scratchpad_explains_the_workflow():
    text = tools.what_is_scratchpad()
    assert "work queue" in text
    for name in ("scratchpad_next", "scratchpad_update_status", "scratchpad_delete"):
        assert name in text


def test_needs_scratchpad_thresholds():
    assert not needs_scratchpad(["a"] * ROW_COUNT_THRESHOLD)
    assert needs_scratchpad(["a"] * (ROW_COUNT_THRESHOLD + 1))
    assert not needs_scratchpad(["x" * CHAR_THRESHOLD])
    assert needs_scratchpad(["x" * CHAR_THRESHOLD, "y"])


async def test_rest_api_round_trip(client, user_id):
    r = await client.post(
        BASE, json={"toolName": "crawl", "items": ["u1", "u2", "u1"], "priorities": [0, 2, 0]}
    )
    assert r.status_code == 201, r.text
    created = r.json()["data"]
    assert created["totalRows"] == 2 and created["duplicatesSkipped"] == 1
    pad = created["scratchpadId"]

    r = await client.post(f"{BASE}/{pad}/next", json={"n": 1})
    assert r.status_code == 200, r.text
    assert [row["text"] for row in r.json()["data"]["rows"]] == ["u2"]

    r = await client.post(
        f"{BASE}/{pad}/status", json={"updates": [{"rowId": 2, "status": "done"}]}
    )
    assert r.json()["data"]["outcomes"] == [{"rowId": 2, "ok": True, "status": "done"}]

    r = await client.get(f"{BASE}/{pad}")
    info = r.json()["data"]
    assert info["toolName"] == "crawl"
    assert info["metrics"] == {"total": 2, "pending": 1, "processing": 0, "done": 1, "failed": 0}

    r = await client.get(f"{BASE}/{pad}/search", params={"q": "U1"})
    assert r.json()["data"]["total"] == 1

    r = await client.delete(f"{BASE}/{pad}")
    assert r.status_code == 409

    r = await client.delete(f"{BASE}/{pad}", params={"force": "true"})
    assert r.status_code == 200
    r = await client.get(f"{BASE}/{pad}/metrics")
    assert r.status_code == 404


async def test_tools_scope_to_the_agent_user(user_id):
    async with unit_of_work() as db:
        spilled = await scratchpad_service.spill(db, user_id, "keywords", ["k1", "k2"])
    assert "scratchpad_next" in spilled.guidance
    token = set_context(
        AgentContext(
            user_id=user_id,
            site_id=None,
            site_domain=None,
            site_status=None,
            role="r",
            schema="s",
            api_key="k",
        )
    )
    try:
        batch = await tools.scratchpad_next(spilled.scratchpad_id, n=5)
        assert [r.text for r in batch.rows] == ["k1", "k2"]
        updated = await tools.scratchpad_update_status(
            spilled.scratchpad_id,
            [RowStatusUpdate(row_id=1, status="done"), RowStatusUpdate(row_id=2, status="done")],
        )
        assert updated.metrics.done == 2
        deleted = await tools.scratchpad_delete(spilled.scratchpad_id)
        assert deleted.deleted
        with pytest.raises(HTTPException) as exc:
            await tools.scratchpad_info(spilled.scratchpad_id)
        assert "Re-run the tool that created it" in exc.value.detail
    finally:
        reset_context(token)
