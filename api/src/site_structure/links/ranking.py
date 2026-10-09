from __future__ import annotations

import heapq
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from statistics import fmean

from src.site_structure.links.schemas import LinkAction
from src.site_structure.pipeline.ranking import (
    UNLIMITED_CAPACITY,
    PageFacts,
    SiteDistribution,
    clamp,
    link_capacity,
    link_room,
    percentile,
)

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
class Candidate:
    suggestion_id: str
    from_page_id: str
    to_page_id: str
    action: LinkAction
    search_score: float | None
    confidence: float | None


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


def intent(from_type: str | None, to_type: str | None) -> float:
    if from_type == "informational" and to_type == "money":
        return INFORMATIONAL_TO_MONEY_INTENT
    if to_type is None:
        return UNKNOWN_TYPE_INTENT
    return TARGET_INTENT.get(to_type, UNKNOWN_TYPE_INTENT)


def _score(
    fit: float | None, structural: float, confidence: float | None, params: RankParams
) -> float:
    base = structural if fit is None else clamp(fit) * structural
    return base * (params.confidence_floor + (1.0 - params.confidence_floor) * (confidence or 0.0))


def score_additions(
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
            "need": 1.0 - percentile(site.inlinks, target.inlinks),
            "source_authority": percentile(site.inlinks, source.inlinks),
            "flow": percentile(site.outlinks, target.outlinks),
            "intent": intent(source.page_type, target.page_type),
        }
        score = _score(c.search_score, fmean(factors.values()), c.confidence, params)
        ranked.append(Ranked(candidate=c, score=score, kept=False, factors=factors))
    return ranked


def select_additions(
    scored: Sequence[Ranked],
    pages: dict[str, PageFacts],
    params: RankParams = DEFAULT_PARAMS,
) -> list[Ranked]:
    remaining = {
        r.candidate.from_page_id: link_room(pages[r.candidate.from_page_id]) for r in scored
    }
    accepted_to: dict[str, int] = defaultdict(int)

    def effective(r: Ranked) -> float:
        return r.score / (1.0 + accepted_to[r.candidate.to_page_id]) ** params.target_discount

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
            "pressure": 0.0
            if capacity >= UNLIMITED_CAPACITY
            else clamp(source.outlinks / capacity),
            "mismatch": 1.0 - intent(source.page_type, target.page_type),
        }
        score = _score(c.search_score, fmean(factors.values()), c.confidence, params)
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


def rank(
    candidates: Sequence[Candidate],
    pages: dict[str, PageFacts],
    site: SiteDistribution,
    params: RankParams = DEFAULT_PARAMS,
) -> list[Ranked]:
    usable = [c for c in candidates if c.from_page_id in pages and c.to_page_id in pages]
    additions = [c for c in usable if c.action is LinkAction.CREATE]
    removals = [c for c in usable if c.action is LinkAction.DELETE]
    return select_additions(score_additions(additions, pages, site, params), pages, params) + (
        select_removals(score_removals(removals, pages, params), pages)
    )
