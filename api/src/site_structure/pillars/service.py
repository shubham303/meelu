from statistics import fmean

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.context import tenant_names
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.site_structure import ranking
from src.site_structure import repository as links_repo
from src.site_structure.constants import (
    OPEN_STATES,
    PILLAR_COVERED,
    PILLAR_DONE_FRACTION,
    PILLAR_OVERLAP,
    PILLAR_PARTLY_COVERED,
    PILLAR_STALE_FRACTION,
    STRUCTURAL_TYPES,
)
from src.site_structure.pillars import clustering, review, screening
from src.site_structure.pillars import repository as repo
from src.site_structure.pillars.clustering import PagePoint
from src.site_structure.schemas import (
    NewPillarPageSuggestion,
    PillarPageSuggestionFilter,
    PillarPageSuggestionRecord,
    PillarPageSuggestionSummaryResponse,
    PillarPageSuggestionUpdateRequest,
    PillarRankRequest,
    PillarReviewRequest,
    PillarScreenRequest,
    PillarsRequest,
    PillarsResult,
    RankResult,
    ReconcileResult,
    ReviewResult,
    ScreenResult,
    WorkspaceGroup,
)

NOT_FOUND = "No such pillar page suggestion on this website."

STRUCTURAL_SHARE = 0.5


async def get_suggestion(
    db: AsyncSession, site_id: str, suggestion_id: str
) -> PillarPageSuggestionRecord:
    found = await repo.get(db, site_id, suggestion_id)
    if found is None:
        raise HTTPException(404, NOT_FOUND)
    return found


async def list_suggestions(
    db: AsyncSession, site_id: str, filters: PillarPageSuggestionFilter, paging: PaginationParams
) -> PaginatedApiResponse[PillarPageSuggestionRecord]:
    return await repo.list_suggestions(db, site_id, filters, paging)


async def update_suggestion(
    db: AsyncSession, site_id: str, suggestion_id: str, body: PillarPageSuggestionUpdateRequest
) -> PillarPageSuggestionRecord:
    updated = await repo.update_one(db, site_id, suggestion_id, body.to_changes())
    if updated is None:
        raise HTTPException(404, NOT_FOUND)
    return updated


async def delete_suggestion(
    db: AsyncSession, site_id: str, suggestion_id: str
) -> PillarPageSuggestionRecord:
    found = await get_suggestion(db, site_id, suggestion_id)
    await repo.delete_one(db, site_id, found.id)
    return found


async def summary(db: AsyncSession, site_id: str) -> PillarPageSuggestionSummaryResponse:
    return await repo.summary(db, site_id)


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


async def propose_pillar_pages(
    db: AsyncSession, user_id: str, site_id: str, body: PillarsRequest
) -> PillarsResult:
    job = await links_repo.get_job(db, site_id, body.job_id)
    if job is None:
        raise HTTPException(404, "No such structure job on this website.")
    points = await repo.page_points(db, site_id)
    by_id = {p.id: p for p in points}
    vectors = {p.id: p.vector for p in points}
    if body.source_table:
        _, schema = tenant_names(user_id)
        try:
            groups = await repo.workspace_groups(db, schema, body.source_table)
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
    links = await repo.link_map(db, site_id)
    live = await repo.live_page_ids(db, site_id)
    open_sets = await repo.member_sets(db, site_id, OPEN_STATES + ("done",))
    rejected_sets = await repo.member_sets(db, site_id, ("user_rejected",))
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
        action = "expand" if cover.score >= PILLAR_PARTLY_COVERED and cover.page_id else "create"
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
    result.inserted = await repo.create_many(db, user_id, site_id, [row for _, row in kept])
    return result


async def screen_suggestions(
    db: AsyncSession, user_id: str, site_id: str, body: PillarScreenRequest
) -> ScreenResult:
    return await screening.screen(db, user_id, site_id, body.job_id, body.ids, body.limit)


async def review_suggestions(
    db: AsyncSession, user_id: str, site_id: str, body: PillarReviewRequest
) -> ReviewResult:
    return await review.review(db, user_id, site_id, body.prompt, body.job_id, body.ids, body.limit)


async def rank_suggestions(db: AsyncSession, site_id: str, body: PillarRankRequest) -> RankResult:
    rows = await repo.open_rows(db, site_id)
    if not rows:
        return RankResult()
    pages, site = await links_repo.page_facts(db, site_id)
    sizes = sorted(len(r.member_page_ids) for r in rows)
    scores: dict[str, float] = {}
    for row in rows:
        members = [pages[m] for m in row.member_page_ids if m in pages]
        authority = (
            fmean(ranking.percentile(site.inlinks, m.inlinks) for m in members) if members else 0.0
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
    await repo.update_scores(db, site_id, scores, cut)
    return RankResult(scored=len(rows), kept=len(rows) - len(cut), llm_rejected=len(cut))


async def reconcile(db: AsyncSession, site_id: str) -> ReconcileResult:
    rows = await repo.open_rows(db, site_id)
    if not rows:
        return ReconcileResult()
    live = await repo.live_page_ids(db, site_id)
    links = await repo.link_map(db, site_id)
    changed_at = await repo.page_changed_at(db, site_id)
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
    await repo.set_states(db, site_id, done, "done")
    await repo.set_states(db, site_id, stale, "stale")
    return ReconcileResult(done=len(done), stale=len(stale))
