import asyncio
import contextlib

from src.core.logging import get_logger
from src.credits import billing
from src.settings import settings

log = get_logger("credits.cron")


async def _loop() -> None:
    while True:
        try:
            result = await billing.sweep()
            if result.considered:
                log.info("site_billing_sweep", **result.model_dump())
        except Exception as exc:
            log.error("site_billing_sweep_failed", error=str(exc))
        await asyncio.sleep(settings.credits_billing_sweep_seconds)


@contextlib.asynccontextmanager
async def running():
    if settings.credits_billing_sweep_disabled:
        yield
        return
    task = asyncio.create_task(_loop())
    try:
        yield
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
