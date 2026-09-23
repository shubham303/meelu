from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.context import tenant_names
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.site_structure import hierarchy, ranking, review, screening
from src.site_structure import repository as repo
from src.site_structure.constants import REMOVAL_REGION
from src.site_structure.pillars import service as pillars
from src.site_structure.schemas import (
    HierarchyRequest,
    HierarchyResult,
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
    ReviewRequest,
    ReviewResult,
    ScreenRequest,
    ScreenResult,
    StructureJobCreateRequest,
    StructureJobRecord,
    StructureJobUpdateRequest,
)

NOT_FOUND = "No such link suggestion on this website."

JOB_NOT_FOUND = "No such structure job on this website."


async def start_job(
    db: AsyncSession, user_id: str, site_id: str, body: StructureJobCreateRequest
) -> tuple[StructureJobRecord, ReconcileResult]:
    reconciled = await reconcile(db, site_id)
    job = await repo.create_job(db, user_id, site_id, body.prompt)
    return job, reconciled


async def get_job(db: AsyncSession, site_id: str, job_id: str) -> StructureJobRecord:
    found = await repo.get_job(db, site_id, job_id)
    if found is None:
        raise HTTPException(404, JOB_NOT_FOUND)
    return found


async def list_jobs(
    db: AsyncSession, site_id: str, paging: PaginationParams
) -> PaginatedApiResponse[StructureJobRecord]:
    return await repo.list_jobs(db, site_id, paging)


async def finish_job(
    db: AsyncSession, site_id: str, job_id: str, body: StructureJobUpdateRequest
) -> StructureJobRecord:
    updated = await repo.update_job_status(db, site_id, job_id, body.status)
    if updated is None:
        raise HTTPException(404, JOB_NOT_FOUND)
    return updated


async def reconcile(db: AsyncSession, site_id: str) -> ReconcileResult:
    done = await repo.mark_done_where_linked(db, site_id)
    done += await repo.mark_done_where_unlinked(db, site_id)
    stale = await repo.mark_stale_where_page_gone(db, site_id)
    pillars_reconciled = await pillars.reconcile(db, site_id)
    return ReconcileResult(
        done=done + pillars_reconciled.done, stale=stale + pillars_reconciled.stale
    )


async def list_suggestions(
    db: AsyncSession, site_id: str, filters: LinkSuggestionFilter, paging: PaginationParams
) -> PaginatedApiResponse[LinkSuggestionRecord]:
    return await repo.list_suggestions(db, site_id, filters, paging)


async def get_suggestion(
    db: AsyncSession, site_id: str, suggestion_id: str
) -> LinkSuggestionRecord:
    found = await repo.get(db, site_id, suggestion_id)
    if found is None:
        raise HTTPException(404, NOT_FOUND)
    return found


async def resolve_page_id(
    db: AsyncSession, site_id: str, page_id: str | None, url: str | None, end: str
) -> str:
    if page_id:
        if not await repo.page_exists(db, site_id, page_id):
            raise HTTPException(404, f"No page {page_id} on this website.")
        return page_id
    target = (url or "").strip()
    if not target:
        raise HTTPException(400, f"A suggestion needs a {end} page: send {end}PageId or {end}Url.")
    found = await repo.page_id_by_url(db, site_id, target)
    if not found:
        raise HTTPException(404, f"No page on record at {target}.")
    return found


async def require_chunk_on_page(
    db: AsyncSession, site_id: str, chunk_id: str, page_id: str
) -> None:
    owner = await repo.chunk_page_id(db, site_id, chunk_id)
    if owner is None:
        raise HTTPException(404, f"No chunk {chunk_id} on this website.")
    if owner != page_id:
        raise HTTPException(400, "The chunk must belong to the page the link goes from.")


async def create_suggestion(
    db: AsyncSession, user_id: str, site_id: str, body: LinkSuggestionCreateRequest
) -> LinkSuggestionRecord:
    await get_job(db, site_id, body.job_id)
    from_page_id = await resolve_page_id(db, site_id, body.from_page_id, body.from_url, "from")
    to_page_id = await resolve_page_id(db, site_id, body.to_page_id, body.to_url, "to")
    if from_page_id == to_page_id:
        raise HTTPException(400, "A link cannot go from a page to itself.")
    if body.from_chunk_id:
        await require_chunk_on_page(db, site_id, body.from_chunk_id, from_page_id)
    linked = await repo.edge_exists(db, site_id, from_page_id, to_page_id)
    if body.action == "create" and linked and body.state != "user_rejected":
        raise HTTPException(409, "That link already exists on the site; nothing to add.")
    if body.action != "create" and not linked:
        raise HTTPException(
            400, f'A "{body.action}" suggestion needs a link the crawl found; there is none.'
        )
    clash = await repo.find_edge(db, site_id, from_page_id, to_page_id, body.action)
    if clash is not None:
        raise HTTPException(
            409,
            f'A "{body.action}" suggestion for that link already exists ({clash.id}, {clash.state}).',
        )
    return await repo.create(db, user_id, site_id, body.to_new(from_page_id, to_page_id))


async def update_suggestion(
    db: AsyncSession, site_id: str, suggestion_id: str, body: LinkSuggestionUpdateRequest
) -> LinkSuggestionRecord:
    if body.from_chunk_id:
        current = await get_suggestion(db, site_id, suggestion_id)
        await require_chunk_on_page(db, site_id, body.from_chunk_id, current.from_page_id)
    updated = await repo.update_one(db, site_id, suggestion_id, body.to_changes())
    if updated is None:
        raise HTTPException(404, NOT_FOUND)
    return updated


async def delete_suggestion(
    db: AsyncSession, site_id: str, suggestion_id: str
) -> LinkSuggestionRecord:
    found = await get_suggestion(db, site_id, suggestion_id)
    await repo.delete_one(db, site_id, found.id)
    return found


async def summary(db: AsyncSession, site_id: str) -> LinkSuggestionSummaryResponse:
    return await repo.summary(db, site_id)


async def screen_suggestions(
    db: AsyncSession, user_id: str, site_id: str, body: ScreenRequest
) -> ScreenResult:
    return await screening.screen(
        db, user_id, site_id, body.job_id, body.ids, body.limit, body.question
    )


async def review_suggestions(
    db: AsyncSession, user_id: str, site_id: str, body: ReviewRequest
) -> ReviewResult:
    return await review.review(db, user_id, site_id, body.prompt, body.job_id, body.ids, body.limit)


async def rank_suggestions(db: AsyncSession, site_id: str, body: RankRequest) -> RankResult:
    candidates = await repo.open_candidates(db, site_id)
    if not candidates:
        return RankResult()
    pages, site = await repo.page_facts(db, site_id)
    params = ranking.RankParams(
        max_per_target=body.max_per_target, target_discount=body.target_discount
    )
    additions = [c for c in candidates if c.action == "create"]
    removals = [c for c in candidates if c.action == "delete"]
    ranked = ranking.rank_link_suggestions(additions, pages, site, params)
    ranked += ranking.rank_link_removals(removals, pages, params)
    scores = {r.candidate.suggestion_id: r.score for r in ranked}
    cut = {r.candidate.suggestion_id for r in ranked if not r.kept}
    await repo.update_scores(db, site_id, scores, cut)
    return RankResult(scored=len(ranked), kept=len(ranked) - len(cut), llm_rejected=len(cut))


async def propose_unlinked_mentions(
    db: AsyncSession, user_id: str, site_id: str, body: MentionsRequest
) -> MentionsResult:
    await get_job(db, site_id, body.job_id)
    known = await repo.page_ids_exist(db, site_id, body.to_ids)
    missing = [p for p in body.to_ids if p not in known]
    if missing:
        raise HTTPException(404, f"No page on this website with id {', '.join(missing)}.")
    result = MentionsResult()
    for to_page_id in body.to_ids:
        rows: dict[tuple[str, str], NewLinkSuggestion] = {}
        for phrase in body.phrases:
            for chunk_id, page_id in await repo.chunks_mentioning(
                db, site_id, to_page_id, phrase, body.limit_per_target
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
        inserted = await repo.create_many(db, user_id, site_id, list(rows.values()))
        result.inserted += inserted
        result.skipped += len(rows) - inserted
    return result


async def propose_hierarchy_links(
    db: AsyncSession, user_id: str, site_id: str, body: HierarchyRequest
) -> HierarchyResult:
    await get_job(db, site_id, body.job_id)
    pages = await repo.hierarchy_pages(db, site_id)
    rows, home, hubs = hierarchy.hierarchy_edges(pages, body.job_id)
    linked = await repo.linked_pairs(db, site_id, [p.id for p in pages])
    rows = [r for r in rows if (r.from_page_id, r.to_page_id) not in linked]
    inserted = await repo.create_many(db, user_id, site_id, rows)
    return HierarchyResult(
        inserted=inserted, skipped=len(rows) - inserted, home_found=home is not None, hubs=hubs
    )


REMOVAL_REASON = "The link does not serve the reader here."


async def propose_link_removals(
    db: AsyncSession, user_id: str, site_id: str, body: RemovalsRequest
) -> RemovalsResult:
    await get_job(db, site_id, body.job_id)
    _, schema = tenant_names(user_id)
    try:
        edges = await repo.workspace_edges(db, schema, body.source_table)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    result = RemovalsResult(read=len(edges))
    pairs = list({(e.from_page_id, e.to_page_id) for e in edges if e.from_page_id != e.to_page_id})
    facts = await repo.edge_facts(db, site_id, pairs)
    rows: list[NewLinkSuggestion] = []
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
        chunk_id = await repo.anchor_chunk(db, site_id, fact.from_page_id, fact.anchor)
        relevance = await repo.edge_relevance(
            db, site_id, fact.from_page_id, fact.to_page_id, chunk_id
        )
        anchor = f'"{fact.anchor}" ' if fact.anchor else ""
        rows.append(
            NewLinkSuggestion(
                job_id=body.job_id,
                from_page_id=fact.from_page_id,
                to_page_id=fact.to_page_id,
                from_chunk_id=chunk_id,
                action="delete",
                suggestion=f"Remove the link {anchor}to {fact.to_url}. {edge.reason or REMOVAL_REASON}",
                search_score=relevance,
            )
        )
    result.inserted = await repo.create_many(db, user_id, site_id, rows)
    result.skipped = len(rows) - result.inserted
    return result
