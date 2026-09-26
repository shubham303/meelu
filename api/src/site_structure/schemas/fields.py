import re
from typing import Any

from src.site_structure.constants import (
    JOB_STATUSES,
    LINK_ACTIONS,
    PILLAR_ACTIONS,
    SORT_ORDERS,
    SUGGESTION_SORTS,
    SUGGESTION_STATES,
    WORKSPACE_TABLE,
)

MAX_SUGGESTION_CHARS = 4_000

MAX_PROMPT_CHARS = 20_000


def blank(value: Any) -> bool:
    return value is None or value == ""


def _choice(value: Any, allowed: tuple[str, ...], label: str) -> str:
    chosen = str(value)
    if chosen not in allowed:
        raise ValueError(f'Invalid {label} "{chosen}". Allowed values: {", ".join(allowed)}.')
    return chosen


def state(value: Any) -> str:
    return _choice(value, SUGGESTION_STATES, "state")


def action(value: Any) -> str:
    return _choice(value, LINK_ACTIONS, "action")


def status(value: Any) -> str:
    return _choice(str(value).upper(), JOB_STATUSES, "status")


def suggestion(value: Any) -> str:
    text = str(value if value is not None else "").strip()
    if not text:
        raise ValueError("A suggestion needs a description.")
    return text[:MAX_SUGGESTION_CHARS]


def prompt(value: Any) -> str:
    text = str(value if value is not None else "").strip()
    if not text:
        raise ValueError("A job needs the prompt it runs.")
    return text[:MAX_PROMPT_CHARS]


def pillar_action(value: Any) -> str:
    return _choice(value, PILLAR_ACTIONS, "action")


def sort_by(value: Any) -> str:
    return _choice(value, SUGGESTION_SORTS, "sortBy")


def sort_order(value: Any) -> str:
    return _choice(str(value).lower(), SORT_ORDERS, "sortOrder")


def workspace_table(value: Any) -> str:
    name = str(value if value is not None else "").strip()
    if not re.match(WORKSPACE_TABLE, name):
        raise ValueError("Name a workspace table: lowercase letters, digits and underscores.")
    return name
