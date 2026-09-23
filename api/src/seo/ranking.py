from sqlalchemy.ext.asyncio import AsyncSession

from src.seo import repository as repo
from src.seo.schemas import PageSuggestionRecord, RankResult


def score_of(row: PageSuggestionRecord) -> float:
    base = float(row.search_score or 0.0)
    evidence = row.evidence or {}
    if row.action == "add":
        keywords = evidence.get("keywords") or evidence.get("missing") or []
        volume = sum(float(k.get("volume") or 0) for k in keywords if isinstance(k, dict))
        competitors = len(evidence.get("competitors") or [])
        difficulty = float(evidence.get("difficulty") or 50)
        base = max(base, volume * (1 + competitors)) / (difficulty + 1)
    if row.confidence is not None:
        base *= 0.5 + row.confidence / 2
    return base


async def rank(db: AsyncSession, site_id: str, job_id: str, budgets: dict[str, int]) -> RankResult:
    rows = await repo.job_rows(db, site_id, job_id, None, ("reviewed",), 10_000)
    result = RankResult()
    scored = {r.id: score_of(r) for r in rows}
    by_id = {r.id: r for r in rows}
    items: dict[str, list[PageSuggestionRecord]] = {"add": [], "edit": [], "delete": []}
    consumed: set[str] = set()
    for row in sorted(rows, key=lambda r: scored[r.id], reverse=True):
        if row.id in consumed:
            continue
        consumed.add(row.id)
        if row.pair_id and row.pair_id in by_id:
            consumed.add(row.pair_id)
            items["delete"].append(row)
        else:
            items[row.action].append(row)
    for action, ranked in items.items():
        budget = budgets.get(action, 0)
        for index, row in enumerate(ranked):
            kept = index < budget
            state = "ready" if kept else "llm_rejected"
            patch = {"state": state, "score": scored[row.id]}
            await repo.update_suggestion(db, site_id, row.id, patch)
            if row.pair_id and row.pair_id in by_id:
                await repo.update_suggestion(
                    db, site_id, row.pair_id, {"state": state, "score": scored[row.id]}
                )
            if kept:
                result.kept += 1
            else:
                result.llm_rejected += 1
    return result
