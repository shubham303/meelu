import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from src.core.database import unit_of_work
from src.core.logging import get_logger
from src.find_leads.repositories.runs import lead_runs

log = get_logger("find_leads.jobs")

HEARTBEAT_SECONDS = 20
SILENT_AFTER_SECONDS = 90
SILENT_ERROR = "The search stopped reporting, most likely because the server restarted. Run again."

JobResult = tuple[dict[str, Any], int]


def running_stats(earlier: int = 0) -> dict[str, Any]:
    return {
        "status": "running",
        "heartbeatAt": datetime.now(UTC).isoformat(),
        "candidates": earlier,
    }


def is_silent(stats: dict[str, Any], now: datetime) -> bool:
    if stats.get("status") != "running":
        return False
    beat = stats.get("heartbeatAt")
    try:
        last = datetime.fromisoformat(beat) if beat else None
    except ValueError:
        last = None
    return last is None or now - last > timedelta(seconds=SILENT_AFTER_SECONDS)


async def _heartbeat(run_id: str, key: str, earlier: int) -> None:
    while True:
        await asyncio.sleep(HEARTBEAT_SECONDS)
        try:
            async with unit_of_work() as db:
                await lead_runs.merge_source_stats(db, run_id, key, running_stats(earlier))
        except Exception as exc:
            log.warning("find_leads_heartbeat_failed", run_id=run_id, key=key, error=str(exc))


async def run_job(
    run_id: str, key: str, work: Callable[[], Awaitable[JobResult]], earlier: int = 0
) -> None:
    stats: dict[str, Any] = {"status": "error"}
    found = 0
    beat = asyncio.create_task(_heartbeat(run_id, key, earlier))
    try:
        stats, found = await work()
    except Exception as exc:
        log.error("find_leads_job_failed", run_id=run_id, key=key, error=str(exc))
        stats = {"status": "error", "error": str(exc)}
    finally:
        beat.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await beat
    stats = {**stats, "candidates": int(stats.get("candidates") or 0) + earlier}
    async with unit_of_work() as db:
        await lead_runs.merge_source_stats(db, run_id, key, stats, found=found)
