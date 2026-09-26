from enum import StrEnum
from typing import Any, TypeVar

from src.site_structure.constants import VISIBLE_STATES, SuggestionState

E = TypeVar("E", bound=StrEnum)


def blank(value: Any) -> bool:
    return value is None or value == ""


def choice(enum: type[E], value: Any, label: str) -> E:
    chosen = str(value)
    try:
        return enum(chosen)
    except ValueError:
        allowed = ", ".join(member.value for member in enum)
        raise ValueError(f'Invalid {label} "{chosen}". Allowed values: {allowed}.') from None


def states(values: list[str] | None) -> frozenset[SuggestionState] | None:
    if not values:
        return VISIBLE_STATES
    if "any" in values:
        return None
    return frozenset(choice(SuggestionState, value, "state") for value in values)
