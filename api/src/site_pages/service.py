from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginationParams, PaginationService
from src.site_pages import repository as repo
from src.site_pages.embedding import EMBED_MODEL, embed_query
from src.site_pages.pagerank import page_rank
from src.site_pages.schemas import (
    SiteChunkRecord,
    SitePageBatchRequest,
    SitePageBatchResult,
    SitePageCreateRequest,
    SitePageFilters,
    SitePageKeywordCoverageResult,
    SitePageListResult,
    SitePageMatch,
    SitePagePruneResult,
    SitePageRecord,
    SitePageRef,
    SitePageStatsResult,
    SitePageUpdateRequest,
    SitePageVisitedRequest,
    SitePageVisitedResult,
    SitePageVisitSweepResult,
)
from src.site_pages.url import landing_path, normalise_url
from src.sites import repository as sites_repo


def _empty_search_note(chunks_total: int, chunks_embedded: int) -> str:
    if chunks_total == 0:
        return "Nothing is embedded for this website yet, so a semantic search cannot see any page."
    if chunks_embedded < chunks_total:
        return (
            f"No page matches. Semantic coverage is partial: {chunks_embedded} of "
            f"{chunks_total} passages embedded."
        )
    return "No page covers that."


async def pages(
    db: AsyncSession,
    site_id: str,
    filters: SitePageFilters,
    paging: PaginationParams,
    view: str | None = None,
    search_text: str | None = None,
) -> SitePageListResult:
    text = search_text.strip() if search_text else None
    if not text:
        return await repo.list_pages(db, site_id, filters, paging, view=view)

    vector = await embed_query(text)
    if vector is None:
        raise HTTPException(
            503, "Semantic search is unavailable — the query could not be embedded."
        )

    matches = await repo.semantic_page_matches(db, site_id, vector, model=EMBED_MODEL)
    if not matches:
        counts = await repo.page_stats(db, site_id)
        return SitePageListResult(
            data=[],
            pagination=PaginationService.build_pagination_meta(0, paging.page, paging.page_size),
            note=_empty_search_note(counts.chunks.total, counts.chunks.embedded),
        )

    by_id = {m.page_id: m for m in matches}
    result = await repo.list_pages(
        db, site_id, filters, paging, view=view, match_ids=[m.page_id for m in matches]
    )
    data = []
    for row in result.data:
        match = by_id.get(getattr(row, "id", None))
        if match is None:
            data.append(row)
            continue
        data.append(
            row.model_copy(
                update={
                    "similarity": match.similarity,
                    "match": SitePageMatch(text=match.snippet, heading_path=match.heading_path),
                }
            )
        )
    return SitePageListResult(data=data, pagination=result.pagination, note=result.note)


async def covered_keywords(
    db: AsyncSession, site_id: str, filters: SitePageFilters, limit: int | None = None
) -> SitePageKeywordCoverageResult:
    return await repo.keyword_coverage(db, site_id, filters, limit if limit is not None else 500)


async def page(db: AsyncSession, site_id: str, page_id: str) -> SitePageRecord:
    found = await repo.get_page(db, site_id, page_id)
    if found is None:
        raise HTTPException(404, f"No page {page_id} for this website.")
    return found


async def resolve_page(db: AsyncSession, site_id: str, url: str) -> SitePageRecord:
    wanted = normalise_url(url)
    found = await repo.get_page_by_url(db, site_id, wanted)
    if found is None:
        raise HTTPException(404, f"No page {wanted} has been crawled for this website.")
    return found


async def update_page(
    db: AsyncSession, user_id: str, site_id: str, page_id: str, body: SitePageUpdateRequest
) -> SitePageRecord:
    existing = await page(db, site_id, page_id)
    values = body.changes()
    if not values:
        raise HTTPException(400, "Nothing to save.")

    if "content_hash" in values and values["content_hash"] != existing.content_hash:
        values["content_changed_at"] = datetime.now(UTC)

    updated = await repo.update_page(db, site_id, existing.id, values)
    if updated is None:
        raise HTTPException(404, f"No page {existing.id} for this website.")
    return updated


async def delete_page(db: AsyncSession, user_id: str, site_id: str, page_id: str) -> SitePageRef:
    existing = await page(db, site_id, page_id)
    removed = await repo.delete_page(db, site_id, existing.id)
    if removed is None:
        raise HTTPException(404, f"No page {existing.id} for this website.")
    return removed


async def save_page(
    db: AsyncSession, user_id: str, site_id: str, body: SitePageCreateRequest
) -> SitePageRecord:
    values = body.changes()
    existing = await repo.get_page_by_url(db, site_id, body.url)

    saved = (
        await repo.update_page(db, site_id, existing.id, values)
        if existing
        else await repo.insert_page(db, user_id, site_id, values)
    )
    if saved is None:
        raise HTTPException(500, "The page was not written.")
    return saved


async def save_pages(
    db: AsyncSession, user_id: str, site_id: str, body: SitePageBatchRequest
) -> SitePageBatchResult:
    if not body.pages:
        raise HTTPException(
            400, "Send `pages: [...]` — a crawl batch with no pages writes nothing."
        )
    written = await repo.upsert_pages(db, user_id, site_id, body.pages)
    return SitePageBatchResult(pages=len(written))


async def start_visit_sweep(db: AsyncSession, site_id: str) -> SitePageVisitSweepResult:
    return SitePageVisitSweepResult(reset=await repo.mark_all_unvisited(db, site_id))


async def mark_visited(
    db: AsyncSession, site_id: str, body: SitePageVisitedRequest
) -> SitePageVisitedResult:
    if not body.urls:
        raise HTTPException(400, "Send `urls: [...]` — the pages the crawl just reached.")
    seen: dict[str, None] = {}
    for u in body.urls:
        if u != "":
            seen[normalise_url(u)] = None
    urls = list(seen)
    if not urls:
        raise HTTPException(400, "`urls` held no usable URLs.")
    return SitePageVisitedResult(visited=await repo.mark_visited(db, site_id, urls))


async def prune_pages(db: AsyncSession, site_id: str) -> SitePagePruneResult:
    return SitePagePruneResult(deleted=await repo.delete_unvisited(db, site_id))


SEED_FLOOR = 0.1


async def compute_link_scores(db: AsyncSession, site_id: str) -> int:
    refs = await repo.live_page_refs(db, site_id)
    edges = await repo.edge_list(db, site_id)
    seed_by_path = (await repo.landing_seed(db, site_id)).sessions_by_path
    if not refs:
        return 0

    teleport: dict[str, float] | None = None
    if seed_by_path:
        weights = {p.id: SEED_FLOOR for p in refs}
        matched = 0
        for ref in refs:
            sessions = seed_by_path.get(landing_path(ref.url))
            if sessions is None:
                continue
            weights[ref.id] = SEED_FLOOR + sessions
            matched += 1
        if matched > 0:
            teleport = weights

    ids = [p.id for p in refs]
    scores = page_rank(ids, edges, teleport=teleport)
    await repo.write_link_scores(db, site_id, scores)
    return len(ids)


async def rebuild_graph(db: AsyncSession, site_id: str) -> None:
    await repo.rebuild_graph(db, site_id)
    await compute_link_scores(db, site_id)


async def stats(db: AsyncSession, user_id: str, site_id: str) -> SitePageStatsResult:
    counts = await repo.page_stats(db, site_id)
    site = await sites_repo.get_site(db, user_id, site_id)
    return SitePageStatsResult(
        **counts.model_dump(),
        last_crawled_at=site.last_crawled_at if site is not None else None,
        sitemap_url_count=site.sitemap_url_count if site is not None else None,
    )


async def chunks(db: AsyncSession, site_id: str, page_id: str) -> list[SiteChunkRecord]:
    await page(db, site_id, page_id)
    return await repo.list_chunks(db, site_id, page_id)
