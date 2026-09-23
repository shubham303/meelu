from __future__ import annotations

import heapq
from bisect import bisect_left, bisect_right
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from statistics import fmean

CAPACITY_BASE_LINKS = 3
CAPACITY_WORDS_PER_LINK = 300
CAPACITY_MAX_LINKS = 15
UNLIMITED_CAPACITY = 10**9
REMOVAL_BUDGET_FRACTION = 0.3
MIN_TARGET_INLINKS = 2

TARGET_INTENT = {
    "money": 0.7,
    "hub": 0.6,
    "informational": 0.4,
    "support": 0.3,
    "company": 0.2,
    "legal": 0.1,
    "utility": 0.1,
}
INFORMATIONAL_TO_MONEY_INTENT = 1.0
UNKNOWN_TYPE_INTENT = 0.3


@dataclass(frozen=True)
class PageFacts:
    page_id: str
    inlinks: int
    outlinks: int
    word_count: int | None = None
    page_type: str | None = None
    existing_suggestions: int = 0
    kind: str | None = None


@dataclass(frozen=True)
class Candidate:
    suggestion_id: str
    from_page_id: str
    to_page_id: str
    search_score: float
    confidence: float | None = None
    action: str = "create"


@dataclass(frozen=True)
class RankParams:
    max_per_target: int | None = None
    target_discount: float = 1.0
    confidence_floor: float = 0.5


DEFAULT_PARAMS = RankParams()


@dataclass(frozen=True)
class Ranked:
    candidate: Candidate
    score: float
    kept: bool
    factors: dict[str, float] = field(default_factory=dict)


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
    return page.kind == "home" or page.page_type == "hub"


def link_capacity(page: PageFacts) -> int:
    if links_out_freely(page):
        return UNLIMITED_CAPACITY
    words = page.word_count or 0
    capacity = CAPACITY_BASE_LINKS + words // CAPACITY_WORDS_PER_LINK
    return min(capacity, CAPACITY_MAX_LINKS)


def percentile(sorted_values: Sequence[int], value: int) -> float:
    n = len(sorted_values)
    if n == 0:
        return 0.5
    lo = bisect_left(sorted_values, value)
    hi = bisect_right(sorted_values, value)
    return (lo + hi) / (2 * n)


def _clamp(value: float) -> float:
    return min(1.0, max(0.0, value))


def intent(from_type: str | None, to_type: str | None) -> float:
    if from_type == "informational" and to_type == "money":
        return INFORMATIONAL_TO_MONEY_INTENT
    if to_type is None:
        return UNKNOWN_TYPE_INTENT
    return TARGET_INTENT.get(to_type, UNKNOWN_TYPE_INTENT)


def score_candidates(
    candidates: Sequence[Candidate],
    pages: dict[str, PageFacts],
    site: SiteDistribution,
    params: RankParams = DEFAULT_PARAMS,
) -> list[Ranked]:
    ranked: list[Ranked] = []
    for c in candidates:
        source = pages[c.from_page_id]
        target = pages[c.to_page_id]
        factors = {
            "relevance": _clamp(c.search_score),
            "need": 1.0 - percentile(site.inlinks, target.inlinks),
            "source_authority": percentile(site.inlinks, source.inlinks),
            "flow": percentile(site.outlinks, target.outlinks),
            "intent": intent(source.page_type, target.page_type),
        }
        structural = fmean(v for k, v in factors.items() if k != "relevance")
        score = factors["relevance"] * structural
        if c.confidence is not None:
            score *= params.confidence_floor + (1.0 - params.confidence_floor) * c.confidence
        ranked.append(Ranked(candidate=c, score=score, kept=False, factors=factors))
    return ranked


def select_within_budget(
    scored: Sequence[Ranked],
    pages: dict[str, PageFacts],
    params: RankParams = DEFAULT_PARAMS,
) -> list[Ranked]:
    remaining: dict[str, int] = {}
    for r in scored:
        source = pages[r.candidate.from_page_id]
        remaining.setdefault(source.page_id, link_capacity(source) - source.existing_suggestions)
    accepted_to: dict[str, int] = defaultdict(int)

    def effective(r: Ranked) -> float:
        n = accepted_to[r.candidate.to_page_id]
        return r.score / (1.0 + n) ** params.target_discount

    heap: list[tuple[float, int, int]] = [(-r.score, i, 0) for i, r in enumerate(scored)]
    heapq.heapify(heap)
    kept: set[int] = set()

    while heap:
        _, i, seen_n = heapq.heappop(heap)
        r = scored[i]
        n = accepted_to[r.candidate.to_page_id]
        if n != seen_n:
            heapq.heappush(heap, (-effective(r), i, n))
            continue
        if remaining[r.candidate.from_page_id] <= 0:
            continue
        if params.max_per_target is not None and n >= params.max_per_target:
            continue
        remaining[r.candidate.from_page_id] -= 1
        accepted_to[r.candidate.to_page_id] += 1
        kept.add(i)

    return [
        Ranked(candidate=r.candidate, score=r.score, kept=i in kept, factors=r.factors)
        for i, r in enumerate(scored)
    ]


def rank_link_suggestions(
    candidates: Sequence[Candidate],
    pages: dict[str, PageFacts],
    site: SiteDistribution,
    params: RankParams = DEFAULT_PARAMS,
) -> list[Ranked]:
    scored = score_candidates(candidates, pages, site, params)
    return select_within_budget(scored, pages, params)


def score_removals(
    candidates: Sequence[Candidate],
    pages: dict[str, PageFacts],
    params: RankParams = DEFAULT_PARAMS,
) -> list[Ranked]:
    ranked: list[Ranked] = []
    for c in candidates:
        source = pages[c.from_page_id]
        target = pages[c.to_page_id]
        capacity = link_capacity(source)
        factors = {
            "irrelevance": _clamp(1.0 - c.search_score),
            "pressure": 0.0
            if capacity >= UNLIMITED_CAPACITY
            else _clamp(source.outlinks / capacity),
            "mismatch": 1.0 - intent(source.page_type, target.page_type),
        }
        structural = fmean(v for k, v in factors.items() if k != "irrelevance")
        score = factors["irrelevance"] * structural
        if c.confidence is not None:
            score *= params.confidence_floor + (1.0 - params.confidence_floor) * c.confidence
        ranked.append(Ranked(candidate=c, score=score, kept=False, factors=factors))
    return ranked


def select_removals(scored: Sequence[Ranked], pages: dict[str, PageFacts]) -> list[Ranked]:
    source_left: dict[str, int] = {}
    target_left: dict[str, int] = {}
    for r in scored:
        source = pages[r.candidate.from_page_id]
        target = pages[r.candidate.to_page_id]
        source_left.setdefault(
            source.page_id, max(1, int(source.outlinks * REMOVAL_BUDGET_FRACTION))
        )
        target_left.setdefault(target.page_id, target.inlinks - MIN_TARGET_INLINKS)
    kept: set[int] = set()
    for i in sorted(range(len(scored)), key=lambda i: -scored[i].score):
        c = scored[i].candidate
        if source_left[c.from_page_id] <= 0 or target_left[c.to_page_id] <= 0:
            continue
        source_left[c.from_page_id] -= 1
        target_left[c.to_page_id] -= 1
        kept.add(i)
    return [
        Ranked(candidate=r.candidate, score=r.score, kept=i in kept, factors=r.factors)
        for i, r in enumerate(scored)
    ]


def rank_link_removals(
    candidates: Sequence[Candidate],
    pages: dict[str, PageFacts],
    params: RankParams = DEFAULT_PARAMS,
) -> list[Ranked]:
    return select_removals(score_removals(candidates, pages, params), pages)
