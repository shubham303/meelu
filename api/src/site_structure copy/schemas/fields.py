from enum import StrEnum
from typing import Any, TypeVar

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
