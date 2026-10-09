import asyncio
import contextlib
import functools
import inspect
import weakref
from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from src.agent.context import optional_current
from src.settings import settings

INSTRUCTIONS = """\
Meelu agent server: direct SQL over the user's data plus deterministic analytics.

Workflow:
1. The tables you can query, with their columns, arrive in your task prompt.
   Anything not listed there is discoverable with run_sql over
   information_schema.columns.
2. Before designing SQL for a non-trivial question, call find_plans — the plan
   library holds vetted step-by-step plans for common questions. If a question
   matches, get_plan and adapt it instead of inventing the approach.
3. Read anything with run_sql. Canonical tables are read-only and already
   filtered to this user; your workspace schema is fully writable — materialize
   filtered or joined tables there (CREATE TABLE ... AS SELECT ...) before
   running analytics on them.
4. Analytics tools take a table name and return {method, summary, trust,
   declined, values, metadata}. Trust the chosen method. When `declined` is
   true the data cannot support the question — report the reason, never
   substitute a number. Always convey the trust level and caveats.
5. Saving results the user should keep goes through the explicit write tools,
   never through workspace tables.
"""

mcp = FastMCP(
    "meelu-agent",
    instructions=INSTRUCTIONS,
    stateless_http=True,
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=settings.agent_allowed_hosts,
        allowed_origins=[],
    ),
)


ToolFn = Callable[..., Any]

READ_TOOLS: set[ToolFn] = set()
WRITE_TOOLS: set[ToolFn] = set()
TOOL_DESKS: dict[ToolFn, str] = {}
TOOL_PROVIDERS: dict[ToolFn, str] = {}

_user_slots: weakref.WeakValueDictionary[str, asyncio.Semaphore] = weakref.WeakValueDictionary()


def _slot_for_current_user() -> asyncio.Semaphore | None:
    ctx = optional_current()
    if ctx is None:
        return None
    slot = _user_slots.get(ctx.user_id)
    if slot is None:
        slot = asyncio.Semaphore(settings.agent_tool_concurrency)
        _user_slots[ctx.user_id] = slot
    return slot


def _served(fn: ToolFn) -> ToolFn:
    is_async = inspect.iscoroutinefunction(fn)

    @functools.wraps(fn)
    async def serve(*args: Any, **kwargs: Any) -> Any:
        async with _slot_for_current_user() or contextlib.nullcontext():
            if is_async:
                return await fn(*args, **kwargs)
            return await asyncio.to_thread(fn, *args, **kwargs)

    return serve


def tool(
    *, writes: bool = False, desk: str | None = None, provider: str | None = None
) -> Callable[[ToolFn], ToolFn]:
    def register(fn: ToolFn) -> ToolFn:
        meta = {
            "meelu/writes": writes,
            **({"meelu/desk": desk} if desk else {}),
            **({"meelu/provider": provider} if provider else {}),
        }
        mcp.tool(meta=meta)(_served(fn))
        (WRITE_TOOLS if writes else READ_TOOLS).add(fn)
        if desk is not None:
            TOOL_DESKS[fn] = desk
        if provider is not None:
            TOOL_PROVIDERS[fn] = provider
        return fn

    return register
