from __future__ import annotations

from collections.abc import Iterator
from typing import Any
from urllib.parse import urlsplit

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.workspace import workspace_tables
from src.core.logging import get_logger
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.credits.service import InsufficientCreditsError
from src.embed_worker.settings import search_settings
from src.providers.errors import NoProviderError, ProviderRequestError
from src.providers.json_data_extractor.service import json_data_extractor
from src.providers.registry import Caller
from src.site_pages.llm_extraction.repository import site_page_llm_extractions
from src.site_pages.repositories.chunks import site_chunks
from src.site_pages.repositories.links import site_page_links
from src.site_pages.repositories.pages import site_pages
from src.site_pages.schemas.llm_extraction import extracted_details
from src.site_structure.constants import HIERARCHY_TYPES, REMOVAL_REGION, SuggestionState
from src.site_structure.jobs.service import structure_job_service
from src.site_structure.links import ranking, review, screening
from src.site_structure.links.repository import link_suggestions
from src.site_structure.links.schemas import (
    EdgeFacts,
    HierarchyPage,
    HierarchyRequest,
    HierarchyResult,
    LinkAction,
    LinkSuggestionChanges,
    LinkSuggestionCreateRequest,
    LinkSuggestionFilter,
    LinkSuggestionRecord,
    LinkSuggestionSummaryResponse,
    LinkSuggestionUpdateRequest,
    MentionsRequest,
    MentionsResult,
    NewLinkSuggestion,
    PairsRequest,
    PairsResult,
    RankRequest,
    ReconcileResult,
    RemovalsRequest,
    RemovalsResult,
    ReviewInputsRequest,
    ScreeningInput,
    ScreenRequest,
    VerdictRequest,
    WorkspaceEdge,
)
from src.site_structure.pipeline.page_facts import page_facts_service
from src.site_structure.pipeline.ranking import is_home, link_room
from src.site_structure.pipeline.schemas import (
    RankResult,
    ReviewBatch,
    ReviewItem,
    ReviewResult,
    ScreenResult,
)
from src.site_structure.pipeline.screening import screened_state, yes_confidence

log = get_logger("site_structure.links.service")

NOT_FOUND = "No such link suggestion on this website."

REMOVAL_REASON = "The link does not serve the reader here."

PAIR_REASON = "The passage covers what the target page is about."

FROM_TEXT_CHARS = 3000

HOME_TO_UTILITY = "The home page should give this utility page a way in."
BACK_TO_HOME = "This page should link back to the home page."
PARENT_TO_CHILD = "This section should list its child section {child}."
CHILD_TO_PARENT = "This section should link up to its parent section {parent}."


def path_of(url: str) -> str:
    return urlsplit(url).path.rstrip("/") or "/"


def parent_of(path: str) -> str:
    if path == "/":
        return ""
    head, _, _ = path.rpartition("/")
    return head or "/"


class LinkSuggestionService:
    async def get(self, db: AsyncSession, site_id: str, suggestion_id: str) -> LinkSuggestionRecord:
        found = await link_suggestions.get(db, site_id, suggestion_id)
        if found is None:
            raise HTTPException(404, NOT_FOUND)
        return (await self._with_pages(db, site_id, [found]))[0]

    async def list(
        self,
        db: AsyncSession,
        site_id: str,
        filters: LinkSuggestionFilter,
        paging: PaginationParams,
    ) -> PaginatedApiResponse[LinkSuggestionRecord]:
        from_page_ids = (
            set(await site_pages.ids_by_url_substring(db, site_id, filters.from_url))
            if filters.from_url
            else None
        )
        to_page_ids = (
            set(await site_pages.ids_by_url_substring(db, site_id, filters.to_url))
            if filters.to_url
            else None
        )
        either_page_ids = (
            set(await site_pages.ids_by_url_substring(db, site_id, filters.url))
            if filters.url
            else None
        )
        page = await link_suggestions.list(
            db, site_id, filters, paging, from_page_ids, to_page_ids, either_page_ids
        )
        page.data = await self._with_pages(db, site_id, page.data)
        return page

    async def summary(self, db: AsyncSession, site_id: str) -> LinkSuggestionSummaryResponse:
        return await link_suggestions.summary(db, site_id)

    async def create(
        self, db: AsyncSession, user_id: str, site_id: str, body: LinkSuggestionCreateRequest
    ) -> LinkSuggestionRecord:
        await structure_job_service.get(db, site_id, body.job_id)
        from_page_id = await self.resolve_page_id(
            db, site_id, body.from_page_id, body.from_url, "from"
        )
        to_page_id = await self.resolve_page_id(db, site_id, body.to_page_id, body.to_url, "to")
        if from_page_id == to_page_id:
            raise HTTPException(400, "A link cannot go from a page to itself.")
        if await site_pages.gone_ids(db, site_id, [from_page_id, to_page_id]):
            raise HTTPException(
                400, "Both pages must be live: one is gone, redirected or blocked by robots."
            )
        if body.from_chunk_id:
            await self.require_chunk_on_page(db, site_id, body.from_chunk_id, from_page_id)
        linked = bool(
            await site_page_links.existing_pairs(db, site_id, [(from_page_id, to_page_id)])
        )
        if (
            body.action is LinkAction.CREATE
            and linked
            and body.state is not SuggestionState.USER_REJECTED
        ):
            raise HTTPException(409, "That link already exists on the site; nothing to add.")
        if body.action is LinkAction.DELETE and not linked:
            raise HTTPException(
                400, 'A "delete" suggestion needs a link the crawl found; there is none.'
            )
        await self._require_no_clash(
            db, site_id, from_page_id, body.from_chunk_id, to_page_id, body.action
        )
        created = await link_suggestions.create(
            db, user_id, site_id, body.to_new(from_page_id, to_page_id)
        )
        return (await self._with_pages(db, site_id, [created]))[0]

    async def create_many(
        self, db: AsyncSession, user_id: str, site_id: str, rows: list[NewLinkSuggestion]
    ) -> int:
        for job_id in {r.job_id for r in rows}:
            await structure_job_service.get(db, site_id, job_id)
        rows = [r for r in rows if r.from_page_id != r.to_page_id]
        page_ids = list({p for r in rows for p in (r.from_page_id, r.to_page_id)})
        live = await site_pages.existing_ids(db, site_id, page_ids) - await site_pages.gone_ids(
            db, site_id, page_ids
        )
        rows = [r for r in rows if r.from_page_id in live and r.to_page_id in live]
        rows = await self._within_budget(db, site_id, rows)
        chunk_ids = [r.from_chunk_id for r in rows if r.from_chunk_id]
        chunk_pages = {
            c.id: c.page_id for c in await site_chunks.list_by_ids(db, site_id, chunk_ids)
        }
        rows = [
            r
            for r in rows
            if not r.from_chunk_id or chunk_pages.get(r.from_chunk_id) == r.from_page_id
        ]
        pairs = list({(r.from_page_id, r.to_page_id) for r in rows})
        linked = await site_page_links.existing_pairs(db, site_id, pairs)
        rows = [
            r
            for r in rows
            if (r.action is LinkAction.CREATE) != ((r.from_page_id, r.to_page_id) in linked)
        ]
        taken = await link_suggestions.edge_keys(db, site_id, pairs)
        taken_pairs = {(f, t, a) for f, t, a, _ in taken}
        fresh: list[NewLinkSuggestion] = []
        for r in rows:
            pair = (r.from_page_id, r.to_page_id, r.action)
            key = (*pair, r.from_chunk_id)
            if (r.from_chunk_id is None and pair in taken_pairs) or key in taken:
                continue
            taken.add(key)
            taken_pairs.add(pair)
            fresh.append(r)
        return await link_suggestions.create_many(db, user_id, site_id, fresh)

    async def update(
        self,
        db: AsyncSession,
        site_id: str,
        suggestion_id: str,
        body: LinkSuggestionUpdateRequest,
    ) -> LinkSuggestionRecord:
        if "from_chunk_id" in body.model_fields_set:
            current = await link_suggestions.get(db, site_id, suggestion_id)
            if current is None:
                raise HTTPException(404, NOT_FOUND)
            if body.from_chunk_id:
                await self.require_chunk_on_page(
                    db, site_id, body.from_chunk_id, current.from_page_id
                )
            if body.from_chunk_id != current.from_chunk_id:
                await self._require_no_clash(
                    db,
                    site_id,
                    current.from_page_id,
                    body.from_chunk_id,
                    current.to_page_id,
                    current.action,
                    exclude_id=current.id,
                )
        updated = await link_suggestions.update(db, site_id, suggestion_id, body.to_changes())
        if updated is None:
            raise HTTPException(404, NOT_FOUND)
        return (await self._with_pages(db, site_id, [updated]))[0]

    async def delete(
        self, db: AsyncSession, site_id: str, suggestion_id: str
    ) -> LinkSuggestionRecord:
        found = await link_suggestions.get(db, site_id, suggestion_id)
        if found is None:
            raise HTTPException(404, NOT_FOUND)
        await link_suggestions.delete(db, site_id, found.id)
        return found

    async def reconcile(self, db: AsyncSession, site_id: str) -> ReconcileResult:
        rows = await link_suggestions.list_for_site(db, site_id)
        pairs = {(r.from_page_id, r.to_page_id) for r in rows}
        linked = await site_page_links.existing_pairs(db, site_id, list(pairs))
        gone = await site_pages.gone_ids(db, site_id, list({p for pair in pairs for p in pair}))
        invalid = {
            r.id
            for r in rows
            if r.from_page_id in gone
            or r.to_page_id in gone
            or (r.action is LinkAction.CREATE and (r.from_page_id, r.to_page_id) in linked)
            or (r.action is LinkAction.DELETE and (r.from_page_id, r.to_page_id) not in linked)
        }
        return ReconcileResult(removed=await link_suggestions.delete_many(db, site_id, invalid))

    async def add_hierarchy_edges(
        self, db: AsyncSession, user_id: str, site_id: str, body: HierarchyRequest
    ) -> HierarchyResult:
        await structure_job_service.get(db, site_id, body.job_id)
        pages = await self._hierarchy_pages(db, site_id)
        home = next((p for p in pages if p.is_home), None)
        hubs = [p for p in pages if p.page_type == "hub" and p is not home]
        utilities = [p for p in pages if p.page_type == "utility" and p is not home]
        rows = [
            NewLinkSuggestion(job_id=body.job_id, from_page_id=src, to_page_id=dst, suggestion=why)
            for src, dst, why in self._hierarchy_edges(home, hubs, utilities)
        ]
        inserted = await self.create_many(db, user_id, site_id, rows)
        return HierarchyResult(
            inserted=inserted,
            skipped=len(rows) - inserted,
            home_found=home is not None,
            hubs=len(hubs),
        )

    async def propose_unlinked_mentions(
        self, db: AsyncSession, user_id: str, site_id: str, body: MentionsRequest
    ) -> MentionsResult:
        await structure_job_service.get(db, site_id, body.job_id)
        to_ids = [t.to_id for t in body.targets]
        known = await site_pages.existing_ids(db, site_id, to_ids)
        missing = [p for p in to_ids if p not in known]
        if missing:
            raise HTTPException(404, f"No page on this website with id {', '.join(missing)}.")
        excluded = [(to_id, to_id) for to_id in to_ids] + [
            (dst, src) for src, dst in await site_page_links.pairs_into(db, site_id, to_ids)
        ]
        hits = await site_chunks.phrase_hits(
            db,
            site_id,
            [(t.to_id, phrase) for t in body.targets for phrase in t.phrases],
            excluded,
            body.limit_per_target,
        )
        rows = [
            NewLinkSuggestion(
                job_id=body.job_id,
                from_page_id=hit.page_id,
                to_page_id=hit.key,
                from_chunk_id=hit.chunk_id,
                suggestion=f'The passage mentions "{hit.phrase}" without linking to the '
                "page about it; link the mention.",
            )
            for hit in hits
        ]
        matched = {hit.key for hit in hits}
        result = MentionsResult(targets_without_match=[p for p in to_ids if p not in matched])
        result.inserted = await self.create_many(db, user_id, site_id, rows)
        result.skipped = len(rows) - result.inserted
        return result

    async def propose_link_removals(
        self, db: AsyncSession, user_id: str, site_id: str, body: RemovalsRequest
    ) -> RemovalsResult:
        await structure_job_service.get(db, site_id, body.job_id)
        try:
            edges = self._workspace_edges(
                await workspace_tables.rows(user_id, site_id, body.source_table), body.source_table
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
            elif fact.to_is_hub:
                result.to_hub_or_home += 1
            elif fact.to_inlinks <= 1:
                result.last_inlink += 1
            else:
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
            related = relevance.get((fact.from_page_id, fact.to_page_id))
            rows.append(
                NewLinkSuggestion(
                    job_id=body.job_id,
                    from_page_id=fact.from_page_id,
                    to_page_id=fact.to_page_id,
                    from_chunk_id=chunk_id,
                    action=LinkAction.DELETE,
                    suggestion=f"Remove the link {anchor}to {fact.to_url}. "
                    f"{edge.reason or REMOVAL_REASON}",
                    search_score=None if related is None else 1.0 - related,
                )
            )
        result.inserted = await self.create_many(db, user_id, site_id, rows)
        result.skipped = len(rows) - result.inserted
        return result

    async def propose_links_from_table(
        self, db: AsyncSession, user_id: str, site_id: str, body: PairsRequest
    ) -> PairsResult:
        await structure_job_service.get(db, site_id, body.job_id)
        try:
            edges = self._workspace_edges(
                await workspace_tables.rows(user_id, site_id, body.source_table), body.source_table
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        floor = (
            search_settings().meelu_search_min_similarity
            if body.min_similarity is None
            else body.min_similarity
        )
        result = PairsResult(read=len(edges), min_similarity=floor)
        reasons: dict[tuple[str, str], str | None] = {}
        for edge in edges:
            if edge.from_page_id != edge.to_page_id:
                reasons.setdefault((edge.from_page_id, edge.to_page_id), edge.reason)
        pairs = list(reasons)

        page_ids = list({p for pair in pairs for p in pair})
        live = await site_pages.existing_ids(db, site_id, page_ids) - await site_pages.gone_ids(
            db, site_id, page_ids
        )
        result.not_live = sum(1 for f, t in pairs if f not in live or t not in live)
        pairs = [(f, t) for f, t in pairs if f in live and t in live]

        linked = await site_page_links.existing_pairs(db, site_id, pairs)
        result.already_linked = sum(1 for p in pairs if p in linked)
        pairs = [p for p in pairs if p not in linked]

        suggested = {
            (f, t)
            for f, t, action, _ in await link_suggestions.edge_keys(db, site_id, pairs)
            if action is LinkAction.CREATE
        }
        result.already_suggested = sum(1 for p in pairs if p in suggested)
        pairs = [p for p in pairs if p not in suggested]

        best = await site_chunks.best_passages(db, site_id, pairs)
        result.not_embedded = len(pairs) - len(best)
        close = {pair: hit for pair, hit in best.items() if hit[1] >= floor}
        result.below_threshold = len(best) - len(close)
        if not close:
            return result

        by_source: dict[str, list[tuple[str, str, float]]] = {}
        for (from_page_id, to_page_id), (chunk_id, similarity) in close.items():
            by_source.setdefault(from_page_id, []).append((to_page_id, chunk_id, similarity))
        left = await self._budget_left(db, site_id, list(by_source))
        urls = await site_pages.urls_by_ids(
            db, site_id, list({to_page_id for _, to_page_id in close})
        )
        rows: list[NewLinkSuggestion] = []
        for from_page_id, hits in by_source.items():
            hits.sort(key=lambda hit: -hit[2])
            cap = max(0, min(body.per_source, left.get(from_page_id, body.per_source)))
            result.over_source_cap += max(0, len(hits) - cap)
            for to_page_id, chunk_id, similarity in hits[:cap]:
                reason = reasons[(from_page_id, to_page_id)] or PAIR_REASON
                rows.append(
                    NewLinkSuggestion(
                        job_id=body.job_id,
                        from_page_id=from_page_id,
                        to_page_id=to_page_id,
                        from_chunk_id=chunk_id,
                        suggestion=f"Link this passage to {urls.get(to_page_id, to_page_id)}. "
                        f"{reason}",
                        search_score=similarity,
                    )
                )
        result.inserted = await self.create_many(db, user_id, site_id, rows)
        result.skipped = len(rows) - result.inserted
        return result

    async def screen_suggestions(
        self, db: AsyncSession, user_id: str, site_id: str, body: ScreenRequest
    ) -> ScreenResult:
        caller = Caller(user_id=user_id, site_id=site_id)
        items = await self._inputs(
            db, site_id, SuggestionState.DRAFT, body.job_id, body.ids, body.limit
        )
        result = ScreenResult()
        for item in items:
            try:
                state = await self._screen_one(db, site_id, caller, item, body.question)
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
        self, db: AsyncSession, site_id: str, body: ReviewInputsRequest
    ) -> ReviewBatch:
        items = await self._inputs(
            db, site_id, SuggestionState.SCREENING_APPROVED, body.job_id, body.ids, body.limit
        )
        outbound = await site_page_links.outbound_by_src_ids(
            db, site_id, list({item.from_page_id for item in items})
        )
        return ReviewBatch(
            instructions=review.INSTRUCTIONS.format(prompt=body.prompt),
            schema=review.SCHEMA,
            items=[
                ReviewItem(
                    id=item.id,
                    state=review.item_state(item, outbound.get(item.from_page_id, [])),
                )
                for item in items
            ],
        )

    async def apply_verdicts(
        self, db: AsyncSession, site_id: str, body: VerdictRequest
    ) -> ReviewResult:
        verdicts = {given.id: given.verdict for given in body.verdicts}
        approved = await link_suggestions.transition(
            db,
            site_id,
            {i for i, v in verdicts.items() if v is SuggestionState.REVIEW_APPROVED},
            SuggestionState.SCREENING_APPROVED,
            SuggestionState.REVIEW_APPROVED,
        )
        rejected = await link_suggestions.transition(
            db,
            site_id,
            {i for i, v in verdicts.items() if v is SuggestionState.REVIEW_REJECTED},
            SuggestionState.SCREENING_APPROVED,
            SuggestionState.REVIEW_REJECTED,
        )
        return ReviewResult(
            reviewed=approved + rejected,
            approved=approved,
            rejected=rejected,
            failed=len(body.verdicts) - approved - rejected,
        )

    async def rank_suggestions(
        self, db: AsyncSession, site_id: str, body: RankRequest
    ) -> RankResult:
        rows = await link_suggestions.list_in_state(db, site_id, SuggestionState.REVIEW_APPROVED)
        if not rows:
            return RankResult()
        pages, site = await page_facts_service.for_site(db, site_id)
        ranked = ranking.rank(
            [
                ranking.Candidate(
                    suggestion_id=r.id,
                    from_page_id=r.from_page_id,
                    to_page_id=r.to_page_id,
                    action=r.action,
                    search_score=r.search_score,
                    confidence=r.confidence,
                )
                for r in rows
            ],
            pages,
            site,
            ranking.RankParams(
                max_per_target=body.max_per_target, target_discount=body.target_discount
            ),
        )
        kept = {r.candidate.suggestion_id: r.score for r in ranked if r.kept}
        await link_suggestions.update_scores(db, site_id, kept)
        removed = await link_suggestions.delete_many(
            db, site_id, {r.candidate.suggestion_id for r in ranked if not r.kept}
        )
        return RankResult(scored=len(ranked), kept=len(kept), removed=removed)

    async def resolve_page_id(
        self, db: AsyncSession, site_id: str, page_id: str | None, url: str | None, end: str
    ) -> str:
        if page_id:
            if not await site_pages.exists(db, site_id, page_id):
                raise HTTPException(404, f"No page {page_id} on this website.")
            return page_id
        if not url:
            raise HTTPException(
                400, f"A suggestion needs a {end} page: send {end}PageId or {end}Url."
            )
        found = await site_pages.id_by_url(db, site_id, url)
        if not found:
            raise HTTPException(404, f"No page on record at {url}.")
        return found

    async def require_chunk_on_page(
        self, db: AsyncSession, site_id: str, chunk_id: str, page_id: str
    ) -> None:
        owner = await site_chunks.page_id_of(db, site_id, chunk_id)
        if owner is None:
            raise HTTPException(404, f"No chunk {chunk_id} on this website.")
        if owner != page_id:
            raise HTTPException(400, "The chunk must belong to the page the link goes from.")

    async def _require_no_clash(
        self,
        db: AsyncSession,
        site_id: str,
        from_page_id: str,
        from_chunk_id: str | None,
        to_page_id: str,
        action: LinkAction,
        exclude_id: str | None = None,
    ) -> None:
        clash = await link_suggestions.find_edge(
            db, site_id, from_page_id, from_chunk_id, to_page_id, action, exclude_id
        )
        if clash is not None:
            scope = "from that chunk" if from_chunk_id else "between those pages"
            raise HTTPException(
                409,
                f'A "{action}" suggestion {scope} already exists ({clash.id}, {clash.state}).',
            )

    async def _within_budget(
        self, db: AsyncSession, site_id: str, rows: list[NewLinkSuggestion]
    ) -> list[NewLinkSuggestion]:
        from_ids = list({r.from_page_id for r in rows if r.action is LinkAction.CREATE})
        if not from_ids:
            return rows
        left = await self._budget_left(db, site_id, from_ids)
        full = {page_id for page_id, room in left.items() if room <= 0}
        return [r for r in rows if r.action is not LinkAction.CREATE or r.from_page_id not in full]

    async def _budget_left(
        self, db: AsyncSession, site_id: str, page_ids: list[str]
    ) -> dict[str, int]:
        facts = await page_facts_service.for_pages(db, site_id, page_ids)
        approved = await link_suggestions.approved_create_counts(db, site_id, page_ids)
        return {
            page_id: link_room(fact) - approved.get(page_id, 0) for page_id, fact in facts.items()
        }

    async def _inputs(
        self,
        db: AsyncSession,
        site_id: str,
        state: SuggestionState,
        job_id: str | None,
        ids: list[str] | None,
        limit: int,
    ) -> list[ScreeningInput]:
        rows = await link_suggestions.list_in_state(db, site_id, state, job_id, ids, limit)
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
        extracted = await site_page_llm_extractions.by_page_ids(db, site_id, from_ids + to_ids)
        anchors: dict[tuple[str, str], str | None] = {}
        for link in await site_page_links.list_between(
            db, site_id, from_ids, to_ids, region=REMOVAL_REGION
        ):
            anchors.setdefault((link.src_page_id, link.dst_page_id), link.anchor)
        items: list[ScreeningInput] = []
        for row in rows:
            source = sources.get(row.from_page_id)
            target = targets.get(row.to_page_id)
            if source is None or target is None:
                continue
            items.append(
                ScreeningInput(
                    id=row.id,
                    action=row.action,
                    suggestion=row.suggestion,
                    from_page_id=row.from_page_id,
                    to_page_id=row.to_page_id,
                    from_url=source.url,
                    from_title=source.title,
                    from_content_hash=source.content_hash,
                    from_text=chunks.get(row.from_chunk_id) or source.body_text or "",
                    from_details=extracted_details(extracted.get(row.from_page_id)),
                    to_url=target.url,
                    to_title=target.title,
                    to_meta_description=target.meta_description,
                    to_h1=list(target.h1 or []),
                    to_details=extracted_details(extracted.get(row.to_page_id)),
                    to_content_hash=target.content_hash,
                    anchor=anchors.get((row.from_page_id, row.to_page_id)),
                )
            )
        return items

    async def _screen_one(
        self,
        db: AsyncSession,
        site_id: str,
        caller: Caller,
        item: ScreeningInput,
        question: str | None,
    ) -> SuggestionState | None:
        subject = {
            "suggestion_id": item.id,
            "from_hash": item.from_content_hash,
            "to_hash": item.to_content_hash,
            "question": question,
        }
        try:
            answer = await json_data_extractor.decide(
                db,
                caller,
                subject,
                screening.item_state(item),
                screening.questions(item.action, question),
            )
        except ProviderRequestError as exc:
            log.warning("link suggestion screening failed", suggestion_id=item.id, error=str(exc))
            return None
        confidence = yes_confidence(answer["answers"]["apply"])
        state = screened_state(confidence)
        await link_suggestions.update(
            db, site_id, item.id, LinkSuggestionChanges(state=state, confidence=confidence)
        )
        return state

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
                to_is_hub=is_home(to_url) or types.get(key[1]) == "hub",
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

    async def _hierarchy_pages(self, db: AsyncSession, site_id: str) -> list[HierarchyPage]:
        pages = await site_pages.list_not_gone(db, site_id)
        types = await site_page_llm_extractions.page_types_by_page_ids(
            db, site_id, [p.id for p in pages]
        )
        found: list[HierarchyPage] = []
        for page in pages:
            home = is_home(page.url)
            page_type = types.get(page.id)
            if home or page_type in HIERARCHY_TYPES:
                found.append(
                    HierarchyPage(id=page.id, url=page.url, is_home=home, page_type=page_type)
                )
        return found

    def _hierarchy_edges(
        self,
        home: HierarchyPage | None,
        hubs: list[HierarchyPage],
        utilities: list[HierarchyPage],
    ) -> Iterator[tuple[str, str, str]]:
        edges: dict[tuple[str, str], str] = {}

        def add(src: HierarchyPage, dst: HierarchyPage, why: str) -> None:
            if src.id != dst.id:
                edges.setdefault((src.id, dst.id), why)

        if home is not None:
            for page in utilities:
                add(home, page, HOME_TO_UTILITY)
                add(page, home, BACK_TO_HOME)

        by_path = {path_of(h.url): h for h in hubs}
        for path, hub in by_path.items():
            parent_path = parent_of(path)
            parent = by_path.get(parent_path)
            if parent is not None:
                add(parent, hub, PARENT_TO_CHILD.format(child=path))
                add(hub, parent, CHILD_TO_PARENT.format(parent=parent_path))

        for (from_page_id, to_page_id), why in edges.items():
            yield from_page_id, to_page_id, why

    async def _with_pages(
        self, db: AsyncSession, site_id: str, records: list[LinkSuggestionRecord]
    ) -> list[LinkSuggestionRecord]:
        urls = await site_pages.urls_by_ids(
            db, site_id, [page_id for r in records for page_id in (r.from_page_id, r.to_page_id)]
        )
        chunk_ids = [r.from_chunk_id for r in records if r.from_chunk_id]
        chunks = {c.id: c for c in await site_chunks.list_by_ids(db, site_id, chunk_ids)}
        removals = [r for r in records if r.action is LinkAction.DELETE]
        anchors: dict[tuple[str, str], str | None] = {}
        if removals:
            for link in await site_page_links.list_between(
                db,
                site_id,
                list({r.from_page_id for r in removals}),
                list({r.to_page_id for r in removals}),
                region=REMOVAL_REGION,
            ):
                if link.anchor:
                    anchors.setdefault((link.src_page_id, link.dst_page_id), link.anchor)
        enriched = []
        for r in records:
            chunk = chunks.get(r.from_chunk_id)
            enriched.append(
                r.model_copy(
                    update={
                        "from_url": urls.get(r.from_page_id),
                        "to_url": urls.get(r.to_page_id),
                        "from_chunk_heading": chunk.heading_path if chunk else None,
                        "from_chunk_ordinal": chunk.ordinal if chunk else None,
                        "from_chunk_text": chunk.text if chunk else None,
                        "anchor": anchors.get((r.from_page_id, r.to_page_id)),
                    }
                )
            )
        return enriched


link_suggestion_service = LinkSuggestionService()
