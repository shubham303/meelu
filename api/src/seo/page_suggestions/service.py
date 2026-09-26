from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.seo.clusters.repository import seo_keyword_clusters
from src.seo.constants import CLICKS_FLOOR, OPEN_STATES, OWNER_COVERAGE, REVIVABLE_STATES
from src.seo.jobs.service import seo_job_service
from src.seo.keyword_content_pages.repository import seo_keyword_content_pages
from src.seo.keyword_gsc_pages.repository import seo_keyword_gsc_pages
from src.seo.keywords.repository import seo_keywords
from src.seo.keywords.service import seo_keyword_service
from src.seo.page_facts.repository import seo_page_facts
from src.seo.page_facts.schemas import PageFactsRecord
from src.seo.page_suggestion_keywords.repository import seo_page_suggestion_keywords
from src.seo.page_suggestions.repository import seo_page_suggestions
from src.seo.page_suggestions.schemas import (
    Collision,
    CreateResult,
    NewPageSuggestion,
    PageSuggestionFilter,
    PageSuggestionRecord,
    SavePageSuggestionRequest,
)

SUGGESTION_NOT_FOUND = "No such page suggestion on this website."

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


class SeoPageSuggestionService:
    async def list(
        self, db: AsyncSession, site_id: str, f: PageSuggestionFilter, paging: PaginationParams
    ) -> PaginatedApiResponse[PageSuggestionRecord]:
        return await seo_page_suggestions.list(db, site_id, f, paging)

    async def get(self, db: AsyncSession, site_id: str, suggestion_id: str) -> PageSuggestionRecord:
        found = await seo_page_suggestions.get(db, site_id, suggestion_id)
        if found is None:
            raise HTTPException(404, SUGGESTION_NOT_FOUND)
        return found

    async def settle(
        self, db: AsyncSession, site_id: str, suggestion_id: str, state: str
    ) -> PageSuggestionRecord:
        await self.get(db, site_id, suggestion_id)
        ids = await seo_page_suggestions.pair_ids(db, site_id, suggestion_id)
        await seo_page_suggestions.set_state(db, site_id, ids, state, OPEN_STATES)
        return await self.get(db, site_id, suggestion_id)

    async def save(
        self, db: AsyncSession, user_id: str, site_id: str, body: SavePageSuggestionRequest
    ) -> CreateResult:
        await seo_job_service.get(db, site_id, body.job_id)
        keyword_ids = list(body.keyword_ids)
        if body.terms:
            keyword_ids += await seo_keyword_service.add(db, user_id, site_id, body.terms, "user")
        new = NewPageSuggestion(
            action=body.action,
            topic_key=body.topic_key,
            page_id=body.page_id,
            merge_into_page_id=body.merge_into_page_id,
            keyword_ids=keyword_ids,
            strategy="agent",
            suggestion=body.suggestion,
            evidence=body.evidence,
            state="ready",
        )
        return await self.create_many(db, user_id, site_id, body.job_id, [new])

    async def page_coverage(
        self, db: AsyncSession, site_id: str, keyword_id: str, page_id: str
    ) -> float | None:
        gsc = await seo_keyword_gsc_pages.coverage_of(db, site_id, keyword_id, page_id)
        if gsc is not None:
            return gsc
        return await seo_keyword_content_pages.coverage_of(db, site_id, keyword_id, page_id)

    async def delete_refusal(
        self, db: AsyncSession, site_id: str, page: PageFactsRecord | None, merge_into: str | None
    ) -> str | None:
        if page is None or not page.live:
            return "page_gone"
        if merge_into is None:
            return "no_merge_target"
        target = await seo_page_facts.get(db, site_id, merge_into)
        if target is None or not target.live:
            return "merge_target_gone"
        if page.is_home or page.page_type in PROTECTED_TYPES:
            return "protected_type"
        if page.inlinks > await seo_page_facts.inlinks_median(db, site_id):
            return "protected_inlinks"
        if page.first_seen_at and page.first_seen_at > datetime.now(UTC) - timedelta(
            days=YOUNG_PAGE_DAYS
        ):
            return "protected_young"
        if page.clicks_28d >= CLICKS_FLOOR:
            return "protected_clicks"
        return None

    async def owner_conversion(
        self, db: AsyncSession, site_id: str, new: NewPageSuggestion
    ) -> NewPageSuggestion:
        if new.action != "add":
            return new
        topic = await seo_keywords.find(db, site_id, new.topic_key)
        cluster = await seo_keyword_clusters.find_by_head(db, site_id, topic.id) if topic else None
        if cluster is None or cluster.owner_page_id is None:
            return new
        if (cluster.owner_coverage or 0) < OWNER_COVERAGE:
            return new
        head = await seo_keywords.get(db, site_id, cluster.head_keyword_id)
        page = await seo_page_facts.get(db, site_id, cluster.owner_page_id)
        if page is None or not page.live:
            return new
        if not compatible(head.intent if head else None, page.page_type):
            return new
        return new.model_copy(
            update={"action": "edit", "page_id": page.page_id, "cluster_id": cluster.id}
        )

    async def baselines(
        self, db: AsyncSession, site_id: str, new: NewPageSuggestion
    ) -> dict[str, Any]:
        values: dict[str, Any] = {"coverage_at_creation": None, "impressions_at_creation": None}
        if new.page_id is None:
            return values
        page = await seo_page_facts.get(db, site_id, new.page_id)
        if page is not None:
            values["impressions_at_creation"] = page.impressions_28d
        head = await seo_keywords.find(db, site_id, new.topic_key)
        if head is not None:
            values["coverage_at_creation"] = await self.page_coverage(
                db, site_id, head.id, new.page_id
            )
        return values

    async def classify(self, db: AsyncSession, site_id: str, new: NewPageSuggestion) -> Outcome:
        if new.action == "delete":
            page = await seo_page_facts.get(db, site_id, new.page_id) if new.page_id else None
            refusal = await self.delete_refusal(db, site_id, page, new.merge_into_page_id)
            if refusal:
                return Outcome("refused", refusal=refusal)
        elif new.page_id is not None:
            page = await seo_page_facts.get(db, site_id, new.page_id)
            if page is None or not page.live:
                return Outcome("refused", refusal="page_gone")
        existing = await seo_page_suggestions.find(
            db, site_id, new.action, new.page_id, new.topic_key
        )
        if existing is None:
            return Outcome("insert")
        if existing.state in REVIVABLE_STATES:
            return Outcome("revive", existing)
        if existing.state in OPEN_STATES:
            return Outcome("touch", existing)
        return Outcome("blocked", existing)

    async def write_one(
        self,
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
                await seo_page_suggestions.touch(
                    db, site_id, existing.id, new.strategy, new.evidence
                )
            result.collided.append(
                Collision(id=existing.id, state=existing.state, strategies=existing.strategies)
            )
            return None
        values = _values(new, await self.baselines(db, site_id, new))
        if outcome.kind == "revive":
            assert outcome.existing is not None
            values["strategies"] = [
                *[s for s in outcome.existing.strategies if s != new.strategy],
                new.strategy,
            ]
            await seo_page_suggestions.revive(db, site_id, outcome.existing.id, job_id, values)
            suggestion_id = outcome.existing.id
        else:
            suggestion_id = await seo_page_suggestions.create(db, user_id, site_id, job_id, values)
        await seo_page_suggestion_keywords.replace(db, suggestion_id, new.keyword_ids)
        result.drafts += 1
        result.ids.append(suggestion_id)
        return suggestion_id

    async def create_many(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        job_id: str,
        rows: list[NewPageSuggestion],
    ) -> CreateResult:
        result = CreateResult()
        converted = [await self.owner_conversion(db, site_id, r) for r in rows]
        outcomes = [await self.classify(db, site_id, r) for r in converted]
        done: set[int] = set()
        for index, new in enumerate(converted):
            if index in done:
                continue
            partner = new.pair_with
            if partner is None or partner >= len(converted):
                await self.write_one(db, user_id, site_id, job_id, new, outcomes[index], result)
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
                        await self.write_one(
                            db, user_id, site_id, job_id, converted[i], outcomes[i], result
                        )
                continue
            first = await self.write_one(db, user_id, site_id, job_id, new, outcomes[index], result)
            second = await self.write_one(
                db, user_id, site_id, job_id, converted[partner], outcomes[partner], result
            )
            if first and second:
                await seo_page_suggestions.link_pair(db, site_id, first, second)
        return result


seo_page_suggestion_service = SeoPageSuggestionService()
