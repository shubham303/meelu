from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from src.providers.apify import ChargeEvents
from src.providers.social_search.shape import epoch_seconds


@dataclass(frozen=True)
class SearchQuery:
    keywords: list[str]
    since: str | None
    limit: int

    def age_days(self) -> float | None:
        start = epoch_seconds(self.since)
        if start is None:
            return None
        return max(datetime.now(UTC).timestamp() - start, 0) / 86400


@dataclass(frozen=True)
class ActorSpec:
    platform: str
    actor_id: str
    build_input: Callable[[SearchQuery], dict[str, Any]]
    normalize: Callable[[dict[str, Any]], dict | None]
    charges: ChargeEvents = ChargeEvents()


def window(query: SearchQuery, steps: list[tuple[float, str]], beyond: str) -> str:
    age = query.age_days()
    if age is None:
        return beyond
    return next((label for days, label in steps if age <= days), beyond)
