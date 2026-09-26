from statistics import fmean
from typing import Any

import numpy as np
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.context import tenant_names
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
from src.site_structure import ranking
from src.site_structure.constants import (
    OPEN_STATES,
    PILLAR_COVERED,
    PILLAR_DONE_FRACTION,
    PILLAR_OVERLAP,
    PILLAR_PARTLY_COVERED,
    PILLAR_STALE_FRACTION,
    STRUCTURAL_TYPES,
)
from src.site_structure.page_facts import ranking_facts_service
from src.site_structure.pillars import clustering, review, screening
from src.site_structure.pillars.clustering import PagePoint
from src.site_structure.pillars.repository import pillar_page_suggestions
from src.site_structure.repository import structure_jobs
from src.site_structure.review import VERDICTS
from src.site_structure.schemas import (
    NewPillarPageSuggestion,
    PillarMember,
    PillarPageSuggestionChanges,
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
    RankResult,
    ReconcileResult,
    ReviewBatch,
    ReviewItem,
    ReviewResult,
    ScreenResult,
    WorkspaceGroup,
)
from src.site_structure.screening import rejected, yes_confidence

log = get_logger("site_structure.pillars.service")

NOT_FOUND = "No such pillar page suggestion on this website."

STRUCTURAL_SHARE = 0.5


def _suggestion_text(
    action: str, topic: str, members: list[PagePoint], covering_url: str | None
) -> str:
    titles = "; ".join((m.title or m.url) for m in members[:8])
    more = f" and {len(members) - 8} more" if len(members) > 8 else ""
    if action == "expand":
        return (
            f"Expand {covering_url} into the hub for {topic}: introduce the topic and link every "
            f"page on it ({titles}{more}), and have those pages link back."
        )
    return (
        f"Create a pillar page about {topic} that introduces the topic and links each page on it "
        f"({titles}{more}); have those pages link back to it."
    )


class PillarPageSuggestionService:
    async def get_suggestion(
        self, db: AsyncSession, site_id: str, suggestion_id: str
    ) -> PillarPageSuggestionRecord:
        found = await pillar_page_suggestions.get(db, site_id, suggestion_id)
        if found is None:
            raise HTTPException(404, NOT_FOUND)
        return (await self._decorate(db, site_id, [found]))[0]

    async def list_suggestions(
        self,
        db: AsyncSession,
        site_id: str,
        filters: PillarPageSuggestionFilter,
        paging: PaginationParams,
    ) -> PaginatedApiResponse[PillarPageSuggestionRecord]:
        page = await pillar_page_suggestions.list(db, site_id, filters, paging)
        return PaginatedApiResponse[PillarPageSuggestionRecord](
            data=await self._decorate(db, site_id, page.data), pagination=page.pagination
        )

    async def update_suggestion(
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
        return (await self._decorate(db, site_id, [updated]))[0]

    async def delete_suggestion(
        self, db: AsyncSession, site_id: str, suggestion_id: str
    ) -> PillarPageSuggestionRecord:
        found = await self.get_suggestion(db, site_id, suggestion_id)
        await pillar_page_suggestions.delete(db, site_id, found.id)
        return found

    async def summary(self, db: AsyncSession, site_id: str) -> PillarPageSuggestionSummaryResponse:
        return await pillar_page_suggestions.summary(db, site_id)

    async def propose_pillar_pages(
        self, db: AsyncSession, user_id: str, site_id: str, body: PillarsRequest
    ) -> PillarsResult:
        job = await structure_jobs.get(db, site_id, body.job_id)
        if job is None:
            raise HTTPException(404, "No such structure job on this website.")
        live_pages = await site_pages.list_not_gone(db, site_id)
        points = await self._page_points(db, site_id, live_pages)
        by_id = {p.id: p for p in points}
        vectors = {p.id: p.vector for p in points}
        if body.source_table:
            _, schema = tenant_names(user_id)
            try:
                groups = self._workspace_groups(
                    await workspace_tables.rows(db, schema, body.source_table), body.source_table
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
        links = await site_page_links.adjacency(db, site_id)
        live = {p.id for p in live_pages}
        open_sets = await pillar_page_suggestions.member_sets(db, site_id, OPEN_STATES + ("done",))
        rejected_sets = await pillar_page_suggestions.member_sets(db, site_id, ("user_rejected",))
        kept: list[tuple[list[str], NewPillarPageSuggestion]] = []
        for group in groups:
            members = [p for p in dict.fromkeys(group.page_ids) if p in live]
            if len(members) < body.min_size:
                result.too_small += 1
                continue
            cohesion = clustering.cohesion(members, vectors)
            if cohesion < body.min_cohesion:
                result.too_loose += 1
                continue
            known = [by_id[m] for m in members if m in by_id]
            if clustering.structural_share(known, STRUCTURAL_TYPES) > STRUCTURAL_SHARE:
                result.structural += 1
                continue
            cover = clustering.coverage(members, vectors, links)
            if cover.score >= PILLAR_COVERED:
                result.covered += 1
                continue
            if any(clustering.overlap(members, s) >= PILLAR_OVERLAP for _, s in rejected_sets):
                result.overlaps_rejected += 1
                continue
            if any(clustering.overlap(members, s) >= PILLAR_OVERLAP for _, s in open_sets) or any(
                clustering.overlap(members, s) >= PILLAR_OVERLAP for s, _ in kept
            ):
                result.overlaps_open += 1
                continue
            action = (
                "expand" if cover.score >= PILLAR_PARTLY_COVERED and cover.page_id else "create"
            )
            covering = cover.page_id if action == "expand" else None
            covering_url = by_id[covering].url if covering and covering in by_id else None
            topic = group.topic or clustering.topic_for(known)
            kept.append(
                (
                    members,
                    NewPillarPageSuggestion(
                        job_id=body.job_id,
                        action=action,
                        topic=topic,
                        member_page_ids=members,
                        covering_page_id=covering,
                        suggestion=_suggestion_text(action, topic, known, covering_url),
                        search_score=cohesion,
                    ),
                )
            )
        result.inserted = await pillar_page_suggestions.create_many(
            db, user_id, site_id, [row for _, row in kept]
        )
        return result

    async def screen_suggestions(
        self, db: AsyncSession, user_id: str, site_id: str, body: PillarScreenRequest
    ) -> ScreenResult:
        caller = Caller(user_id=user_id, site_id=site_id)
        items = await self._review_inputs(db, site_id, body.job_id, body.ids, body.limit, True)
        result = ScreenResult()
        for item in items:
            try:
                confidence = await self._screen_one(db, caller, item)
            except (NoProviderError, InsufficientCreditsError) as exc:
                result.stopped = str(exc)
                break
            if confidence is None:
                result.failed += 1
                continue
            result.screened += 1
            if rejected(confidence):
                result.llm_rejected += 1
            else:
                result.passed += 1
        return result

    async def review_inputs(
        self, db: AsyncSession, site_id: str, body: PillarReviewInputsRequest
    ) -> ReviewBatch:
        items = await self._review_inputs(db, site_id, body.job_id, body.ids, body.limit, False)
        return ReviewBatch(
            instructions=review.INSTRUCTIONS.format(prompt=body.prompt),
            schema=review.SCHEMA,
            items=[ReviewItem(id=item.id, state=review.review_state(item)) for item in items],
        )

    async def apply_verdicts(
        self, db: AsyncSession, site_id: str, body: PillarVerdictRequest
    ) -> ReviewResult:
        result = ReviewResult()
        for given in body.verdicts:
            if given.verdict not in VERDICTS:
                result.failed += 1
                continue
            changes = PillarPageSuggestionChanges(state=given.verdict)
            if given.verdict == "ready":
                if given.title:
                    changes.topic = given.title.strip()
                if given.suggestion:
                    changes.suggestion = given.suggestion.strip()
            updated = await pillar_page_suggestions.update(db, site_id, given.id, changes)
            if updated is None:
                result.failed += 1
                continue
            result.reviewed += 1
            setattr(result, given.verdict, getattr(result, given.verdict) + 1)
        return result

    async def rank_suggestions(
        self, db: AsyncSession, site_id: str, body: PillarRankRequest
    ) -> RankResult:
        rows = await pillar_page_suggestions.open_rows(db, site_id)
        if not rows:
            return RankResult()
        pages, site = await ranking_facts_service.page_facts(db, site_id)
        sizes = sorted(len(r.member_page_ids) for r in rows)
        scores: dict[str, float] = {}
        for row in rows:
            members = [pages[m] for m in row.member_page_ids if m in pages]
            authority = (
                fmean(ranking.percentile(site.inlinks, m.inlinks) for m in members)
                if members
                else 0.0
            )
            factors = [
                ranking.percentile(sizes, len(row.member_page_ids)),
                authority,
                0.5 if row.covering_page_id else 1.0,
            ]
            score = (row.search_score if row.search_score is not None else 1.0) * fmean(factors)
            if row.confidence is not None:
                score *= 0.5 + 0.5 * row.confidence
            scores[row.id] = score
        ordered = sorted(scores, key=lambda sid: -scores[sid])
        cut = set(ordered[body.budget :])
        await pillar_page_suggestions.update_scores(db, site_id, scores, cut)
        return RankResult(scored=len(rows), kept=len(rows) - len(cut), llm_rejected=len(cut))

    async def reconcile(self, db: AsyncSession, site_id: str) -> ReconcileResult:
        rows = await pillar_page_suggestions.open_rows(db, site_id)
        if not rows:
            return ReconcileResult()
        live = {p.id for p in await site_pages.list_not_gone(db, site_id)}
        links = await site_page_links.adjacency(db, site_id)
        changed_at = await site_pages.changed_at_by_id(db, site_id)
        done: list[str] = []
        stale: list[str] = []
        for row in rows:
            members = set(row.member_page_ids)
            if not members:
                continue
            alive = members & live
            if len(alive) / len(members) < PILLAR_STALE_FRACTION:
                stale.append(row.id)
                continue
            covered = max(
                (
                    len(targets & alive)
                    for src, targets in links.items()
                    if src in changed_at and changed_at[src] > row.created_at
                ),
                default=0,
            )
            if covered / len(alive) >= PILLAR_DONE_FRACTION:
                done.append(row.id)
        await pillar_page_suggestions.set_states(db, site_id, done, "done")
        await pillar_page_suggestions.set_states(db, site_id, stale, "stale")
        return ReconcileResult(done=len(done), stale=len(stale))

    async def _decorate(
        self, db: AsyncSession, site_id: str, records: list[PillarPageSuggestionRecord]
    ) -> list[PillarPageSuggestionRecord]:
        if not records:
            return []
        ids = {p for r in records for p in r.member_page_ids}
        ids |= {r.covering_page_id for r in records if r.covering_page_id}
        pages = {p.id: p for p in await site_pages.list_by_ids(db, site_id, list(ids))}
        decorated: list[PillarPageSuggestionRecord] = []
        for record in records:
            covering = pages.get(record.covering_page_id) if record.covering_page_id else None
            decorated.append(
                record.model_copy(
                    update={
                        "covering_url": covering.url if covering else None,
                        "members": [
                            PillarMember(id=p, url=pages[p].url, title=pages[p].title)
                            for p in record.member_page_ids
                            if p in pages
                        ],
                    }
                )
            )
        return decorated

    async def _page_points(
        self, db: AsyncSession, site_id: str, live_pages: list[SitePageBrief]
    ) -> list[PagePoint]:
        vectors = await site_chunks.page_vectors(db, site_id)
        types = await site_page_llm_extractions.page_types_by_page_ids(db, site_id)
        return [
            PagePoint(
                id=p.id,
                url=p.url,
                title=p.title,
                page_type=types.get(p.id),
                inlinks=p.inlinks,
                vector=np.asarray(vectors[p.id], dtype=float),
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
        job_id: str | None,
        ids: list[str] | None,
        limit: int,
        unscreened_only: bool,
    ) -> list[PillarReviewInput]:
        rows = await pillar_page_suggestions.list_for_review(
            db, site_id, job_id, ids, limit, unscreened_only
        )
        if not rows:
            return []
        member_ids = {p for r in rows for p in r.member_page_ids}
        wanted = member_ids | {r.covering_page_id for r in rows if r.covering_page_id}
        pages = {p.id: p for p in await site_pages.list_by_ids(db, site_id, list(wanted))}
        types = await site_page_llm_extractions.page_types_by_page_ids(
            db, site_id, list(member_ids)
        )
        items: list[PillarReviewInput] = []
        for row in rows:
            covering = pages.get(row.covering_page_id) if row.covering_page_id else None
            items.append(
                PillarReviewInput(
                    id=row.id,
                    action=row.action,
                    topic=row.topic,
                    suggestion=row.suggestion,
                    search_score=row.search_score,
                    covering_url=covering.url if covering else None,
                    covering_title=covering.title if covering else None,
                    members=[
                        {
                            "url": pages[m].url,
                            "title": pages[m].title or "",
                            "meta_description": pages[m].meta_description or "",
                            "inlinks": pages[m].inlinks,
                            "page_type": types.get(m),
                        }
                        for m in dict.fromkeys(row.member_page_ids)
                        if m in pages
                    ],
                )
            )
        return items

    async def _screen_one(
        self, db: AsyncSession, caller: Caller, item: PillarReviewInput
    ) -> float | None:
        subject = {"pillar_id": item.id, "members": sorted(m["url"] for m in item.members)}
        try:
            result = await json_data_extractor.decide(
                db,
                caller,
                subject,
                screening.screening_state(item),
                screening.questions(item.action),
            )
        except ProviderRequestError as exc:
            log.warning("pillar suggestion screening failed", suggestion_id=item.id, error=str(exc))
            return None
        confidence = yes_confidence(result["answers"]["apply"])
        await pillar_page_suggestions.update(
            db,
            caller.site_id or "",
            item.id,
            PillarPageSuggestionChanges(
                state="llm_rejected" if rejected(confidence) else "draft", confidence=confidence
            ),
        )
        return confidence


pillar_page_suggestion_service = PillarPageSuggestionService()
