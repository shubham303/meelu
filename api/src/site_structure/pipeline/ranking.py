from __future__ import annotations

import re
from bisect import bisect_left, bisect_right
from collections.abc import Sequence
from dataclasses import dataclass

CAPACITY_BASE_LINKS = 3
CAPACITY_WORDS_PER_LINK = 300
CAPACITY_MAX_LINKS = 15
UNLIMITED_CAPACITY = 10**9

HOST_PREFIX = re.compile(r"^[a-z]+://[^/]+")


def is_home(url: str) -> bool:
    return HOST_PREFIX.sub("", url, count=1) in ("", "/")


@dataclass(frozen=True)
class PageFacts:
    page_id: str
    inlinks: int
    outlinks: int
    word_count: int | None = None
    page_type: str | None = None
    is_home: bool = False


@dataclass(frozen=True)
class SiteDistribution:
    inlinks: Sequence[int]
    outlinks: Sequence[int]

    @classmethod
    def from_pages(cls, pages: Sequence[PageFacts]) -> SiteDistribution:
        return cls(
            inlinks=sorted(p.inlinks for p in pages),
            outlinks=sorted(p.outlinks for p in pages),
        )


def links_out_freely(page: PageFacts) -> bool:
    return page.is_home or page.page_type == "hub"


def link_capacity(page: PageFacts) -> int:
    if links_out_freely(page):
        return UNLIMITED_CAPACITY
    words = page.word_count or 0
    return min(CAPACITY_BASE_LINKS + words // CAPACITY_WORDS_PER_LINK, CAPACITY_MAX_LINKS)


def percentile(sorted_values: Sequence[int], value: int) -> float:
    n = len(sorted_values)
    if n == 0:
        return 0.5
    lo = bisect_left(sorted_values, value)
    hi = bisect_right(sorted_values, value)
    return (lo + hi) / (2 * n)


def clamp(value: float) -> float:
    return min(1.0, max(0.0, value))
