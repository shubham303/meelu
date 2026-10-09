from collections import defaultdict
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginationParams, PaginationService
from src.embed_worker.search.service import page_search_service
from src.seo.site_search.repositories.site_page_index_status import site_page_index_statuses
from src.seo.site_traffic.repositories.site_traffic_landing_daily import (
    site_traffic_landing_dailies,
)
from src.site_pages.llm_extraction.repository import site_page_llm_extractions
from src.site_pages.pagerank import page_rank
from src.site_pages.repositories.chunks import site_chunks
from src.site_pages.repositories.links import site_page_links
from src.site_pages.repositories.pages import site_pages
from src.site_pages.schemas import (
    DiscoveryPage,
    PageTypeCount,
    SiteChunkRecord,
    SitePageBatchRequest,
    SitePageBatchResult,
    SitePageCreateRequest,
    SitePageDiscoveryRecord,
    SitePageExportRecord,
    SitePageFilters,
    SitePageLinksResult,
    SitePageListResult,
    SitePageMatch,
    SitePagePruneResult,
    SitePageRecord,
    SitePageRef,
    SitePageSlimRecord,
    SitePageStatsResult,
    SitePageUpdateRequest,
    SitePageVisitedRequest,
    SitePageVisitedResult,
    SitePageVisitSweepResult,
)
from src.site_pages.schemas.links import (
    NewSitePageLink,
    PageLink,
    SitePageOutlinksRequest,
    SitePageOutlinksResult,
    merge_links,
)
from src.site_pages.schemas.search import SitePageSearchRequest, SitePageSearchResponse
from src.site_pages.url import landing_path, normalise_url
from src.sites.repository import sites

SEARCH_MATCH_POOL = 200
SEED_FLOOR = 0.1
SEED_DAYS = 90
MAX_DEPTH = 50
LINK_CAP = 500
DEEP_FROM = 4
DISCOVERY_CAP = 500


class SitePageService:
    async def list_pages(
        self,
        db: AsyncSession,
        site_id: str,
        filters: SitePageFilters,
        paging: PaginationParams,
        view: str | None = None,
        search_text: str | None = None,
    ) -> SitePageListResult:
        text = search_text.strip() if search_text else None
        if not text:
            return await self._list(db, site_id, filters, paging, view)

        found = await page_search_service.search_from_query(
            db, site_id, text, limit=SEARCH_MATCH_POOL
        )
        if not found.hits:
            return SitePageListResult(
                data=[],
                pagination=PaginationService.build_pagination_meta(
                    0, paging.page, paging.page_size
                ),
                note=found.note or "No page covers that.",
            )

        by_id = {h.page_id: h for h in found.hits}
        result = await self._list(db, site_id, filters, paging, view, match_ids=list(by_id))
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
                        "match": SitePageMatch(
                            text=hit.snippet or "", heading_path=hit.heading_path
                        ),
                    }
                )
            )
        return SitePageListResult(data=data, pagination=result.pagination, note=found.note)

    async def search(
        self, db: AsyncSession, site_id: str, body: SitePageSearchRequest
    ) -> SitePageSearchResponse:
        if not body.text.strip():
            raise HTTPException(400, "Pass something to search for.")
        run = (
            page_search_service.search_from_text
            if body.input == "text"
            else page_search_service.search_from_query
        )
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

    async def get(self, db: AsyncSession, site_id: str, page_id: str) -> SitePageRecord:
        found = await site_pages.get(db, site_id, page_id)
        if found is None:
            raise HTTPException(404, f"No page {page_id} for this website.")
        return await self._with_link_counts(db, site_id, found)

    async def get_by_url(self, db: AsyncSession, site_id: str, url: str) -> SitePageRecord:
        wanted = normalise_url(url)
        found = await site_pages.get_by_url(db, site_id, wanted)
        if found is None:
            raise HTTPException(404, f"No page {wanted} has been crawled for this website.")
        return await self._with_link_counts(db, site_id, found)

    async def update(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        page_id: str,
        body: SitePageUpdateRequest,
    ) -> SitePageRecord:
        existing = await self._require(db, site_id, page_id)
        values = body.changes()
        if not values:
            raise HTTPException(400, "Nothing to save.")

        if "content_hash" in values and values["content_hash"] != existing.content_hash:
            values["content_changed_at"] = datetime.now(UTC)

        updated = await site_pages.update(db, site_id, existing.id, values)
        if updated is None:
            raise HTTPException(404, f"No page {existing.id} for this website.")
        return updated

    async def delete(
        self, db: AsyncSession, user_id: str, site_id: str, page_id: str
    ) -> SitePageRef:
        existing = await self._require(db, site_id, page_id)
        removed = await site_pages.delete(db, site_id, existing.id)
        if removed is None:
            raise HTTPException(404, f"No page {existing.id} for this website.")
        return removed

    async def save(
        self, db: AsyncSession, user_id: str, site_id: str, body: SitePageCreateRequest
    ) -> SitePageRecord:
        values = body.changes()
        existing = await site_pages.get_by_url(db, site_id, body.url)

        saved = (
            await site_pages.update(db, site_id, existing.id, values)
            if existing
            else await site_pages.insert(db, user_id, site_id, values)
        )
        if saved is None:
            raise HTTPException(500, "The page was not written.")
        return saved

    async def save_many(
        self, db: AsyncSession, user_id: str, site_id: str, body: SitePageBatchRequest
    ) -> SitePageBatchResult:
        if not body.pages:
            raise HTTPException(
                400, "Send `pages: [...]` — a crawl batch with no pages writes nothing."
            )
        written = await site_pages.upsert_many(db, user_id, site_id, body.pages)
        return SitePageBatchResult(pages=len(written))

    async def save_outlinks(
        self, db: AsyncSession, user_id: str, site_id: str, body: SitePageOutlinksRequest
    ) -> SitePageOutlinksResult:
        if not body.pages:
            raise HTTPException(400, "Send `pages: [...]` — each page url with the links it holds.")
        merged = {item.url: merge_links(item.links) for item in body.pages}
        sources = await site_pages.ids_by_urls(db, site_id, list(merged))
        targets = await site_pages.link_targets(
            db, site_id, list({link.url for links in merged.values() for link in links})
        )
        unresolved: set[str] = set()
        links_by_page: dict[str, list[NewSitePageLink]] = {}
        for url, links in merged.items():
            src_id = sources.get(url)
            if src_id is None:
                continue
            rows = links_by_page.setdefault(src_id, [])
            for link in links:
                target = targets.get(link.url)
                if target is None:
                    unresolved.add(link.url)
                    continue
                dst_id, canonical = target
                if dst_id == src_id:
                    continue
                rows.append(
                    NewSitePageLink(
                        dst_page_id=dst_id,
                        dst_url=link.url,
                        region=link.region,
                        rel=link.rel,
                        anchor=link.anchor,
                        count=link.count,
                        followable=link.followable,
                        dst_canonical=canonical,
                    )
                )
        stored = await site_page_links.replace_for_pages(db, user_id, site_id, links_by_page)
        return SitePageOutlinksResult(
            pages=len(links_by_page), links=stored, unresolved=sorted(unresolved)
        )

    async def start_visit_sweep(self, db: AsyncSession, site_id: str) -> SitePageVisitSweepResult:
        return SitePageVisitSweepResult(reset=await site_pages.mark_all_unvisited(db, site_id))

    async def mark_visited(
        self, db: AsyncSession, site_id: str, body: SitePageVisitedRequest
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
        return SitePageVisitedResult(visited=await site_pages.mark_visited(db, site_id, urls))

    async def prune(self, db: AsyncSession, site_id: str) -> SitePagePruneResult:
        return SitePagePruneResult(deleted=await site_pages.delete_unvisited(db, site_id))

    async def restamp_graph(self, db: AsyncSession, site_id: str) -> None:
        sources: dict[str, set[str]] = defaultdict(set)
        forward: dict[str, list[str]] = defaultdict(list)
        for src, dst, region in await site_page_links.resolved_edges(db, site_id):
            sources[dst].add(src)
            if region != "pagination":
                forward[src].append(dst)

        depths: dict[str, int] = {}
        home = await site_pages.home_page_id(db, site_id)
        if home is not None:
            depths[home] = 0
            frontier = [home]
            depth = 0
            while frontier and depth < MAX_DEPTH:
                reached: list[str] = []
                for node in frontier:
                    for nxt in forward.get(node, ()):
                        if nxt not in depths:
                            depths[nxt] = depth + 1
                            reached.append(nxt)
                frontier = reached
                depth += 1

        stamps = {
            page_id: (len(sources.get(page_id, ())), depths.get(page_id))
            for page_id in set(sources) | set(depths)
        }
        await site_pages.write_graph_stamps(db, site_id, stamps)

    async def compute_link_scores(self, db: AsyncSession, site_id: str) -> int:
        refs = await site_pages.live_page_refs(db, site_id)
        if not refs:
            return 0
        ids = [p.id for p in refs]
        live = set(ids)
        edges = [e for e in await site_page_links.followable_edges(db, site_id) if e.src in live]
        seed = await site_traffic_landing_dailies.sessions_by_path(db, site_id, SEED_DAYS)
        teleport = self._teleport(refs, seed)

        await site_pages.write_scores(
            db, site_id, "link_score", page_rank(ids, edges, teleport=teleport)
        )
        return len(ids)

    async def rebuild_graph(self, db: AsyncSession, site_id: str) -> None:
        await site_page_links.set_dst_canonical(
            db, site_id, await site_pages.canonical_target_ids(db, site_id)
        )
        await self.restamp_graph(db, site_id)
        await self.compute_link_scores(db, site_id)

    async def stats(self, db: AsyncSession, user_id: str, site_id: str) -> SitePageStatsResult:
        counts = await site_pages.page_counts(db, site_id)
        by_type = await site_page_llm_extractions.count_by_page_type(db, site_id)
        typed = {page_type: n for page_type, n in by_type.items() if page_type is not None}
        untyped = await site_pages.count(db, site_id) - sum(typed.values())
        by_page_type = [PageTypeCount(page_type=t, n=n) for t, n in typed.items()]
        if untyped > 0:
            by_page_type.append(PageTypeCount(page_type=None, n=untyped))
        site = await sites.get(db, user_id, site_id)
        return SitePageStatsResult(
            **counts.model_dump(),
            by_page_type=by_page_type,
            chunks=await site_chunks.counts(db, site_id),
            last_crawled_at=site.last_crawled_at if site is not None else None,
            sitemap_url_count=site.sitemap_url_count if site is not None else None,
        )

    async def discovery(self, db: AsyncSession, site_id: str) -> SitePageDiscoveryRecord:
        found = await site_pages.page_discovery(db, site_id, deep_from=DEEP_FROM, cap=DISCOVERY_CAP)
        listed = [*found.orphan_pages, *found.unreachable_pages, *found.deep_pages]
        types = await site_page_llm_extractions.page_types_by_page_ids(
            db, site_id, list({p.id for p in listed})
        )

        def typed(pages: list[DiscoveryPage]) -> list[DiscoveryPage]:
            return [p.model_copy(update={"page_type": types.get(p.id)}) for p in pages]

        return found.model_copy(
            update={
                "orphan_pages": typed(found.orphan_pages),
                "unreachable_pages": typed(found.unreachable_pages),
                "deep_pages": typed(found.deep_pages),
            }
        )

    async def links(self, db: AsyncSession, site_id: str, page_id: str) -> SitePageLinksResult:
        page = await self._require(db, site_id, page_id)
        inbound = await site_page_links.list_inbound(db, site_id, page_id)
        src_urls = await site_pages.urls_by_ids(
            db, site_id, list({link.src_page_id for link in inbound})
        )
        stitched = sorted(
            (
                link.model_copy(update={"src_url": src_urls[link.src_page_id]})
                for link in inbound
                if link.src_page_id in src_urls
            ),
            key=lambda link: link.src_url or "",
        )
        return SitePageLinksResult(
            inbound=stitched[:LINK_CAP],
            outbound=await site_page_links.list_outbound(db, site_id, page_id, LINK_CAP),
            external=[PageLink.model_validate(link) for link in page.external_links[:LINK_CAP]],
        )

    async def chunks(self, db: AsyncSession, site_id: str, page_id: str) -> list[SiteChunkRecord]:
        await self._require(db, site_id, page_id)
        return await site_chunks.list_for_page(db, site_id, page_id)

    async def _require(self, db: AsyncSession, site_id: str, page_id: str) -> SitePageRecord:
        found = await site_pages.get(db, site_id, page_id)
        if found is None:
            raise HTTPException(404, f"No page {page_id} for this website.")
        return found

    async def _list(
        self,
        db: AsyncSession,
        site_id: str,
        filters: SitePageFilters,
        paging: PaginationParams,
        view: str | None,
        match_ids: list[str] | None = None,
    ) -> SitePageListResult:
        result = await site_pages.list_filtered(
            db,
            site_id,
            filters,
            paging,
            view=view,
            match_ids=match_ids,
            page_ids=await self._ids_of_types(db, site_id, filters),
        )
        return result.model_copy(update={"data": await self._decorate(db, site_id, result.data)})

    async def _ids_of_types(
        self, db: AsyncSession, site_id: str, filters: SitePageFilters
    ) -> list[str] | None:
        wanted: set[str] | None = None
        for types in ([filters.page_type] if filters.page_type else None, filters.page_types):
            if not types:
                continue
            ids = set(await site_page_llm_extractions.page_ids_with_types(db, site_id, types))
            wanted = ids if wanted is None else wanted & ids
        return None if wanted is None else sorted(wanted)

    async def _decorate(self, db: AsyncSession, site_id: str, rows: list) -> list:
        if not rows:
            return rows
        ids = [row.id for row in rows]
        first = rows[0]
        if isinstance(first, SitePageRecord):
            statuses = {
                st.page_id: st
                for st in await site_page_index_statuses.list_by_page_ids(db, site_id, ids)
            }
            return [self._with_index_status(row, statuses.get(row.id)) for row in rows]
        if not isinstance(first, (SitePageSlimRecord, SitePageExportRecord)):
            return rows
        types = await site_page_llm_extractions.page_types_by_page_ids(db, site_id, ids)
        if isinstance(first, SitePageSlimRecord):
            return [row.model_copy(update={"page_type": types.get(row.id)}) for row in rows]
        counts = await site_page_links.out_link_counts_by_src_ids(db, site_id, ids)
        return [
            row.model_copy(
                update={"page_type": types.get(row.id), "out_link_count": counts.get(row.id, 0)}
            )
            for row in rows
        ]

    def _with_index_status(self, page: SitePageRecord, st) -> SitePageRecord:
        if st is None:
            return page
        return page.model_copy(
            update={
                "index_state": st.index_state,
                "coverage_state": st.coverage_state,
                "google_canonical": st.google_canonical,
                "index_checked_at": st.index_checked_at,
            }
        )

    async def _with_link_counts(
        self, db: AsyncSession, site_id: str, page: SitePageRecord
    ) -> SitePageRecord:
        internal = (await site_page_links.out_link_counts_by_src_ids(db, site_id, [page.id])).get(
            page.id, 0
        )
        return page.model_copy(
            update={"out_link_count": internal, "external_link_count": len(page.external_links)}
        )

    def _teleport(
        self, refs: list[SitePageRef], seed_by_path: dict[str, int]
    ) -> dict[str, float] | None:
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


site_page_service = SitePageService()
