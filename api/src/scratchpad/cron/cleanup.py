from src.core.database import unit_of_work
from src.core.logging import get_logger
from src.scratchpad.service import scratchpad_service

log = get_logger()


async def cleanup() -> None:
    try:
        async with unit_of_work() as db:
            result = await scratchpad_service.cleanup(db)
    except Exception as exc:
        log.error("scratchpad.cron.cleanup_failed", error=str(exc))
        return
    log.info("scratchpad.cron.cleaned", **result.model_dump())
