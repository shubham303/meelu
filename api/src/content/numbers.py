import math
from typing import Any


def number_or_null(value: Any) -> int | None:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(n) or n <= 0:
        return None
    return math.floor(n + 0.5)
