import math
from collections.abc import Mapping, Sequence

from src.site_pages.schemas import SitePageEdge


def page_rank(
    ids: Sequence[str],
    edges: Sequence[SitePageEdge],
    damping: float = 0.85,
    iterations: int = 24,
    teleport: Mapping[str, float] | None = None,
) -> dict[str, float]:
    n = len(ids)
    result: dict[str, float] = {}
    if n == 0:
        return result

    index = {page_id: i for i, page_id in enumerate(ids)}
    out_weight = [0.0] * n
    inbound: list[list[tuple[int, float]]] = [[] for _ in range(n)]
    for e in edges:
        src = index.get(e.src)
        dst = index.get(e.dst)
        w = float(getattr(e, "weight", 1.0))
        if src is None or dst is None or src == dst or w <= 0:
            continue
        out_weight[src] += w
        inbound[dst].append((src, w))

    tele = [1 / n] * n
    if teleport is not None:
        total = 0.0
        for i in range(n):
            w = max(teleport.get(ids[i], 0.0), 0.0)
            tele[i] = w
            total += w
        tele = [w / total for w in tele] if total > 0 else [1 / n] * n

    rank = [1 / n] * n
    for _ in range(iterations):
        dangling = sum(rank[i] for i in range(n) if out_weight[i] == 0)
        nxt = [(1 - damping + damping * dangling) * tele[i] for i in range(n)]
        for i in range(n):
            for src, w in inbound[i]:
                nxt[i] += damping * rank[src] * w / out_weight[src]
        rank = nxt

    top = max(1e-12, max(rank))
    for i, page_id in enumerate(ids):
        result[page_id] = math.floor(rank[i] / top * 1000 + 0.5) / 10
    return result
