from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.seo.keyword_content_pages.repository import seo_keyword_content_pages
from src.seo.keywords.repository import seo_keywords
from src.seo.page_facts.repository import seo_page_facts
from src.seo.page_suggestion_keywords.repository import seo_page_suggestion_keywords
from src.seo.page_suggestions.repository import seo_page_suggestions
from src.seo.page_suggestions.schemas import PageSuggestionRecord
from src.seo.serp_results.repository import seo_serp_results
from src.seo.serp_snapshots.repository import seo_serp_snapshots

SERP_TOP = 3

QUESTIONS_TOP = 10


def has_serp_evidence(state: dict[str, Any]) -> bool:
    serp = state.get("serp") or {}
    return bool(serp.get("results")) or bool(state.get("questions"))


class SeoReviewInputService:
    async def keyword_facts(
        self, db: AsyncSession, site_id: str, keyword_ids: list[str]
    ) -> list[dict]:
        return [
            {
                "keyword": k.keyword,
                "volume": k.volume,
                "difficulty": k.difficulty,
                "intent": k.intent,
                "impressions_28d": k.impressions_28d,
                "clicks_28d": k.clicks_28d,
            }
            for k in await seo_keywords.list_by_ids(db, site_id, keyword_ids)
        ]

    async def page_brief(
        self, db: AsyncSession, site_id: str, page_id: str | None
    ) -> dict[str, Any] | None:
        if page_id is None:
            return None
        page = await seo_page_facts.get(db, site_id, page_id)
        if page is None:
            return None
        return {
            "url": page.url,
            "title": page.title,
            "h1": page.h1,
            "headings": list(page.headings)[:30],
            "meta_description": page.meta_description,
            "page_type": page.page_type,
            "word_count": page.word_count,
            "inlinks": page.inlinks,
            "impressions_28d": page.impressions_28d,
            "clicks_28d": page.clicks_28d,
        }

    async def latest_serp(
        self, db: AsyncSession, site_id: str, keyword_id: str
    ) -> dict[str, Any] | None:
        snapshot = await seo_serp_snapshots.latest(db, site_id, keyword_id)
        if snapshot is None:
            return None
        results = await seo_serp_results.top_for_snapshot(db, snapshot.id, SERP_TOP)
        return {
            "features": list(snapshot.features),
            "results": [
                {
                    "rank": r.rank,
                    "domain": r.domain,
                    "title": r.title,
                    "description": r.description,
                    "ours": r.is_ours,
                }
                for r in results
            ],
        }

    async def nearest_page(
        self, db: AsyncSession, site_id: str, keyword_id: str
    ) -> dict[str, Any] | None:
        candidates = await seo_keyword_content_pages.list_for_keyword(db, site_id, keyword_id)
        pages = {
            p.page_id: p
            for p in await seo_page_facts.list_by_page_ids(
                db, site_id, [c.page_id for c in candidates]
            )
        }
        for candidate in candidates:
            page = pages.get(candidate.page_id)
            if page is not None and page.live:
                return {
                    "url": page.url,
                    "title": page.title,
                    "coverage": round(candidate.coverage, 2),
                }
        return None

    async def review_state(
        self, db: AsyncSession, site_id: str, row: PageSuggestionRecord
    ) -> dict[str, Any]:
        head = await seo_keywords.find(db, site_id, row.topic_key)
        keyword_ids = await seo_page_suggestion_keywords.keyword_ids(db, row.id)
        state: dict[str, Any] = {
            "action": row.action,
            "topic": row.topic_key,
            "strategies": list(row.strategies),
            "suggestion": row.suggestion,
            "evidence": row.evidence,
            "keywords": await self.keyword_facts(db, site_id, keyword_ids),
            "page": await self.page_brief(db, site_id, row.page_id),
            "serp": await self.latest_serp(db, site_id, head.id) if head else None,
        }
        if row.action == "add" and head:
            state["nearest_page"] = await self.nearest_page(db, site_id, head.id)
            state["questions"] = (
                await seo_keywords.seeded_terms(db, site_id, head.id, "serp_paa")
            )[:QUESTIONS_TOP]
        if row.action == "delete":
            state["merge_into"] = await self.page_brief(db, site_id, row.merge_into_page_id)
        if row.pair_id:
            partner = await seo_page_suggestions.get(db, site_id, row.pair_id)
            if partner is not None:
                state["pair"] = {
                    "action": partner.action,
                    "suggestion": partner.suggestion,
                    "page": await self.page_brief(db, site_id, partner.page_id),
                }
        return state


seo_review_input_service = SeoReviewInputService()
