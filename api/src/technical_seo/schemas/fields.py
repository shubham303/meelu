from typing import Any

from src.technical_seo.constants import (
    SITE_ISSUE_KINDS,
    SITE_ISSUE_SEVERITIES,
    SITE_ISSUE_STATES,
    SITE_ISSUE_TYPES,
)

MAX_ISSUE_CHARS = 2_000

MAX_REASON_CHARS = 2_000

MAX_TRIGGER_CHARS = 40


def blank(value: Any) -> bool:
    return value is None or value == ""


def state(value: Any) -> str:
    chosen = str(value)
    if chosen not in SITE_ISSUE_STATES:
        raise ValueError(
            f'Invalid state "{chosen}". Allowed values: {", ".join(SITE_ISSUE_STATES)}.'
        )
    return chosen


def severity(value: Any) -> str:
    chosen = str(value)
    if chosen not in SITE_ISSUE_SEVERITIES:
        raise ValueError(
            f'Invalid severity "{chosen}". Allowed values: {", ".join(SITE_ISSUE_SEVERITIES)}.'
        )
    return chosen


def issue_type(value: Any) -> str:
    chosen = str(value)
    if chosen not in SITE_ISSUE_TYPES:
        raise ValueError(f'Invalid type "{chosen}". Allowed values: {", ".join(SITE_ISSUE_TYPES)}.')
    return chosen


def kind(value: Any) -> str:
    chosen = str(value if value is not None else "").strip()
    if chosen not in SITE_ISSUE_KINDS:
        raise ValueError(
            f'Unknown issue kind "{chosen}". Allowed values: {", ".join(SITE_ISSUE_KINDS)}.'
        )
    return chosen


def kinds(value: Any) -> list[str] | None:
    if value is None:
        return None
    parts: list[str] = []
    for part in value if isinstance(value, list) else [value]:
        parts.extend(str(part).split(","))
    chosen = [kind(p) for p in (part.strip() for part in parts) if p]
    return chosen or None


def issue_text(value: Any) -> str:
    text = str(value if value is not None else "").strip()
    if not text:
        raise ValueError("An issue needs a wording.")
    return text[:MAX_ISSUE_CHARS]


def reason(value: Any) -> str | None:
    text = str(value if value is not None else "").strip()
    return text[:MAX_REASON_CHARS] if text else None


def trigger(value: Any) -> str:
    text = str(value if value is not None else "user").strip()
    return text[:MAX_TRIGGER_CHARS] if text else "user"


def matched_pages(value: Any) -> int:
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        return 1
    return n or 1
