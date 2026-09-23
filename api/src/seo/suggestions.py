from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.seo import repository as repo
from src.seo.constants import CLICKS_FLOOR, OPEN_STATES, OWNER_COVERAGE, REVIVABLE_STATES
from src.seo.schemas import Collision, CreateResult, NewPageSuggestion, PageFactsRecord

PROTECTED_TYPES = ("money", "hub")

YOUNG_PAGE_DAYS = 90

COMPATIBLE_TYPES = {
    "transactional": ("money",),
    "commercial": ("money", "hub", "informational"),
    "informational": ("informational", "hub", "support"),
    "navigational": ("money", "hub", "company", "support", "informational"),
}


def compatible(intent: str | None, page_type: str | None) -> bool:
    if intent is None or page_type is None:
        return True
    return page_type in COMPATIBLE_TYPES.get(intent, ())


async def delete_refusal(
    db: AsyncSession, site_id: str, page: PageFactsRecord | None, merge_into: str | None
) -> str | None:
    if page is None or not page.live:
        return "page_gone"
    if merge_into is None:
        return "no_merge_target"
    target = await repo.get_page_facts(db, site_id, merge_into)
    if target is None or not target.live:
        return "merge_target_gone"
    if page.is_home or page.page_type in PROTECTED_TYPES:
        return "protected_type"
    if page.inlinks > await repo.inlinks_median(db, site_id):
        return "protected_inlinks"
    if page.first_seen_at and page.first_seen_at > datetime.now(UTC) - timedelta(
        days=YOUNG_PAGE_DAYS
    ):
        return "protected_young"
    if page.clicks_28d >= CLICKS_FLOOR:
        return "protected_clicks"
    return None


async def owner_conversion(
    db: AsyncSession, site_id: str, new: NewPageSuggestion
) -> NewPageSuggestion:
    if new.action != "add":
        return new
    cluster = await repo.cluster_by_head(db, site_id, new.topic_key)
    if cluster is None or cluster.owner_page_id is None:
        return new
    if (cluster.owner_coverage or 0) < OWNER_COVERAGE:
        return new
    head = await repo.get_keyword(db, site_id, cluster.head_keyword_id)
    page = await repo.get_page_facts(db, site_id, cluster.owner_page_id)
    if page is None or not page.live:
        return new
    if not compatible(head.intent if head else None, page.page_type):
        return new
    return new.model_copy(
        update={"action": "edit", "page_id": page.page_id, "cluster_id": cluster.id}
    )


async def baselines(db: AsyncSession, site_id: str, new: NewPageSuggestion) -> dict[str, Any]:
    values: dict[str, Any] = {"coverage_at_creation": None, "impressions_at_creation": None}
    if new.page_id is None:
        return values
    page = await repo.get_page_facts(db, site_id, new.page_id)
    if page is not None:
        values["impressions_at_creation"] = page.impressions_28d
    head = await repo.find_keyword(db, site_id, new.topic_key)
    if head is not None:
        values["coverage_at_creation"] = await repo.page_coverage(db, site_id, head.id, new.page_id)
    return values


def _values(new: NewPageSuggestion, extra: dict[str, Any]) -> dict[str, Any]:
    return {
        "action": new.action,
        "page_id": new.page_id,
        "topic_key": new.topic_key,
        "cluster_id": new.cluster_id,
        "merge_into_page_id": new.merge_into_page_id,
        "strategies": [new.strategy],
        "suggestion": new.suggestion,
        "evidence": new.evidence,
        "search_score": new.search_score,
        "target_position": new.target_position,
        "state": new.state,
        **extra,
    }


class Outcome:
    def __init__(self, kind: str, existing=None, refusal: str | None = None):
        self.kind = kind
        self.existing = existing
        self.refusal = refusal


async def classify(db: AsyncSession, site_id: str, new: NewPageSuggestion) -> Outcome:
    if new.action == "delete":
        page = await repo.get_page_facts(db, site_id, new.page_id) if new.page_id else None
        refusal = await delete_refusal(db, site_id, page, new.merge_into_page_id)
        if refusal:
            return Outcome("refused", refusal=refusal)
    elif new.page_id is not None:
        page = await repo.get_page_facts(db, site_id, new.page_id)
        if page is None or not page.live:
            return Outcome("refused", refusal="page_gone")
    existing = await repo.find_suggestion(db, site_id, new.action, new.page_id, new.topic_key)
    if existing is None:
        return Outcome("insert")
    if existing.state in REVIVABLE_STATES:
        return Outcome("revive", existing)
    if existing.state in OPEN_STATES:
        return Outcome("touch", existing)
    return Outcome("blocked", existing)


async def write_one(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    job_id: str,
    new: NewPageSuggestion,
    outcome: Outcome,
    result: CreateResult,
) -> str | None:
    if outcome.kind == "refused":
        result.filtered[outcome.refusal or "refused"] = (
            result.filtered.get(outcome.refusal or "refused", 0) + 1
        )
        return None
    if outcome.kind in ("touch", "blocked"):
        existing = outcome.existing
        if outcome.kind == "touch":
            await repo.touch_suggestion(db, site_id, existing.id, new.strategy, new.evidence)
        result.collided.append(
            Collision(id=existing.id, state=existing.state, strategies=existing.strategies)
        )
        return None
    values = _values(new, await baselines(db, site_id, new))
    if outcome.kind == "revive":
        assert outcome.existing is not None
        values["strategies"] = [
            *[s for s in outcome.existing.strategies if s != new.strategy],
            new.strategy,
        ]
        await repo.revive_suggestion(db, site_id, outcome.existing.id, job_id, values)
        suggestion_id = outcome.existing.id
    else:
        suggestion_id = await repo.insert_suggestion(db, user_id, site_id, job_id, values)
    await repo.replace_suggestion_keywords(db, suggestion_id, new.keyword_ids)
    result.drafts += 1
    result.ids.append(suggestion_id)
    return suggestion_id


async def create_many(
    db: AsyncSession, user_id: str, site_id: str, job_id: str, rows: list[NewPageSuggestion]
) -> CreateResult:
    result = CreateResult()
    converted = [await owner_conversion(db, site_id, r) for r in rows]
    outcomes = [await classify(db, site_id, r) for r in converted]
    done: set[int] = set()
    for index, new in enumerate(converted):
        if index in done:
            continue
        partner = new.pair_with
        if partner is None or partner >= len(converted):
            await write_one(db, user_id, site_id, job_id, new, outcomes[index], result)
            done.add(index)
            continue
        pair = (index, partner)
        done.update(pair)
        creatable = all(outcomes[i].kind in ("insert", "revive") for i in pair)
        if not creatable:
            for i in pair:
                if outcomes[i].kind in ("insert", "revive"):
                    result.filtered["pair_blocked"] = result.filtered.get("pair_blocked", 0) + 1
                else:
                    await write_one(db, user_id, site_id, job_id, converted[i], outcomes[i], result)
            continue
        first = await write_one(db, user_id, site_id, job_id, new, outcomes[index], result)
        second = await write_one(
            db, user_id, site_id, job_id, converted[partner], outcomes[partner], result
        )
        if first and second:
            await repo.link_pair(db, site_id, first, second)
    return result
