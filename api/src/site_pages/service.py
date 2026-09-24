from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginationParams, PaginationService
from src.embed_worker.search import search_from_query, search_from_text
from src.site_pages import repository as repo
from src.site_pages.pagerank import page_rank
from src.site_pages.schemas import (
    SiteChunkRecord,
    SitePageBatchRequest,
    SitePageBatchResult,
    SitePageCreateRequest,
    SitePageDiscoveryRecord,
    SitePageFilters,
    SitePageLinksResult,
    SitePageListResult,
    SitePageMatch,
    SitePagePruneResult,
    SitePageRecord,
    SitePageRef,
    SitePageSearchRequest,
    SitePageSearchResponse,
    SitePageStatsResult,
    SitePageUpdateRequest,
    SitePageVisitedRequest,
    SitePageVisitedResult,
    SitePageVisitSweepResult,
)
from src.site_pages.url import landing_path, normalise_url
from src.sites import repository as sites_repo

SEARCH_MATCH_POOL = 200


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

    found = await search_from_query(db, site_id, text, limit=SEARCH_MATCH_POOL)
    if not found.hits:
        return SitePageListResult(
            data=[],
            pagination=PaginationService.build_pagination_meta(0, paging.page, paging.page_size),
            note=found.note or "No page covers that.",
        )

    by_id = {h.page_id: h for h in found.hits}
    result = await repo.list_pages(db, site_id, filters, paging, view=view, match_ids=list(by_id))
    data = []
    for row in result.data:
        hit = by_id.get(getattr(row, "id", None))
        if hit is None:
            data.append(row)
            continue
        data.append(
            row.model_copy(
                update={
                    "similarity": hit.rerank_score
                    if hit.rerank_score is not None
                    else hit.similarity,
                    "match": SitePageMatch(text=hit.snippet or "", heading_path=hit.heading_path),
                }
            )
        )
    return SitePageListResult(data=data, pagination=result.pagination, note=found.note)


async def search(
    db: AsyncSession, site_id: str, body: SitePageSearchRequest
) -> SitePageSearchResponse:
    if not body.text.strip():
        raise HTTPException(400, "Pass something to search for.")
    run = search_from_text if body.input == "text" else search_from_query
    found = await run(
        db,
        site_id,
        body.text,
        mode=body.mode,
        min_similarity=body.min_similarity,
        limit=body.limit,
        rerank=body.rerank,
    )
    return SitePageSearchResponse(
        hits=found.hits, mode=found.mode, reranked=found.reranked, note=found.note
    )


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


def _teleport(refs, seed_by_path: dict[str, int]) -> dict[str, float] | None:
    if not seed_by_path:
        return None
    weights = {p.id: SEED_FLOOR for p in refs}
    matched = 0
    for ref in refs:
        sessions = seed_by_path.get(landing_path(ref.url))
        if sessions is None:
            continue
        weights[ref.id] = SEED_FLOOR + sessions
        matched += 1
    return weights if matched > 0 else None


async def compute_link_scores(db: AsyncSession, site_id: str) -> int:
    refs = await repo.live_page_refs(db, site_id)
    if not refs:
        return 0
    edges = await repo.edge_list(db, site_id)
    teleport = _teleport(refs, (await repo.landing_seed(db, site_id)).sessions_by_path)
    ids = [p.id for p in refs]

    await repo.write_scores(db, site_id, "link_score", page_rank(ids, edges, teleport=teleport))
    return len(ids)


async def rebuild_graph(db: AsyncSession, site_id: str) -> None:
    await repo.resolve_links(db, site_id)
    await repo.restamp_graph(db, site_id)
    await compute_link_scores(db, site_id)


async def stats(db: AsyncSession, user_id: str, site_id: str) -> SitePageStatsResult:
    counts = await repo.page_stats(db, site_id)
    site = await sites_repo.get_site(db, user_id, site_id)
    return SitePageStatsResult(
        **counts.model_dump(),
        last_crawled_at=site.last_crawled_at if site is not None else None,
        sitemap_url_count=site.sitemap_url_count if site is not None else None,
    )


async def discovery(db: AsyncSession, site_id: str) -> SitePageDiscoveryRecord:
    return await repo.page_discovery(db, site_id, deep_from=4, cap=500)


async def page_links(db: AsyncSession, site_id: str, page_id: str) -> SitePageLinksResult:
    await page(db, site_id, page_id)
    return await repo.page_links(db, site_id, page_id)


async def chunks(db: AsyncSession, site_id: str, page_id: str) -> list[SiteChunkRecord]:
    await page(db, site_id, page_id)
    return await repo.list_chunks(db, site_id, page_id)
