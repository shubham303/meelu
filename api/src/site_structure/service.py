from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.context import tenant_names
from src.agent.workspace import workspace_tables
from src.core.logging import get_logger
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.credits.service import InsufficientCreditsError
from src.providers.errors import NoProviderError, ProviderRequestError
from src.providers.json_data_extractor.service import json_data_extractor
from src.providers.registry import Caller
from src.site_pages.llm_extraction.repository import site_page_llm_extractions
from src.site_pages.repositories.chunks import site_chunks
from src.site_pages.repositories.links import site_page_links
from src.site_pages.repositories.pages import site_pages
from src.site_structure import hierarchy, ranking, review, screening
from src.site_structure.constants import HIERARCHY_TYPES, REMOVAL_REGION
from src.site_structure.page_facts import ranking_facts_service
from src.site_structure.pillars.service import pillar_page_suggestion_service
from src.site_structure.repository import link_suggestions, structure_jobs
from src.site_structure.schemas import (
    EdgeFacts,
    HierarchyPage,
    HierarchyRequest,
    HierarchyResult,
    LinkSuggestionChanges,
    LinkSuggestionCreateRequest,
    LinkSuggestionFilter,
    LinkSuggestionRecord,
    LinkSuggestionSummaryResponse,
    LinkSuggestionUpdateRequest,
    MentionsRequest,
    MentionsResult,
    NewLinkSuggestion,
    RankRequest,
    RankResult,
    ReconcileResult,
    RemovalsRequest,
    RemovalsResult,
    ReviewBatch,
    ReviewInputsRequest,
    ReviewItem,
    ReviewResult,
    ScreeningInput,
    ScreenRequest,
    ScreenResult,
    StructureJobCreateRequest,
    StructureJobRecord,
    StructureJobUpdateRequest,
    VerdictRequest,
    WorkspaceEdge,
)

log = get_logger("site_structure.service")

NOT_FOUND = "No such link suggestion on this website."

JOB_NOT_FOUND = "No such structure job on this website."

REMOVAL_REASON = "The link does not serve the reader here."

FROM_TEXT_CHARS = 3000


class LinkSuggestionService:
    async def reconcile(self, db: AsyncSession, site_id: str) -> ReconcileResult:
        removed = await self._delete_edges(db, site_id, "create", linked=True)
        removed += await self._delete_edges(db, site_id, "delete", linked=False)
        gone = await site_pages.gone_ids(db, site_id)
        removed += await link_suggestions.delete_touching_pages(db, site_id, list(gone))
        pillars_reconciled = await pillar_page_suggestion_service.reconcile(db, site_id)
        return ReconcileResult(
            done=pillars_reconciled.done, stale=pillars_reconciled.stale, removed=removed
        )

    async def list_suggestions(
        self,
        db: AsyncSession,
        site_id: str,
        filters: LinkSuggestionFilter,
        paging: PaginationParams,
    ) -> PaginatedApiResponse[LinkSuggestionRecord]:
        page_ids_any = None
        if filters.url:
            page_ids_any = await site_pages.ids_by_url_substring(db, site_id, filters.url)
            if not page_ids_any:
                return PaginatedApiResponse[LinkSuggestionRecord](
                    data=[],
                    pagination=PaginationService.build_pagination_meta(
                        0, paging.page, paging.page_size
                    ),
                )
        page = await link_suggestions.list(db, site_id, filters, paging, page_ids_any)
        return PaginatedApiResponse[LinkSuggestionRecord](
            data=await self._decorate(db, site_id, page.data), pagination=page.pagination
        )

    async def get_suggestion(
        self, db: AsyncSession, site_id: str, suggestion_id: str
    ) -> LinkSuggestionRecord:
        found = await link_suggestions.get(db, site_id, suggestion_id)
        if found is None:
            raise HTTPException(404, NOT_FOUND)
        return await self._decorate_one(db, site_id, found)

    async def resolve_page_id(
        self, db: AsyncSession, site_id: str, page_id: str | None, url: str | None, end: str
    ) -> str:
        if page_id:
            if not await site_pages.exists(db, site_id, page_id):
                raise HTTPException(404, f"No page {page_id} on this website.")
            return page_id
        target = (url or "").strip()
        if not target:
            raise HTTPException(
                400, f"A suggestion needs a {end} page: send {end}PageId or {end}Url."
            )
        found = await site_pages.id_by_url(db, site_id, target)
        if not found:
            raise HTTPException(404, f"No page on record at {target}.")
        return found

    async def require_chunk_on_page(
        self, db: AsyncSession, site_id: str, chunk_id: str, page_id: str
    ) -> None:
        owner = await site_chunks.page_id_of(db, site_id, chunk_id)
        if owner is None:
            raise HTTPException(404, f"No chunk {chunk_id} on this website.")
        if owner != page_id:
            raise HTTPException(400, "The chunk must belong to the page the link goes from.")

    async def create_suggestion(
        self, db: AsyncSession, user_id: str, site_id: str, body: LinkSuggestionCreateRequest
    ) -> LinkSuggestionRecord:
        await structure_job_service.get_job(db, site_id, body.job_id)
        from_page_id = await self.resolve_page_id(
            db, site_id, body.from_page_id, body.from_url, "from"
        )
        to_page_id = await self.resolve_page_id(db, site_id, body.to_page_id, body.to_url, "to")
        if from_page_id == to_page_id:
            raise HTTPException(400, "A link cannot go from a page to itself.")
        if body.from_chunk_id:
            await self.require_chunk_on_page(db, site_id, body.from_chunk_id, from_page_id)
        pair = (from_page_id, to_page_id)
        linked = pair in await site_page_links.existing_pairs(db, site_id, [pair])
        if body.action == "create" and linked and body.state != "user_rejected":
            raise HTTPException(409, "That link already exists on the site; nothing to add.")
        if body.action != "create" and not linked:
            raise HTTPException(
                400, f'A "{body.action}" suggestion needs a link the crawl found; there is none.'
            )
        clash = await link_suggestions.find_edge(db, site_id, from_page_id, to_page_id, body.action)
        if clash is not None:
            raise HTTPException(
                409,
                f'A "{body.action}" suggestion for that link already exists ({clash.id}, {clash.state}).',
            )
        created = await link_suggestions.create(
            db, user_id, site_id, body.to_new(from_page_id, to_page_id)
        )
        return await self._decorate_one(db, site_id, created)

    async def update_suggestion(
        self, db: AsyncSession, site_id: str, suggestion_id: str, body: LinkSuggestionUpdateRequest
    ) -> LinkSuggestionRecord:
        if body.from_chunk_id:
            current = await self.get_suggestion(db, site_id, suggestion_id)
            await self.require_chunk_on_page(db, site_id, body.from_chunk_id, current.from_page_id)
        updated = await link_suggestions.update(db, site_id, suggestion_id, body.to_changes())
        if updated is None:
            raise HTTPException(404, NOT_FOUND)
        return await self._decorate_one(db, site_id, updated)

    async def delete_suggestion(
        self, db: AsyncSession, site_id: str, suggestion_id: str
    ) -> LinkSuggestionRecord:
        found = await self.get_suggestion(db, site_id, suggestion_id)
        await link_suggestions.delete(db, site_id, found.id)
        return found

    async def summary(self, db: AsyncSession, site_id: str) -> LinkSuggestionSummaryResponse:
        return await link_suggestions.summary(db, site_id)

    async def screen_suggestions(
        self, db: AsyncSession, user_id: str, site_id: str, body: ScreenRequest
    ) -> ScreenResult:
        caller = Caller(user_id=user_id, site_id=site_id)
        items = await self._inputs(db, site_id, body.job_id, body.ids, body.limit, True)
        result = ScreenResult()
        for item in items:
            try:
                confidence = await self._screen_one(db, caller, item, body.question)
            except (NoProviderError, InsufficientCreditsError) as exc:
                result.stopped = str(exc)
                break
            if confidence is None:
                result.failed += 1
                continue
            result.screened += 1
            if screening.rejected(confidence):
                result.llm_rejected += 1
            else:
                result.passed += 1
        return result

    async def review_inputs(
        self, db: AsyncSession, site_id: str, body: ReviewInputsRequest
    ) -> ReviewBatch:
        items = await self._inputs(db, site_id, body.job_id, body.ids, body.limit, False)
        return ReviewBatch(
            instructions=review.INSTRUCTIONS.format(prompt=body.prompt),
            schema=review.SCHEMA,
            items=[ReviewItem(id=item.id, state=review.review_state(item)) for item in items],
        )

    async def apply_verdicts(
        self, db: AsyncSession, site_id: str, body: VerdictRequest
    ) -> ReviewResult:
        result = ReviewResult()
        for given in body.verdicts:
            if given.verdict not in review.VERDICTS:
                result.failed += 1
                continue
            updated = await link_suggestions.update(
                db, site_id, given.id, LinkSuggestionChanges(state=given.verdict)
            )
            if updated is None:
                result.failed += 1
                continue
            result.reviewed += 1
            setattr(result, given.verdict, getattr(result, given.verdict) + 1)
        return result

    async def rank_suggestions(
        self, db: AsyncSession, site_id: str, body: RankRequest
    ) -> RankResult:
        candidates = await link_suggestions.open_candidates(db, site_id)
        if not candidates:
            return RankResult()
        pages, site = await ranking_facts_service.page_facts(db, site_id)
        params = ranking.RankParams(
            max_per_target=body.max_per_target, target_discount=body.target_discount
        )
        additions = [c for c in candidates if c.action == "create"]
        removals = [c for c in candidates if c.action == "delete"]
        ranked = ranking.rank_link_suggestions(additions, pages, site, params)
        ranked += ranking.rank_link_removals(removals, pages, params)
        scores = {r.candidate.suggestion_id: r.score for r in ranked}
        cut = {r.candidate.suggestion_id for r in ranked if not r.kept}
        await link_suggestions.update_scores(db, site_id, scores, cut)
        return RankResult(scored=len(ranked), kept=len(ranked) - len(cut), llm_rejected=len(cut))

    async def propose_unlinked_mentions(
        self, db: AsyncSession, user_id: str, site_id: str, body: MentionsRequest
    ) -> MentionsResult:
        await structure_job_service.get_job(db, site_id, body.job_id)
        known = await site_pages.existing_ids(db, site_id, body.to_ids)
        missing = [p for p in body.to_ids if p not in known]
        if missing:
            raise HTTPException(404, f"No page on this website with id {', '.join(missing)}.")
        result = MentionsResult()
        for to_page_id in body.to_ids:
            linking = await site_page_links.src_ids_linking_to(db, site_id, to_page_id)
            excluded = {to_page_id} | linking
            rows: dict[tuple[str, str], NewLinkSuggestion] = {}
            for phrase in body.phrases:
                for chunk_id, page_id in await site_chunks.search_text(
                    db, site_id, phrase, excluded, body.limit_per_target
                ):
                    key = (page_id, to_page_id)
                    if key in rows:
                        continue
                    rows[key] = NewLinkSuggestion(
                        job_id=body.job_id,
                        from_page_id=page_id,
                        to_page_id=to_page_id,
                        from_chunk_id=chunk_id,
                        suggestion=f'The passage mentions "{phrase}" without linking to the page about it; link the mention.',
                    )
            if not rows:
                result.targets_without_match.append(to_page_id)
                continue
            inserted = await link_suggestions.create_many(db, user_id, site_id, list(rows.values()))
            result.inserted += inserted
            result.skipped += len(rows) - inserted
        return result

    async def propose_hierarchy_links(
        self, db: AsyncSession, user_id: str, site_id: str, body: HierarchyRequest
    ) -> HierarchyResult:
        await structure_job_service.get_job(db, site_id, body.job_id)
        pages = await self._hierarchy_pages(db, site_id)
        rows, home, hubs = hierarchy.hierarchy_edges(pages, body.job_id)
        linked = await site_page_links.pairs_among(db, site_id, [p.id for p in pages])
        rows = [r for r in rows if (r.from_page_id, r.to_page_id) not in linked]
        inserted = await link_suggestions.create_many(db, user_id, site_id, rows)
        return HierarchyResult(
            inserted=inserted, skipped=len(rows) - inserted, home_found=home is not None, hubs=hubs
        )

    async def propose_link_removals(
        self, db: AsyncSession, user_id: str, site_id: str, body: RemovalsRequest
    ) -> RemovalsResult:
        await structure_job_service.get_job(db, site_id, body.job_id)
        _, schema = tenant_names(user_id)
        try:
            edges = self._workspace_edges(
                await workspace_tables.rows(db, schema, body.source_table), body.source_table
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        result = RemovalsResult(read=len(edges))
        pairs = list(
            {(e.from_page_id, e.to_page_id) for e in edges if e.from_page_id != e.to_page_id}
        )
        facts = await self._edge_facts(db, site_id, pairs)
        candidates: list[tuple[WorkspaceEdge, EdgeFacts]] = []
        seen: set[tuple[str, str]] = set()
        for edge in edges:
            key = (edge.from_page_id, edge.to_page_id)
            fact = facts.get(key)
            if fact is None or key in seen:
                continue
            seen.add(key)
            if fact.region != REMOVAL_REGION:
                result.not_body_links += 1
                continue
            if fact.to_is_hub:
                result.to_hub_or_home += 1
                continue
            if fact.to_inlinks <= 1:
                result.last_inlink += 1
                continue
            candidates.append((edge, fact))
        anchors = await site_chunks.first_ids_containing(
            db, site_id, [(f.from_page_id, (f.anchor or "").strip()) for _, f in candidates]
        )
        kept = [
            (edge, fact, anchors.get((fact.from_page_id, (fact.anchor or "").strip())))
            for edge, fact in candidates
        ]
        relevance = await self._edge_relevance(
            db, site_id, [(f.from_page_id, f.to_page_id, c) for _, f, c in kept]
        )
        rows: list[NewLinkSuggestion] = []
        for edge, fact, chunk_id in kept:
            anchor = f'"{fact.anchor}" ' if fact.anchor else ""
            rows.append(
                NewLinkSuggestion(
                    job_id=body.job_id,
                    from_page_id=fact.from_page_id,
                    to_page_id=fact.to_page_id,
                    from_chunk_id=chunk_id,
                    action="delete",
                    suggestion=f"Remove the link {anchor}to {fact.to_url}. {edge.reason or REMOVAL_REASON}",
                    search_score=relevance.get((fact.from_page_id, fact.to_page_id)),
                )
            )
        result.inserted = await link_suggestions.create_many(db, user_id, site_id, rows)
        result.skipped = len(rows) - result.inserted
        return result

    async def _delete_edges(self, db: AsyncSession, site_id: str, action: str, linked: bool) -> int:
        edges = await link_suggestions.list_undone_edges(db, site_id, action)
        if not edges:
            return 0
        existing = await site_page_links.existing_pairs(
            db, site_id, list({(src, dst) for _, src, dst in edges})
        )
        doomed = [sid for sid, src, dst in edges if ((src, dst) in existing) == linked]
        return await link_suggestions.delete_by_ids(db, site_id, doomed)

    async def _decorate(
        self, db: AsyncSession, site_id: str, records: list[LinkSuggestionRecord]
    ) -> list[LinkSuggestionRecord]:
        if not records:
            return []
        urls = await site_pages.urls_by_ids(
            db, site_id, list({p for r in records for p in (r.from_page_id, r.to_page_id)})
        )
        chunks = {
            c.id: c
            for c in await site_chunks.list_by_ids(
                db, site_id, list({r.from_chunk_id for r in records if r.from_chunk_id})
            )
        }
        decorated: list[LinkSuggestionRecord] = []
        for record in records:
            chunk = chunks.get(record.from_chunk_id) if record.from_chunk_id else None
            decorated.append(
                record.model_copy(
                    update={
                        "from_url": urls.get(record.from_page_id),
                        "to_url": urls.get(record.to_page_id),
                        "from_chunk_heading": chunk.heading_path if chunk else None,
                        "from_chunk_ordinal": chunk.ordinal if chunk else None,
                    }
                )
            )
        return decorated

    async def _decorate_one(
        self, db: AsyncSession, site_id: str, record: LinkSuggestionRecord
    ) -> LinkSuggestionRecord:
        return (await self._decorate(db, site_id, [record]))[0]

    async def _inputs(
        self,
        db: AsyncSession,
        site_id: str,
        job_id: str | None,
        ids: list[str] | None,
        limit: int,
        unscreened_only: bool,
    ) -> list[ScreeningInput]:
        rows = await link_suggestions.list_for_review(
            db, site_id, job_id, ids, limit, unscreened_only
        )
        if not rows:
            return []
        from_ids = list({r.from_page_id for r in rows})
        to_ids = list({r.to_page_id for r in rows})
        sources = {
            p.id: p
            for p in await site_pages.list_by_ids(db, site_id, from_ids, body_chars=FROM_TEXT_CHARS)
        }
        targets = {p.id: p for p in await site_pages.list_by_ids(db, site_id, to_ids)}
        chunks = {
            c.id: c.text
            for c in await site_chunks.list_by_ids(
                db, site_id, list({r.from_chunk_id for r in rows if r.from_chunk_id})
            )
        }
        types = await site_page_llm_extractions.page_types_by_page_ids(db, site_id, to_ids)
        anchors: dict[tuple[str, str], str | None] = {}
        for link in await site_page_links.list_between(
            db, site_id, from_ids, to_ids, region=REMOVAL_REGION
        ):
            if link.dst_page_id is not None:
                anchors.setdefault((link.src_page_id, link.dst_page_id), link.anchor)
        items: list[ScreeningInput] = []
        for row in rows:
            source = sources.get(row.from_page_id)
            target = targets.get(row.to_page_id)
            if source is None or target is None:
                continue
            chunk_text = chunks.get(row.from_chunk_id) if row.from_chunk_id else None
            items.append(
                ScreeningInput(
                    id=row.id,
                    action=row.action,
                    suggestion=row.suggestion,
                    from_url=source.url,
                    from_title=source.title,
                    from_content_hash=source.content_hash,
                    from_text=chunk_text or source.body_text or "",
                    to_url=target.url,
                    to_title=target.title,
                    to_meta_description=target.meta_description,
                    to_h1=list(target.h1 or []),
                    to_page_type=types.get(row.to_page_id),
                    to_content_hash=target.content_hash,
                    anchor=anchors.get((row.from_page_id, row.to_page_id)),
                )
            )
        return items

    async def _screen_one(
        self, db: AsyncSession, caller: Caller, item: ScreeningInput, question: str | None
    ) -> float | None:
        subject = {
            "suggestion_id": item.id,
            "from_hash": item.from_content_hash,
            "to_hash": item.to_content_hash,
            "question": question,
        }
        try:
            result = await json_data_extractor.decide(
                db,
                caller,
                subject,
                screening.screening_state(item),
                screening.questions(item.action, question),
            )
        except ProviderRequestError as exc:
            log.warning("link suggestion screening failed", suggestion_id=item.id, error=str(exc))
            return None
        confidence = screening.yes_confidence(result["answers"]["apply"])
        await link_suggestions.update(
            db,
            caller.site_id or "",
            item.id,
            LinkSuggestionChanges(
                state="llm_rejected" if screening.rejected(confidence) else "draft",
                confidence=confidence,
            ),
        )
        return confidence

    async def _hierarchy_pages(self, db: AsyncSession, site_id: str) -> list[HierarchyPage]:
        pages = await site_pages.list_not_gone(db, site_id)
        types = await site_page_llm_extractions.page_types_by_page_ids(
            db, site_id, [p.id for p in pages]
        )
        found: list[HierarchyPage] = []
        for page in pages:
            home = hierarchy.is_home(page.url)
            page_type = types.get(page.id)
            if home or page_type in HIERARCHY_TYPES:
                found.append(
                    HierarchyPage(id=page.id, url=page.url, is_home=home, page_type=page_type)
                )
        return found

    def _workspace_edges(self, rows: list[dict[str, Any]], table: str) -> list[WorkspaceEdge]:
        edges: list[WorkspaceEdge] = []
        for row in rows:
            if not row.get("from_page_id") or not row.get("to_page_id"):
                raise ValueError(
                    f"{table} needs from_page_id and to_page_id columns (reason is optional)."
                )
            reason = row.get("reason")
            edges.append(
                WorkspaceEdge(
                    from_page_id=str(row["from_page_id"]),
                    to_page_id=str(row["to_page_id"]),
                    reason=None if reason is None else str(reason),
                )
            )
        return edges

    async def _edge_facts(
        self, db: AsyncSession, site_id: str, pairs: list[tuple[str, str]]
    ) -> dict[tuple[str, str], EdgeFacts]:
        if not pairs:
            return {}
        wanted = set(pairs)
        links = await site_page_links.list_between(
            db, site_id, [p[0] for p in pairs], [p[1] for p in pairs]
        )
        chosen: dict[tuple[str, str], Any] = {}
        for link in sorted(links, key=lambda k: k.region != REMOVAL_REGION):
            if link.dst_page_id is None:
                continue
            key = (link.src_page_id, link.dst_page_id)
            if key in wanted and key not in chosen:
                chosen[key] = link
        dst_ids = list({k[1] for k in chosen})
        urls = await site_pages.urls_by_ids(db, site_id, dst_ids)
        types = await site_page_llm_extractions.page_types_by_page_ids(db, site_id, dst_ids)
        inlinks = await site_page_links.inlink_counts(db, site_id, dst_ids)
        facts: dict[tuple[str, str], EdgeFacts] = {}
        for key, link in chosen.items():
            to_url = urls.get(key[1])
            if to_url is None:
                continue
            facts[key] = EdgeFacts(
                from_page_id=key[0],
                to_page_id=key[1],
                region=link.region,
                anchor=link.anchor,
                to_url=to_url,
                to_inlinks=inlinks.get(key[1], 0),
                to_is_hub=hierarchy.is_home(to_url) or types.get(key[1]) == "hub",
            )
        return facts

    async def _edge_relevance(
        self, db: AsyncSession, site_id: str, edges: list[tuple[str, str, str | None]]
    ) -> dict[tuple[str, str], float]:
        by_chunk = await site_chunks.chunk_page_similarities(
            db, site_id, [(chunk_id, dst) for _, dst, chunk_id in edges if chunk_id]
        )
        relevance: dict[tuple[str, str], float] = {}
        fallback: list[tuple[str, str]] = []
        for src, dst, chunk_id in edges:
            found = by_chunk.get((chunk_id, dst)) if chunk_id else None
            if found is None:
                fallback.append((src, dst))
            else:
                relevance[(src, dst)] = found
        relevance.update(await site_chunks.page_similarities(db, site_id, fallback))
        return relevance


link_suggestion_service = LinkSuggestionService()


class StructureJobService:
    async def start_job(
        self, db: AsyncSession, user_id: str, site_id: str, body: StructureJobCreateRequest
    ) -> tuple[StructureJobRecord, ReconcileResult]:
        reconciled = await link_suggestion_service.reconcile(db, site_id)
        job = await structure_jobs.create(db, user_id, site_id, body.prompt)
        return job, reconciled

    async def get_job(self, db: AsyncSession, site_id: str, job_id: str) -> StructureJobRecord:
        found = await structure_jobs.get(db, site_id, job_id)
        if found is None:
            raise HTTPException(404, JOB_NOT_FOUND)
        return found

    async def list_jobs(
        self, db: AsyncSession, site_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[StructureJobRecord]:
        return await structure_jobs.list(db, site_id, paging)

    async def finish_job(
        self, db: AsyncSession, site_id: str, job_id: str, body: StructureJobUpdateRequest
    ) -> StructureJobRecord:
        updated = await structure_jobs.update_status(db, site_id, job_id, body.status)
        if updated is None:
            raise HTTPException(404, JOB_NOT_FOUND)
        return updated


structure_job_service = StructureJobService()
