from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.seo import repository as repo
from src.seo.schemas import PageSuggestionRecord


async def review_state(db: AsyncSession, site_id: str, row: PageSuggestionRecord) -> dict[str, Any]:
    head = await repo.find_keyword(db, site_id, row.topic_key)
    keyword_ids = await repo.suggestion_keyword_ids(db, row.id)
    state: dict[str, Any] = {
        "action": row.action,
        "topic": row.topic_key,
        "strategies": list(row.strategies),
        "suggestion": row.suggestion,
        "evidence": row.evidence,
        "keywords": await repo.keyword_facts_for(db, site_id, keyword_ids),
        "page": await repo.page_brief(db, site_id, row.page_id),
        "serp": await repo.latest_serp(db, site_id, head.id) if head else None,
    }
    if row.action == "add" and head:
        state["nearest_page"] = await repo.nearest_page(db, site_id, head.id)
        state["questions"] = await repo.paa_questions(db, site_id, head.id)
    if row.action == "delete":
        state["merge_into"] = await repo.page_brief(db, site_id, row.merge_into_page_id)
    if row.pair_id:
        partner = await repo.get_suggestion(db, site_id, row.pair_id)
        if partner is not None:
            state["pair"] = {
                "action": partner.action,
                "suggestion": partner.suggestion,
                "page": await repo.page_brief(db, site_id, partner.page_id),
            }
    return state


def has_serp_evidence(state: dict[str, Any]) -> bool:
    serp = state.get("serp") or {}
    return bool(serp.get("results")) or bool(state.get("questions"))
