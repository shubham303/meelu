import hashlib
import re
from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentContext:
    user_id: str
    site_id: str | None
    site_domain: str | None
    site_status: str | None
    role: str
    schema: str
    api_key: str


_current: ContextVar[AgentContext | None] = ContextVar("meelu_agent_context", default=None)


def tenant_names(user_id: str) -> tuple[str, str]:
    base = re.sub(r"[^a-z0-9]", "", user_id.lower())[:20]
    suffix = hashlib.sha256(user_id.encode()).hexdigest()[:8]
    return f"agent_{base}_{suffix}", f"ws_{base}_{suffix}"


def set_context(ctx: AgentContext):
    return _current.set(ctx)


def reset_context(token) -> None:
    _current.reset(token)


def current() -> AgentContext:
    ctx = _current.get()
    if ctx is None:
        raise RuntimeError("No authenticated agent context on this request.")
    return ctx


def require_site() -> AgentContext:
    ctx = current()
    if not ctx.site_id:
        raise ValueError(
            "No website selected. Pass the x-meelu-site header (the workspace has "
            "more than one site)."
        )
    if ctx.site_status != "active":
        raise ValueError(
            f"{ctx.site_domain} is paused because the workspace ran out of credits. "
            "Tell the user to add credits: the website turns back on as soon as they cover "
            "a day, and a website paused for 30 days is deleted."
        )
    return ctx


def optional_current() -> AgentContext | None:
    return _current.get()
