from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import numpy as np
from sklearn.cluster import AgglomerativeClustering

TOPIC_WORDS = 3
STOPWORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "how",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "what",
        "with",
        "your",
        "you",
        "we",
        "our",
    ]
)


@dataclass(frozen=True)
class PagePoint:
    id: str
    url: str
    title: str | None
    page_type: str | None
    inlinks: int
    keywords: tuple[str, ...]
    vector: np.ndarray


def unit(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm > 0 else vector


def cluster_pages(points: Sequence[PagePoint], min_cohesion: float) -> list[list[str]]:
    if len(points) < 2:
        return []
    matrix = np.stack([unit(p.vector) for p in points])
    labels = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=1.0 - min_cohesion,
        metric="cosine",
        linkage="average",
    ).fit_predict(matrix)
    groups: dict[int, list[str]] = {}
    for point, label in zip(points, labels, strict=True):
        groups.setdefault(int(label), []).append(point.id)
    return [members for members in groups.values() if len(members) > 1]


def centroid(members: Iterable[str], vectors: dict[str, np.ndarray]) -> np.ndarray | None:
    rows = [unit(vectors[m]) for m in members if m in vectors]
    if not rows:
        return None
    return unit(np.mean(np.stack(rows), axis=0))


def cohesion(members: Sequence[str], vectors: dict[str, np.ndarray]) -> float:
    rows = [unit(vectors[m]) for m in members if m in vectors]
    if len(rows) < 2:
        return 1.0
    matrix = np.stack(rows)
    sims = matrix @ matrix.T
    n = len(rows)
    return float((sims.sum() - np.trace(sims)) / (n * (n - 1)))


@dataclass(frozen=True)
class Coverage:
    page_id: str | None
    score: float


def coverage(
    members: Sequence[str],
    vectors: dict[str, np.ndarray],
    links: dict[str, set[str]],
) -> Coverage:
    center = centroid(members, vectors)
    member_set = set(members)
    if center is None or not member_set:
        return Coverage(page_id=None, score=0.0)
    best = Coverage(page_id=None, score=0.0)
    for page_id, targets in links.items():
        hit = len(targets & member_set)
        if hit == 0 or page_id not in vectors:
            continue
        similarity = max(0.0, float(unit(vectors[page_id]) @ center))
        score = similarity * hit / len(member_set)
        if score > best.score:
            best = Coverage(page_id=page_id, score=score)
    return best


def overlap(a: Iterable[str], b: Iterable[str]) -> float:
    left, right = set(a), set(b)
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def topic_for(points: Sequence[PagePoint]) -> str:
    counts: Counter[str] = Counter()
    for p in points:
        counts.update(k.strip().lower() for k in p.keywords if k.strip())
    if not counts:
        for p in points:
            words = [
                w for w in (p.title or "").lower().split() if w.isalpha() and w not in STOPWORDS
            ]
            counts.update(set(words))
    top = [word for word, _ in counts.most_common(TOPIC_WORDS)]
    return ", ".join(top) if top else "untitled topic"


def structural_share(points: Sequence[PagePoint], structural_types: Sequence[str]) -> float:
    if not points:
        return 0.0
    return sum(1 for p in points if p.page_type in structural_types) / len(points)
