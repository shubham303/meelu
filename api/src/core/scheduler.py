import asyncio
import contextlib

from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()


@contextlib.asynccontextmanager
async def running():
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)
        await asyncio.sleep(0)
