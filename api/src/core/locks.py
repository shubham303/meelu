from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import func, select

from src.core.database import engine


@asynccontextmanager
async def skip_if_locked(key: str) -> AsyncIterator[bool]:
    lock_id = func.hashtextextended(key, 0)
    async with engine.connect() as conn:
        held = bool(await conn.scalar(select(func.pg_try_advisory_lock(lock_id))))
        try:
            yield held
        finally:
            if held:
                await conn.scalar(select(func.pg_advisory_unlock(lock_id)))
