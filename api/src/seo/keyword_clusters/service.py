from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.providers.errors import ProviderRequestError
from src.providers.registry import Caller
from src.providers.seo_data.service import seo_data
from src.providers.seo_data.shape import own_domain
from src.seo.keyword_clusters.cluster_competitor_repository import seo_cluster_competitors
from src.seo.keyword_clusters.constants import (
    CLUSTER_NOT_FOUND,
    DISCOVERED_PER_SOURCE,
    MAX_COMPETITORS_READ,
    METRICS_TTL,
    MIN_COMPETITORS_FOR_GAP,
    NOISE_SHARE_OF_CORE,
    PAGE_WEIGHT,
    RANKED_PULL,
    SERP_DEPTH,
    SERP_DEVICE,
    SERP_TTL,
    TOP_N,
)
from src.seo.keyword_clusters.judging import intent_fits, relevant_keywords, split_groups
from src.seo.keyword_clusters.repository import seo_keyword_clusters
from src.seo.keyword_clusters.schemas import (
    ClusterBrief,
    ClusterDraft,
    ClusterFilters,
    ClusterMetrics,
    ClusterRecord,
    ClustersCreated,
    CreateClustersRequest,
    KeywordFacts,
    MetricsComputed,
    normalize_keyword,
)
from src.seo.keyword_clusters.winnability import climb, pass_chance, smoothed, strength
from src.seo.market import markets
from src.seo.site_search.repositories.site_search_daily import site_search_dailies
from src.seo.site_seo.competitor_repository import seo_competitors
from src.seo.site_seo.schemas import CompetitorRecord
from src.sites.schemas import SiteRecord

TOP_CLUSTERS = 20


def whole(value) -> int | None:
    return round(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def keyword_facts(item: dict) -> KeywordFacts:
    core = normalize_keyword((item.get("keyword_properties") or {}).get("core_keyword"))
    return KeywordFacts(
        keyword=normalize_keyword(item["keyword"]),
        ads_volume=whole((item.get("keyword_info") or {}).get("search_volume")),
        clickstream_volume=whole((item.get("clickstream_keyword_info") or {}).get("search_volume")),
        core_keyword=core or None,
    )


def belongs_to(domain: str, site_domain: str) -> bool:
    return domain == site_domain or domain.endswith(f".{site_domain}")


def gap_keywords(
    rivals: list[tuple[CompetitorRecord, set[str]]], ours: set[str], limit: int
) -> list[str]:
    counts: dict[str, int] = {}
    for _, keywords in rivals:
        for keyword in keywords:
            counts[keyword] = counts.get(keyword, 0) + 1
    gaps = [k for k, n in counts.items() if n >= MIN_COMPETITORS_FOR_GAP and k not in ours]
    return sorted(gaps, key=lambda k: (-counts[k], k))[:limit]


def brief(record: ClusterRecord) -> ClusterBrief:
    return ClusterBrief(
        id=record.id,
        main_keyword=record.main_keyword,
        size=len(record.keywords),
        volume=record.volume,
        winnability=record.winnability,
    )


class KeywordClusterService:
    async def get(self, db: AsyncSession, site_id: str, cluster_id: str) -> ClusterRecord:
        found = await seo_keyword_clusters.get(db, site_id, cluster_id)
        if found is None:
            raise HTTPException(404, CLUSTER_NOT_FOUND)
        return (await self._with_competitors(db, [found]))[0]

    async def list(
        self, db: AsyncSession, site_id: str, filters: ClusterFilters, paging: PaginationParams
    ) -> PaginatedApiResponse[ClusterRecord]:
        page = await seo_keyword_clusters.list(db, site_id, filters, paging)
        page.data = await self._with_competitors(db, page.data)
        return page

    async def delete(self, db: AsyncSession, site_id: str, cluster_id: str) -> None:
        if not await seo_keyword_clusters.delete(db, site_id, cluster_id):
            raise HTTPException(404, CLUSTER_NOT_FOUND)

    async def create_clusters(
        self,
        db: AsyncSession,
        caller: Caller,
        user_id: str,
        site: SiteRecord,
        body: CreateClustersRequest,
    ) -> ClustersCreated:
        market = markets(site.markets, site.language)[0]
        searched = await self._search_console_queries(db, site.id)
        ours = searched | await self._ranked(db, caller, site.domain, market)
        rivals = await self._competitor_keywords(db, caller, site.id, market)

        if body.source == "seeds":
            await db.commit()
            discovered = await seo_data.discover_keywords(
                caller, body.seeds, DISCOVERED_PER_SOURCE, market
            )
            raw = [*body.seeds, *discovered]
        elif body.source == "search_console":
            raw = await self._top_search_console_queries(db, site.id, body.limit)
        elif body.source == "ranked_keywords":
            raw = await self._ranked_by_traffic(db, caller, site.domain, market, body.limit)
        else:
            raw = gap_keywords(rivals, ours, body.limit)

        candidates = [k for k in dict.fromkeys(normalize_keyword(r) for r in raw) if k]
        clustered = await seo_keyword_clusters.clustered_keywords(
            db, site.id, market["location_code"], market["language_code"]
        )
        fresh = [k for k in candidates if k not in clustered]

        facts = await self._facts(db, caller, fresh, market)
        cores = {f.core_keyword or f.keyword for f in facts.values()}
        missing_cores = [c for c in cores if c not in facts]
        core_facts = {**facts, **await self._facts(db, caller, missing_cores, market)}

        def threshold(fact: KeywordFacts) -> float:
            if body.min_volume is not None:
                return body.min_volume
            core = core_facts.get(fact.core_keyword or fact.keyword)
            core_volume = (core.ads_volume if core else None) or fact.ads_volume or 0
            return max(NOISE_SHARE_OF_CORE * core_volume, 1)

        meaningful = [
            f.keyword
            for f in facts.values()
            if f.clickstream_volume is not None and f.clickstream_volume >= threshold(f)
        ]
        website = {"domain": site.domain, "about": site.summary or ""}
        await db.commit()
        relevant = await relevant_keywords(caller, website, body.seeds, meaningful)

        groups: dict[str, list[str]] = {}
        for keyword in relevant:
            groups.setdefault(facts[keyword].core_keyword or keyword, []).append(keyword)
        ordered = [
            sorted(members, key=lambda k: (-(facts[k].clickstream_volume or 0), k))
            for members in groups.values()
        ]
        clusters = await split_groups(caller, ordered)

        drafts = [
            ClusterDraft(
                main_keyword=cluster[0],
                keywords=cluster,
                core_keyword=facts[cluster[0]].core_keyword,
                seeds=body.seeds,
                location_code=market["location_code"],
                language_code=market["language_code"],
                volume=facts[cluster[0]].clickstream_volume or 0,
            )
            for cluster in clusters
        ]
        saved = await seo_keyword_clusters.upsert_many(db, user_id, site.id, drafts)
        await seo_keyword_clusters.mark_ranked(
            db, site.id, [r.id for r in saved if ours.intersection(r.keywords)]
        )
        await seo_cluster_competitors.link(
            db,
            [
                (r.id, competitor.id)
                for r in saved
                for competitor, keywords in rivals
                if keywords.intersection(r.keywords)
            ],
        )
        top = sorted(saved, key=lambda r: (-r.volume, r.main_keyword))[:TOP_CLUSTERS]
        return ClustersCreated(
            source=body.source,
            candidates=len(candidates),
            already_clustered=len(candidates) - len(fresh),
            noise=len(fresh) - len(meaningful),
            irrelevant=len(meaningful) - len(relevant),
            clusters=len(saved),
            top=[brief(r) for r in top],
        )

    async def compute_metrics(
        self,
        db: AsyncSession,
        caller: Caller,
        site: SiteRecord,
        cluster_ids: list[str] | None,
        limit: int,
    ) -> MetricsComputed:
        stale_before = datetime.now(UTC) - METRICS_TTL
        clusters = await seo_keyword_clusters.needing_metrics(
            db, site.id, cluster_ids, stale_before, limit
        )
        done: list[ClusterRecord] = []
        failed: list[str] = []
        for cluster in clusters:
            try:
                scored = await self._score(db, caller, site, cluster)
            except ProviderRequestError:
                failed.append(cluster.main_keyword)
                continue
            if scored is None:
                failed.append(cluster.main_keyword)
                continue
            done.append(scored)
        return MetricsComputed(computed=len(done), failed=failed, clusters=[brief(r) for r in done])

    async def rescore(
        self, db: AsyncSession, caller: Caller, site: SiteRecord, cluster_id: str
    ) -> ClusterRecord:
        cluster = await self.get(db, site.id, cluster_id)
        scored = await self._score(db, caller, site, cluster)
        if scored is None:
            raise HTTPException(502, f"No results page came back for {cluster.main_keyword}.")
        return (await self._with_competitors(db, [scored]))[0]

    async def _score(
        self, db: AsyncSession, caller: Caller, site: SiteRecord, cluster: ClusterRecord
    ) -> ClusterRecord | None:
        found = await self._metrics(db, caller, own_domain(site.domain), cluster)
        if found is None:
            return None
        metrics, serp_domains = found
        saved = await seo_competitors.list(db, site.id)
        await seo_cluster_competitors.link(
            db,
            [
                (cluster.id, c.id)
                for c in saved
                if any(belongs_to(d, c.domain) for d in serp_domains)
            ],
        )
        return await seo_keyword_clusters.set_metrics(db, site.id, cluster.id, metrics)

    async def _with_competitors(
        self, db: AsyncSession, records: list[ClusterRecord]
    ) -> list[ClusterRecord]:
        domains = await seo_cluster_competitors.domains_by_cluster(db, [r.id for r in records])
        return [r.model_copy(update={"competitors": domains.get(r.id, [])}) for r in records]

    async def _search_console_queries(self, db: AsyncSession, site_id: str) -> set[str]:
        totals = await site_search_dailies.query_window_totals(db, site_id)
        return {normalize_keyword(t.query) for t in totals}

    async def _top_search_console_queries(
        self, db: AsyncSession, site_id: str, limit: int
    ) -> list[str]:
        totals = await site_search_dailies.query_window_totals(db, site_id)
        ordered = sorted(
            totals,
            key=lambda t: -(t.impressions_28d + t.impressions_prev_28d + t.impressions_ly_28d),
        )
        return [t.query for t in ordered][:limit]

    async def _ranked(
        self, db: AsyncSession, caller: Caller, domain: str, market: dict
    ) -> set[str]:
        return {
            normalize_keyword(r["keyword"])
            for r in await self._rankings(db, caller, domain, market)
        }

    async def _ranked_by_traffic(
        self, db: AsyncSession, caller: Caller, domain: str, market: dict, limit: int
    ) -> list[str]:
        rankings = await self._rankings(db, caller, domain, market)
        ordered = sorted(rankings, key=lambda r: -(r.get("etv") or 0))
        return [r["keyword"] for r in ordered][:limit]

    async def _rankings(
        self, db: AsyncSession, caller: Caller, domain: str, market: dict
    ) -> list[dict]:
        await db.commit()
        pulled = await seo_data.ranked_keywords(
            caller,
            domain,
            RANKED_PULL,
            location_code=market["location_code"],
            language_code=market["language_code"],
        )
        return pulled["rankings"]

    async def _competitor_keywords(
        self, db: AsyncSession, caller: Caller, site_id: str, market: dict
    ) -> list[tuple[CompetitorRecord, set[str]]]:
        saved = (await seo_competitors.list(db, site_id))[:MAX_COMPETITORS_READ]
        return [(c, await self._ranked(db, caller, c.domain, market)) for c in saved]

    async def _facts(
        self, db: AsyncSession, caller: Caller, keywords: list[str], market: dict
    ) -> dict[str, KeywordFacts]:
        if not keywords:
            return {}
        await db.commit()
        items = await seo_data.keyword_overview(caller, keywords, market)
        facts = [keyword_facts(i) for i in items]
        return {f.keyword: f for f in facts if f.keyword}

    async def _metrics(
        self, db: AsyncSession, caller: Caller, site_domain: str, cluster: ClusterRecord
    ) -> tuple[ClusterMetrics, set[str]] | None:
        market = {"location_code": cluster.location_code, "language_code": cluster.language_code}
        await db.commit()
        serp = await seo_data.serp_organic(
            caller, cluster.main_keyword, SERP_DEVICE, SERP_DEPTH, market, ttl=SERP_TTL
        )
        if serp is None:
            return None
        organic = sorted(
            (
                {
                    "position": int(i["rank_group"]),
                    "url": str(i["url"]),
                    "domain": own_domain(i["url"]),
                    "title": i.get("title"),
                    "description": i.get("description"),
                }
                for i in serp.get("items") or []
                if isinstance(i, dict)
                and i.get("type") == "organic"
                and i.get("url")
                and isinstance(i.get("rank_group"), int)
            ),
            key=lambda r: r["position"],
        )
        ours = next((r for r in organic if belongs_to(r["domain"], site_domain)), None)
        start = ours["position"] if ours else TOP_N + 1
        above = [
            r for r in organic if r["position"] < start and not belongs_to(r["domain"], site_domain)
        ]

        our_target = ours["url"] if ours else f"https://{site_domain}/"
        ranks = await seo_data.pages_summary(caller, [r["url"] for r in above] + [our_target])

        def rank_of(url: str) -> dict:
            return (
                ranks.get(url)
                or ranks.get(url.rstrip("/"))
                or ranks.get(f"{url.rstrip('/')}/")
                or {}
            )

        mine = rank_of(our_target)
        our_strength = (
            strength(mine.get("rank"), mine.get("main_domain_rank"))
            if ours
            else (1 - PAGE_WEIGHT) * (mine.get("main_domain_rank") or 0)
        )
        theirs = [
            strength(rank_of(r["url"]).get("rank"), rank_of(r["url"]).get("main_domain_rank"))
            for r in above
        ]
        flattened = smoothed(theirs)
        await db.commit()
        fits = await intent_fits(caller, cluster.main_keyword, above)

        passes = [1.0] * (start - 1)
        climb_rows = []
        for result, raw, smooth, fit in zip(above, theirs, flattened, fits, strict=True):
            chance = pass_chance(smooth, our_strength, fit)
            passes[result["position"] - 1] = chance
            facts = rank_of(result["url"])
            climb_rows.append(
                {
                    "position": result["position"],
                    "url": result["url"],
                    "domain": result["domain"],
                    "title": result["title"],
                    "pageRank": whole(facts.get("rank")),
                    "domainRank": whole(facts.get("main_domain_rank")),
                    "strength": round(raw, 1),
                    "smoothedStrength": round(smooth, 1),
                    "intentFit": fit,
                    "passChance": round(chance, 3),
                }
            )
        outcome = climb(passes, start)
        top_fits = fits[:TOP_N]
        metrics = ClusterMetrics(
            winnability=outcome["winnability"],
            p_top_three=round(outcome["p_top_three"], 4),
            p_page_one=round(outcome["p_page_one"], 4),
            likely_position=outcome["likely_position"],
            our_position=ours["position"] if ours else None,
            our_url=ours["url"] if ours else None,
            our_strength=round(our_strength, 1),
            intent_fit=round(sum(top_fits) / len(top_fits), 3) if top_fits else None,
            climb=climb_rows,
        )
        return metrics, {r["domain"] for r in organic}


keyword_cluster_service = KeywordClusterService()
