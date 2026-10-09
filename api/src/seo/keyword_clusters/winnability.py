import math

from src.seo.keyword_clusters.constants import MARGIN, PAGE_WEIGHT, SCALE, TOP_N


def strength(page_rank: float | None, domain_rank: float | None) -> float:
    return PAGE_WEIGHT * (page_rank or 0) + (1 - PAGE_WEIGHT) * (domain_rank or 0)


def smoothed(strengths: list[float]) -> list[float]:
    blocks: list[list[float]] = []
    for value in strengths:
        blocks.append([value])
        while len(blocks) > 1 and _mean(blocks[-2]) < _mean(blocks[-1]):
            last = blocks.pop()
            blocks[-1].extend(last)
    return [_mean(block) for block in blocks for _ in block]


def authority_pass(theirs: float, ours: float) -> float:
    return 1 / (1 + math.exp((theirs - ours - MARGIN) / SCALE))


def pass_chance(theirs: float, ours: float, fit: float) -> float:
    return 1 - fit * (1 - authority_pass(theirs, ours))


def climb(passes: list[float], start: int) -> dict[str, float | int]:
    reach = {start: 1.0}
    for position in range(start - 1, 0, -1):
        reach[position] = passes[position - 1] * reach[position + 1]
    p_top_three = reach.get(3, 1.0) if start > 3 else 1.0
    p_page_one = reach.get(TOP_N, 1.0) if start > TOP_N else 1.0
    likely = min(p for p, r in reach.items() if r >= 0.5)
    return {
        "p_top_three": p_top_three,
        "p_page_one": p_page_one,
        "likely_position": likely,
        "winnability": round(100 * (p_top_three + p_page_one) / 2, 1),
    }


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)
