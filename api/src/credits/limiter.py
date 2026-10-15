import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from src.settings import settings


class PaidCallsBusyError(Exception):
    code = "paid_calls_busy"

    def __init__(self) -> None:
        super().__init__(
            f"{settings.credits_parallel_calls_per_user} paid calls are already running for "
            "this workspace and none finished in time. Try again in a minute."
        )


@dataclass
class _UserSlots:
    semaphore: asyncio.Semaphore
    users: int = field(default=0)


class PaidCallLimiter:
    def __init__(self) -> None:
        self._slots: dict[str, _UserSlots] = {}

    async def acquire(self, user_id: str) -> None:
        slots = self._slots.get(user_id)
        if slots is None:
            slots = _UserSlots(asyncio.Semaphore(settings.credits_parallel_calls_per_user))
            self._slots[user_id] = slots
        slots.users += 1
        try:
            async with asyncio.timeout(settings.credits_slot_wait_seconds):
                await slots.semaphore.acquire()
        except TimeoutError:
            self._leave(user_id, slots)
            raise PaidCallsBusyError() from None
        except BaseException:
            self._leave(user_id, slots)
            raise

    def release(self, user_id: str) -> None:
        slots = self._slots[user_id]
        slots.semaphore.release()
        self._leave(user_id, slots)

    def _leave(self, user_id: str, slots: _UserSlots) -> None:
        slots.users -= 1
        if slots.users == 0:
            del self._slots[user_id]

    @asynccontextmanager
    async def slot(self, user_id: str) -> AsyncIterator[None]:
        await self.acquire(user_id)
        try:
            yield
        finally:
            self.release(user_id)


paid_calls = PaidCallLimiter()
