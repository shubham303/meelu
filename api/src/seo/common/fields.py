import re
from typing import Any

from src.seo.constants import (
    ACTIONS,
    COMPETITOR_STATES,
    JOB_STATUSES,
    MAX_BRAND_TERMS,
    SUGGESTION_STATES,
    WORKSPACE_TABLE,
)

MAX_SUGGESTION_CHARS = 4_000

MAX_PROMPT_CHARS = 20_000

MAX_KEYWORD_CHARS = 200


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
    return _choice(value, ACTIONS, "action")


def status(value: Any) -> str:
    return _choice(str(value).upper(), JOB_STATUSES, "status")


def competitor_state(value: Any) -> str:
    return _choice(value, COMPETITOR_STATES, "state")


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


def keyword(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value if value is not None else "").strip().lower())[
        :MAX_KEYWORD_CHARS
    ]


def keywords(values: Any) -> list[str]:
    seen: dict[str, None] = {}
    for raw in values or []:
        cleaned = keyword(raw)
        if cleaned:
            seen[cleaned] = None
    return list(seen)


def brand_terms(values: Any) -> list[str]:
    return keywords(values)[:MAX_BRAND_TERMS]


def workspace_table(value: Any) -> str:
    name = str(value if value is not None else "").strip()
    if not re.match(WORKSPACE_TABLE, name):
        raise ValueError("A workspace table name is lowercase letters, digits and underscores.")
    return name
