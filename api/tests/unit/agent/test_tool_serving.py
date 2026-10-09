import asyncio
import threading
import time

from src.agent import server
from src.agent.context import AgentContext, reset_context, set_context
from src.settings import settings


def context(user_id: str) -> AgentContext:
    return AgentContext(
        user_id=user_id,
        site_id=None,
        site_domain=None,
        site_status=None,
        role="r",
        schema="s",
        api_key="",
    )


async def test_sync_tools_run_off_the_event_loop():
    loop_thread = threading.get_ident()

    def probe(n: int) -> int:
        return threading.get_ident()

    served = server._served(probe)
    assert await served(n=1) != loop_thread
    assert served.__wrapped__ is probe


async def test_tool_calls_are_capped_per_user(monkeypatch):
    monkeypatch.setattr(settings, "agent_tool_concurrency", 2)
    running = 0
    peak = 0
    lock = threading.Lock()

    def slow() -> None:
        nonlocal running, peak
        with lock:
            running += 1
            peak = max(peak, running)
        time.sleep(0.05)
        with lock:
            running -= 1

    served = server._served(slow)
    token = set_context(context("user-cap"))
    try:
        await asyncio.gather(*(served() for _ in range(6)))
    finally:
        reset_context(token)
    assert peak == 2
