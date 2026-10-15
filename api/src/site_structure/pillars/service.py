from __future__ import annotations

from statistics import fmean
from typing import Any

import numpy as np
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.workspace import workspace_tables
from src.core.logging import get_logger
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.credits.service import InsufficientCreditsError
from src.providers.errors import NoProviderError, ProviderRequestError
from src.providers.json_data_extractor.service import json_data_extractor
from src.providers.registry import Caller
from src.site_pages.llm_extraction.repository import site_page_llm_extractions
from src.site_pages.repositories.chunks import site_chunks
from src.site_pages.repositories.links import site_page_links
from src.site_pages.repositories.pages import site_pages
from src.site_pages.schemas import SitePageBrief
from src.site_pages.schemas.llm_extraction import extracted_details
from src.site_structure.constants import (
    PILLAR_COVERED,
    PILLAR_DONE_FRACTION,
    PILLAR_OVERLAP,
    PILLAR_PARTLY_COVERED,
    PILLAR_STALE_FRACTION,
    PillarAction,
    SuggestionState,
)
from src.site_structure.jobs.service import structure_job_service
from src.site_structure.pillars import clustering, review, screening
from src.site_structure.pillars.clustering import PagePoint
from src.site_structure.pillars.repository import pillar_page_suggestions
from src.site_structure.pillars.schemas import (
    NewPillarPageSuggestion,
    PillarMember,
    PillarPageSuggestionChanges,
    PillarPageSuggestionCreateRequest,
    PillarPageSuggestionFilter,
    PillarPageSuggestionRecord,
    PillarPageSuggestionSummaryResponse,
    PillarPageSuggestionUpdateRequest,
    PillarRankRequest,
    PillarReviewInput,
    PillarReviewInputsRequest,
    PillarScreenRequest,
    PillarsRequest,
    PillarsResult,
    PillarVerdictRequest,
    ReconcileResult,
    WorkspaceGroup,
)
from src.site_structure.pipeline.page_facts import page_facts_service
from src.site_structure.pipeline.ranking import percentile
from src.site_structure.pipeline.schemas import (
    RankResult,
    ReviewBatch,
    ReviewItem,
    ReviewResult,
    ScreenResult,
)
from src.site_structure.pipeline.screening import screened_state, yes_confidence

log = get_logger("site_structure.pillars.service")

NOT_FOUND = "No such pillar page suggestion on this website."

REJECTED_STATES = frozenset(
    {
        SuggestionState.SCREENING_REJECTED,
        SuggestionState.REVIEW_REJECTED,
        SuggestionState.USER_REJECTED,
    }
)


def _suggestion_text(
    action: PillarAction, topic: str, members: list[PagePoint], covering_url: str | None
) -> str:
    titles = "; ".join((m.title or m.url) for m in members[:8])
    more = f" and {len(members) - 8} more" if len(members) > 8 else ""
    if action is PillarAction.EXPAND:
        return (
            f"Expand {covering_url} into the hub for {topic}: introduce the topic and link every "
            f"page on it ({titles}{more}), and have those pages link back."
        )
    return (
        f"Create a pillar page about {topic} that introduces the topic and links each page on it "
        f"({titles}{more}); have those pages link back to it."
    )


class PillarPageSuggestionService:
    async def get(
        self, db: AsyncSession, site_id: str, suggestion_id: str
    ) -> PillarPageSuggestionRecord:
        found = await pillar_page_suggestions.get(db, site_id, suggestion_id)
        if found is None:
            raise HTTPException(404, NOT_FOUND)
        return (await self._with_pages(db, site_id, [found]))[0]

    async def list(
        self,
        db: AsyncSession,
        site_id: str,
        filters: PillarPageSuggestionFilter,
        paging: PaginationParams,
    ) -> PaginatedApiResponse[PillarPageSuggestionRecord]:
        page = await pillar_page_suggestions.list(db, site_id, filters, paging)
        page.data = await self._with_pages(db, site_id, page.data)
        return page

    async def summary(self, db: AsyncSession, site_id: str) -> PillarPageSuggestionSummaryResponse:
        return await pillar_page_suggestions.summary(db, site_id)

    async def create(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        body: PillarPageSuggestionCreateRequest,
    ) -> PillarPageSuggestionRecord:
        await structure_job_service.get(db, site_id, body.job_id)
        page_ids = body.member_page_ids + ([body.covering_page_id] if body.covering_page_id else [])
        missing = set(page_ids) - await site_pages.existing_ids(db, site_id, page_ids)
        if missing:
            raise HTTPException(
                404, f"No such pages on this website: {', '.join(sorted(missing))}."
            )
        gone = await site_pages.gone_ids(db, site_id, page_ids)
        if gone:
            raise HTTPException(
                400,
                "Every page must be live; these are gone, redirected or blocked by robots: "
                f"{', '.join(sorted(gone))}.",
            )
        clash = await pillar_page_suggestions.find_by_members(db, site_id, body.member_page_ids)
        if clash is not None:
            raise HTTPException(
                409,
                f"A pillar suggestion for exactly these pages already exists "
                f"({clash.id}, {clash.state}).",
            )
        created = await pillar_page_suggestions.create(db, user_id, site_id, body.to_new())
        return (await self._with_pages(db, site_id, [created]))[0]

    async def update(
        self,
        db: AsyncSession,
        site_id: str,
        suggestion_id: str,
        body: PillarPageSuggestionUpdateRequest,
    ) -> PillarPageSuggestionRecord:
        updated = await pillar_page_suggestions.update(
            db, site_id, suggestion_id, body.to_changes()
        )
        if updated is None:
            raise HTTPException(404, NOT_FOUND)
        return (await self._with_pages(db, site_id, [updated]))[0]

    async def delete(
        self, db: AsyncSession, site_id: str, suggestion_id: str
    ) -> PillarPageSuggestionRecord:
        found = await pillar_page_suggestions.get(db, site_id, suggestion_id)
        if found is None:
            raise HTTPException(404, NOT_FOUND)
        await pillar_page_suggestions.delete(db, site_id, found.id)
        return found

    async def reconcile(self, db: AsyncSession, site_id: str) -> ReconcileResult:
        rows = await pillar_page_suggestions.list_for_site(db, site_id)
        page_ids = list(
            {p for r in rows for p in r.member_page_ids}
            | {r.covering_page_id for r in rows if r.covering_page_id}
        )
        live = await site_pages.existing_ids(db, site_id, page_ids) - await site_pages.gone_ids(
            db, site_id, page_ids
        )
        inbound = await site_page_links.pairs_into(
            db, site_id, list({p for r in rows for p in r.member_page_ids} & live)
        )
        changed_at = await site_pages.changed_at_by_id(
            db, site_id, list({src for src, _ in inbound})
        )
        targets_by_src: dict[str, set[str]] = {}
        for src, dst in inbound:
            targets_by_src.setdefault(src, set()).add(dst)

        invalid: set[str] = set()
        for row in rows:
            if row.action is PillarAction.EXPAND and row.covering_page_id not in live:
                invalid.add(row.id)
                continue
            alive = set(row.member_page_ids) & live
            if not alive or len(alive) / len(row.member_page_ids) < PILLAR_STALE_FRACTION:
                invalid.add(row.id)
                continue
            covered = max(
                (
                    len(targets & alive)
                    for src, targets in targets_by_src.items()
                    if changed_at[src] > row.created_at
                ),
                default=0,
            )
            if covered / len(alive) >= PILLAR_DONE_FRACTION:
                invalid.add(row.id)
        return ReconcileResult(
            removed=await pillar_page_suggestions.delete_many(db, site_id, invalid)
        )

    async def propose_pillar_pages(
        self, db: AsyncSession, user_id: str, site_id: str, body: PillarsRequest
    ) -> PillarsResult:
        await structure_job_service.get(db, site_id, body.job_id)
        live_pages = await site_pages.list_not_gone(db, site_id)
        points = await self._page_points(db, site_id, live_pages)
        by_id = {p.id: p for p in points}
        vectors = {p.id: p.vector for p in points}
        if body.source_table:
            try:
                groups = self._workspace_groups(
                    await workspace_tables.rows(user_id, site_id, body.source_table),
                    body.source_table,
                )
            except ValueError as exc:
                raise HTTPException(400, str(exc)) from exc
        else:
            groups = [
                WorkspaceGroup(key=str(i), page_ids=members)
                for i, members in enumerate(clustering.cluster_pages(points, body.min_cohesion))
            ]
        result = PillarsResult(groups=len(groups))
        if not groups:
            return result
        live = {p.id for p in live_pages}
        candidates = list({p for g in groups for p in g.page_ids if p in live})
        links: dict[str, set[str]] = {}
        for src, dst in await site_page_links.pairs_into(db, site_id, candidates):
            if src not in by_id or not clustering.is_structural(by_id[src]):
                links.setdefault(src, set()).add(dst)
        existing = await pillar_page_suggestions.member_sets(db, site_id)
        rejected_sets = [m for state, m in existing if state in REJECTED_STATES]
        open_sets = [m for state, m in existing if state not in REJECTED_STATES]
        kept: list[NewPillarPageSuggestion] = []
        for group in groups:
            members = [p for p in dict.fromkeys(group.page_ids) if p in live]
            structural = [m for m in members if m in by_id and clustering.is_structural(by_id[m])]
            if structural:
                result.structural_pages += len(structural)
                members = [m for m in members if m not in structural]
            if len(members) < body.min_size:
                result.too_small += 1
                continue
            cohesion = clustering.cohesion(members, vectors)
            if cohesion < body.min_cohesion:
                result.too_loose += 1
                continue
            known = [by_id[m] for m in members if m in by_id]
            if clustering.mixed_families(known):
                result.mixed_types += 1
                continue
            cover = clustering.coverage(members, vectors, links)
            if cover.score >= PILLAR_COVERED:
                result.covered += 1
                continue
            if any(clustering.overlap(members, s) >= PILLAR_OVERLAP for s in rejected_sets):
                result.overlaps_rejected += 1
                continue
            if any(
                clustering.overlap(members, s) >= PILLAR_OVERLAP
                for s in open_sets + [k.member_page_ids for k in kept]
            ):
                result.overlaps_open += 1
                continue
            action = (
                PillarAction.EXPAND
                if cover.score >= PILLAR_PARTLY_COVERED and cover.page_id
                else PillarAction.CREATE
            )
            covering = cover.page_id if action is PillarAction.EXPAND else None
            covering_url = by_id[covering].url if covering and covering in by_id else None
            topic = group.topic or clustering.topic_for(known)
            kept.append(
                NewPillarPageSuggestion(
                    job_id=body.job_id,
                    action=action,
                    topic=topic,
                    member_page_ids=members,
                    covering_page_id=covering,
                    suggestion=_suggestion_text(action, topic, known, covering_url),
                    search_score=cohesion,
                )
            )
        result.inserted = await pillar_page_suggestions.create_many(db, user_id, site_id, kept)
        return result

    async def screen_suggestions(
        self, db: AsyncSession, user_id: str, site_id: str, body: PillarScreenRequest
    ) -> ScreenResult:
        caller = Caller(user_id=user_id, site_id=site_id)
        items = await self._review_inputs(
            db, site_id, SuggestionState.DRAFT, body.job_id, body.ids, body.limit
        )
        result = ScreenResult()
        for item in items:
            try:
                state = await self._screen_one(db, site_id, caller, item)
            except (NoProviderError, InsufficientCreditsError) as exc:
                result.stopped = str(exc)
                break
            if state is None:
                result.failed += 1
                continue
            result.screened += 1
            if state is SuggestionState.SCREENING_APPROVED:
                result.approved += 1
            else:
                result.rejected += 1
        return result

    async def review_inputs(
        self, db: AsyncSession, site_id: str, body: PillarReviewInputsRequest
    ) -> ReviewBatch:
        items = await self._review_inputs(
            db, site_id, SuggestionState.SCREENING_APPROVED, body.job_id, body.ids, body.limit
        )
        return ReviewBatch(
            instructions=review.INSTRUCTIONS.format(prompt=body.prompt),
            schema=review.SCHEMA,
            items=[ReviewItem(id=item.id, state=review.item_state(item)) for item in items],
        )

    async def apply_verdicts(
        self, db: AsyncSession, site_id: str, body: PillarVerdictRequest
    ) -> ReviewResult:
        verdicts = {given.id: given for given in body.verdicts}
        eligible = await pillar_page_suggestions.list_in_state(
            db, site_id, SuggestionState.SCREENING_APPROVED, ids=list(verdicts)
        )
        result = ReviewResult(failed=len(body.verdicts) - len(eligible))
        for row in eligible:
            given = verdicts[row.id]
            changes = PillarPageSuggestionChanges(state=given.verdict)
            if given.verdict is SuggestionState.REVIEW_APPROVED:
                if given.title and given.title.strip():
                    changes.topic = given.title.strip()
                if given.suggestion and given.suggestion.strip():
                    changes.suggestion = given.suggestion.strip()
            await pillar_page_suggestions.update(db, site_id, row.id, changes)
            result.reviewed += 1
            if given.verdict is SuggestionState.REVIEW_APPROVED:
                result.approved += 1
            else:
                result.rejected += 1
        return result

    async def rank_suggestions(
        self, db: AsyncSession, site_id: str, body: PillarRankRequest
    ) -> RankResult:
        rows = await pillar_page_suggestions.list_in_state(
            db, site_id, SuggestionState.REVIEW_APPROVED
        )
        if not rows:
            return RankResult()
        pages, site = await page_facts_service.for_site(db, site_id)
        sizes = sorted(len(r.member_page_ids) for r in rows)
        scores: dict[str, float] = {}
        for row in rows:
            members = [pages[m] for m in row.member_page_ids if m in pages]
            authority = (
                fmean(percentile(site.inlinks, m.inlinks) for m in members) if members else 0.0
            )
            structural = fmean(
                [
                    percentile(sizes, len(row.member_page_ids)),
                    authority,
                    0.5 if row.covering_page_id else 1.0,
                ]
            )
            fit = structural if row.search_score is None else row.search_score * structural
            scores[row.id] = fit * (0.5 + 0.5 * (row.confidence or 0.0))
        ordered = sorted(scores, key=lambda sid: -scores[sid])
        kept = {sid: scores[sid] for sid in ordered[: body.budget]}
        await pillar_page_suggestions.update_scores(db, site_id, kept)
        removed = await pillar_page_suggestions.delete_many(
            db, site_id, set(ordered[body.budget :])
        )
        return RankResult(scored=len(rows), kept=len(kept), removed=removed)

    async def _page_points(
        self, db: AsyncSession, site_id: str, live_pages: list[SitePageBrief]
    ) -> list[PagePoint]:
        vectors = await site_chunks.page_vectors(db, site_id)
        types = await site_page_llm_extractions.page_types_by_page_ids(db, site_id)
        broad = await site_page_llm_extractions.broad_page_types_by_page_ids(db, site_id)
        return [
            PagePoint(
                id=p.id,
                url=p.url,
                title=p.title,
                page_type=types.get(p.id),
                inlinks=p.inlinks,
                vector=np.asarray(vectors[p.id], dtype=float),
                broad_page_type=broad.get(p.id),
            )
            for p in live_pages
            if p.id in vectors
        ]

    def _workspace_groups(self, rows: list[dict[str, Any]], table: str) -> list[WorkspaceGroup]:
        groups: dict[str, WorkspaceGroup] = {}
        for row in rows:
            if not row.get("group_key") or not row.get("page_id"):
                raise ValueError(
                    f"{table} needs group_key and page_id columns (topic is optional)."
                )
            key = str(row["group_key"])
            group = groups.setdefault(key, WorkspaceGroup(key=key))
            group.page_ids.append(str(row["page_id"]))
            topic = row.get("topic")
            if topic and not group.topic:
                group.topic = str(topic)
        return list(groups.values())

    async def _review_inputs(
        self,
        db: AsyncSession,
        site_id: str,
        state: SuggestionState,
        job_id: str | None,
        ids: list[str] | None,
        limit: int,
    ) -> list[PillarReviewInput]:
        rows = await pillar_page_suggestions.list_in_state(db, site_id, state, job_id, ids, limit)
        if not rows:
            return []
        member_ids = {p for r in rows for p in r.member_page_ids}
        wanted = member_ids | {r.covering_page_id for r in rows if r.covering_page_id}
        pages = {p.id: p for p in await site_pages.list_by_ids(db, site_id, list(wanted))}
        extracted = await site_page_llm_extractions.by_page_ids(db, site_id, list(wanted))
        items: list[PillarReviewInput] = []
        for row in rows:
            covering = pages.get(row.covering_page_id)
            items.append(
                PillarReviewInput(
                    id=row.id,
                    action=row.action,
                    topic=row.topic,
                    suggestion=row.suggestion,
                    search_score=row.search_score,
                    covering_url=covering.url if covering else None,
                    covering_title=covering.title if covering else None,
                    covering_details=(
                        extracted_details(extracted.get(covering.id)) if covering else None
                    ),
                    members=[
                        {
                            "url": pages[m].url,
                            "title": pages[m].title or "",
                            "meta_description": pages[m].meta_description or "",
                            "inlinks": pages[m].inlinks,
                            "details": extracted_details(extracted.get(m)),
                        }
                        for m in dict.fromkeys(row.member_page_ids)
                        if m in pages
                    ],
                )
            )
        return items

    async def _screen_one(
        self, db: AsyncSession, site_id: str, caller: Caller, item: PillarReviewInput
    ) -> SuggestionState | None:
        subject = {"pillar_id": item.id, "members": sorted(m["url"] for m in item.members)}
        await db.commit()
        try:
            answer = await json_data_extractor.decide(
                caller,
                subject,
                screening.item_state(item),
                screening.questions(item.action),
            )
        except ProviderRequestError as exc:
            log.warning("pillar suggestion screening failed", suggestion_id=item.id, error=str(exc))
            return None
        confidence = yes_confidence(answer["answers"]["apply"])
        state = screened_state(confidence)
        await pillar_page_suggestions.update(
            db, site_id, item.id, PillarPageSuggestionChanges(state=state, confidence=confidence)
        )
        return state

    async def _with_pages(
        self, db: AsyncSession, site_id: str, records: list[PillarPageSuggestionRecord]
    ) -> list[PillarPageSuggestionRecord]:
        ids = {p for r in records for p in r.member_page_ids}
        ids |= {r.covering_page_id for r in records if r.covering_page_id}
        pages = {p.id: p for p in await site_pages.list_by_ids(db, site_id, list(ids))}
        enriched = []
        for r in records:
            covering = pages.get(r.covering_page_id)
            enriched.append(
                r.model_copy(
                    update={
                        "covering_url": covering.url if covering else None,
                        "members": [
                            PillarMember(id=p, url=pages[p].url, title=pages[p].title)
                            for p in r.member_page_ids
                            if p in pages
                        ],
                    }
                )
            )
        return enriched


pillar_page_suggestion_service = PillarPageSuggestionService()
