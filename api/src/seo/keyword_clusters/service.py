from __future__ import annotations

import math
import random

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.providers.registry import Caller
from src.providers.seo_data.service import seo_data
from src.seo.keyword_clusters.constants import (
    CLUSTER_NOT_FOUND,
    COMPETITOR_KEYWORDS_PER_CLUSTER,
    DISCOVERED_FROM_SEEDS,
    KEYWORD_NOT_IN_CLUSTER,
    MAIN_KEYWORD_STAYS,
    MAX_COMPETITOR_KEYWORDS_PER_DOMAIN,
    MIN_COMPETITOR_KEYWORDS_PER_DOMAIN,
    NO_SAVED_COMPETITORS,
    NOISE_SHARE_OF_CORE,
    RELEVANCE_ROUND,
)
from src.seo.keyword_clusters.judging import (
    label_keywords,
    relevant_keywords,
    split_groups,
)
from src.seo.keyword_clusters.repository import seo_keyword_clusters
from src.seo.keyword_clusters.schemas import (
    ClusterDeleted,
    ClusterDraft,
    ClusterFilters,
    ClusterRecord,
    ClustersDeleted,
    ClustersDeleteRequest,
    CompetitorClustersRequest,
    KeywordFacts,
    KeywordsClusterRequest,
    SearchConsoleClustersRequest,
    SeedClustersRequest,
    normalize_keyword,
)
from src.seo.market import markets
from src.seo.site_search.repositories.site_search_daily import site_search_dailies
from src.seo.site_seo.competitor_repository import site_competitors
from src.sites.schemas import SiteRecord


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


def website_of(site: SiteRecord) -> dict[str, str]:
    return {"domain": site.domain, "about": site.summary or ""}


def cluster_volume(
    members: list[str], existing: ClusterRecord | None, facts: dict[str, KeywordFacts]
) -> int:
    added = members[1:] if existing else members
    return (existing.volume if existing else 0) + sum(
        facts[k].clickstream_volume or 0 for k in added
    )


def cluster_ids_of(keywords: list[str], records: list[ClusterRecord]) -> dict[str, str]:
    wanted = set(keywords)
    found: dict[str, str] = {}
    for record in records:
        for keyword in record.keywords:
            if keyword in wanted:
                found.setdefault(keyword, record.id)
    return found


def rows_per_competitor(limit: int, competitors: int) -> int:
    wanted = math.ceil(COMPETITOR_KEYWORDS_PER_CLUSTER * limit / max(competitors, 1))
    return min(MAX_COMPETITOR_KEYWORDS_PER_DOMAIN, max(MIN_COMPETITOR_KEYWORDS_PER_DOMAIN, wanted))


def by_volume(records: list[ClusterRecord]) -> list[ClusterRecord]:
    return sorted(records, key=lambda r: (-r.volume, r.main_keyword))


class KeywordClusterService:
    async def get(self, db: AsyncSession, site_id: str, cluster_id: str) -> ClusterRecord:
        found = await seo_keyword_clusters.get(db, site_id, cluster_id)
        if found is None:
            raise HTTPException(404, CLUSTER_NOT_FOUND)
        return found

    async def list(
        self, db: AsyncSession, site_id: str, filters: ClusterFilters, paging: PaginationParams
    ) -> PaginatedApiResponse[ClusterRecord]:
        return await seo_keyword_clusters.list(db, site_id, filters, paging)

    async def delete(self, db: AsyncSession, site_id: str, cluster_id: str) -> None:
        if not await seo_keyword_clusters.delete(db, site_id, cluster_id):
            raise HTTPException(404, CLUSTER_NOT_FOUND)

    async def delete_many(
        self, db: AsyncSession, site: SiteRecord, body: ClustersDeleteRequest
    ) -> ClustersDeleted:
        found = {
            c.id: c for c in await seo_keyword_clusters.get_many(db, site.id, body.cluster_ids)
        }
        unclustered: list[str] = []
        market = markets(site.markets, site.language)[0]
        for keyword in body.keywords:
            cluster = await seo_keyword_clusters.containing(
                db, site.id, keyword, market["location_code"], market["language_code"]
            )
            if cluster is None:
                unclustered.append(keyword)
            else:
                found.setdefault(cluster.id, cluster)
        await seo_keyword_clusters.delete_many(db, site.id, list(found))
        return ClustersDeleted(
            deleted=[
                ClusterDeleted(id=c.id, main_keyword=c.main_keyword, keywords=c.keywords)
                for c in found.values()
            ],
            missing_ids=[i for i in body.cluster_ids if i not in found],
            unclustered_keywords=unclustered,
        )

    async def remove_keywords(
        self,
        db: AsyncSession,
        caller: Caller,
        site_id: str,
        cluster_id: str,
        body: KeywordsClusterRequest,
    ) -> ClusterRecord:
        cluster = await self.get(db, site_id, cluster_id)
        keywords = body.keywords
        absent = [k for k in keywords if k not in cluster.keywords]
        if absent:
            raise HTTPException(404, KEYWORD_NOT_IN_CLUSTER.format(keywords=", ".join(absent)))
        if cluster.main_keyword in keywords:
            raise HTTPException(409, MAIN_KEYWORD_STAYS.format(keyword=cluster.main_keyword))
        market = {"location_code": cluster.location_code, "language_code": cluster.language_code}
        facts = await self._facts(db, caller, keywords, market)
        removed = sum(facts[k].clickstream_volume or 0 for k in keywords if k in facts)
        remaining = [k for k in cluster.keywords if k not in keywords]
        searched = await self._search_console_queries(db, site_id)
        updated = await seo_keyword_clusters.set_members(
            db,
            site_id,
            cluster_id,
            remaining,
            max(cluster.volume - removed, 0),
            bool(searched.intersection(remaining)),
        )
        return updated

    async def from_search_console(
        self,
        db: AsyncSession,
        caller: Caller,
        user_id: str,
        site: SiteRecord,
        body: SearchConsoleClustersRequest,
    ) -> list[str]:
        totals = await site_search_dailies.query_window_totals(db, site.id)
        ordered = sorted(
            totals,
            key=lambda t: -(t.impressions_28d + t.impressions_prev_28d + t.impressions_ly_28d),
        )
        raw = [t.query for t in ordered][: body.limit]
        saved = await self._cluster(db, caller, user_id, site, raw, [], body.min_volume)
        return [r.main_keyword for r in by_volume(saved)]

    async def from_seeds(
        self,
        db: AsyncSession,
        caller: Caller,
        user_id: str,
        site: SiteRecord,
        body: SeedClustersRequest,
    ) -> list[str]:
        market = markets(site.markets, site.language)[0]
        await db.commit()
        discovered = await seo_data.discover_keywords(
            caller, body.seeds, DISCOVERED_FROM_SEEDS, market
        )
        raw = [*body.seeds, *discovered]
        saved = await self._cluster(db, caller, user_id, site, raw, body.seeds, body.min_volume)
        return [r.main_keyword for r in by_volume(saved)]

    async def _cluster(
        self,
        db: AsyncSession,
        caller: Caller,
        user_id: str,
        site: SiteRecord,
        raw: list[str],
        seeds: list[str],
        min_volume: int | None,
    ) -> list[ClusterRecord]:
        market = markets(site.markets, site.language)[0]
        candidates = [k for k in dict.fromkeys(normalize_keyword(r) for r in raw) if k]
        clustered = await seo_keyword_clusters.clustered_keywords(
            db, site.id, market["location_code"], market["language_code"]
        )
        fresh = [k for k in candidates if k not in clustered]

        await db.commit()
        relevant = await relevant_keywords(caller, website_of(site), seeds, fresh)
        facts, meaningful = await self._meaningful(db, caller, relevant, market, min_volume)

        return await self._place(db, caller, user_id, site, market, meaningful, facts, seeds)

    async def from_competitors(
        self,
        db: AsyncSession,
        caller: Caller,
        user_id: str,
        site: SiteRecord,
        body: CompetitorClustersRequest,
    ) -> list[str]:
        competitors = await site_competitors.list(db, site.id)
        if not competitors:
            raise HTTPException(409, NO_SAVED_COMPETITORS)
        market = markets(site.markets, site.language)[0]
        await db.commit()
        rows = rows_per_competitor(body.limit, len(competitors))
        ranked: dict[str, None] = {}
        for competitor in competitors:
            pulled = await seo_data.ranked_keywords(
                caller,
                competitor.domain,
                rows,
                [],
                market["location_code"],
                market["language_code"],
            )
            ranked.update(
                dict.fromkeys(normalize_keyword(r["keyword"]) for r in pulled["rankings"])
            )
        candidates = [k for k in ranked if k]

        impressed = {
            normalize_keyword(q)
            for q in await site_search_dailies.queries_with_impressions(db, site.id, body.lookback)
        }
        unseen = [k for k in candidates if k not in impressed]
        clustered = await seo_keyword_clusters.clustered_keywords(
            db, site.id, market["location_code"], market["language_code"]
        )
        fresh = [k for k in unseen if k not in clustered]

        random.shuffle(fresh)
        website = website_of(site)
        facts: dict[str, KeywordFacts] = {}
        picked: list[str] = []
        judged = 0
        while len(picked) < body.limit and judged < len(fresh):
            batch = fresh[judged : judged + RELEVANCE_ROUND]
            judged += len(batch)
            await db.commit()
            relevant = await relevant_keywords(caller, website, [], batch)
            found, meaningful = await self._meaningful(
                db, caller, relevant, market, body.min_volume
            )
            facts.update(found)
            picked.extend(meaningful)
        picked = picked[: body.limit]

        drafts = [
            ClusterDraft(
                main_keyword=k,
                keywords=[k],
                core_keyword=facts[k].core_keyword,
                seeds=[],
                location_code=market["location_code"],
                language_code=market["language_code"],
                volume=facts[k].clickstream_volume or 0,
            )
            for k in picked
        ]
        saved = await self._save(db, caller, user_id, site, drafts)
        searched = await self._search_console_queries(db, site.id)
        await seo_keyword_clusters.mark_ranked(
            db, site.id, [r.id for r in saved if searched.intersection(r.keywords)]
        )
        return [r.main_keyword for r in by_volume(saved)]

    async def add_keywords(
        self,
        db: AsyncSession,
        caller: Caller,
        user_id: str,
        site: SiteRecord,
        body: KeywordsClusterRequest,
    ) -> list[tuple[str, str]]:
        market = markets(site.markets, site.language)[0]
        location_code, language_code = market["location_code"], market["language_code"]
        keywords = body.keywords
        existing = await seo_keyword_clusters.containing_any(
            db, site.id, keywords, location_code, language_code
        )
        placed = cluster_ids_of(keywords, existing)
        missing = [k for k in keywords if k not in placed]
        if missing:
            facts = await self._facts(db, caller, missing, market)
            for keyword in missing:
                facts.setdefault(keyword, KeywordFacts(keyword=keyword))
            cores = {facts[k].core_keyword for k in missing} - {None, *missing}
            clustered = await seo_keyword_clusters.clustered_keywords(
                db, site.id, location_code, language_code
            )
            new_cores = sorted(c for c in cores if c not in clustered)
            facts.update(await self._facts(db, caller, new_cores, market))
            for core in new_cores:
                facts.setdefault(core, KeywordFacts(keyword=core, core_keyword=core))
            members = [*missing, *new_cores]
            saved = await self._place(db, caller, user_id, site, market, members, facts, [])
            placed.update(cluster_ids_of(missing, saved))
        return [(k, placed[k]) for k in keywords]

    async def _place(
        self,
        db: AsyncSession,
        caller: Caller,
        user_id: str,
        site: SiteRecord,
        market: dict,
        keywords: list[str],
        facts: dict[str, KeywordFacts],
        seeds: list[str],
    ) -> list[ClusterRecord]:
        groups: dict[str, list[str]] = {}
        for keyword in keywords:
            groups.setdefault(facts[keyword].core_keyword or keyword, []).append(keyword)
        existing = await seo_keyword_clusters.with_cores(
            db, site.id, market["location_code"], market["language_code"], list(groups)
        )
        by_main = {c.main_keyword: c for c in existing}
        leaders: dict[str, list[str]] = {}
        for cluster in existing:
            leaders.setdefault(cluster.core_keyword or "", []).append(cluster.main_keyword)
        ordered = [
            (
                sorted(members, key=lambda k: (-(facts[k].clickstream_volume or 0), k)),
                leaders.get(core, []),
            )
            for core, members in groups.items()
        ]
        await db.commit()
        clusters = await split_groups(caller, ordered)

        drafts = [
            ClusterDraft(
                main_keyword=cluster[0],
                keywords=cluster,
                core_keyword=(
                    by_main[cluster[0]].core_keyword
                    if cluster[0] in by_main
                    else facts[cluster[0]].core_keyword
                ),
                seeds=seeds,
                location_code=market["location_code"],
                language_code=market["language_code"],
                volume=cluster_volume(cluster, by_main.get(cluster[0]), facts),
            )
            for cluster in clusters
        ]
        saved = await self._save(db, caller, user_id, site, drafts)
        searched = await self._search_console_queries(db, site.id)
        await seo_keyword_clusters.mark_ranked(
            db, site.id, [r.id for r in saved if searched.intersection(r.keywords)]
        )
        return saved

    async def _save(
        self,
        db: AsyncSession,
        caller: Caller,
        user_id: str,
        site: SiteRecord,
        drafts: list[ClusterDraft],
    ) -> list[ClusterRecord]:
        if not drafts:
            return []
        labelled = await seo_keyword_clusters.labelled_mains(
            db,
            site.id,
            drafts[0].location_code,
            drafts[0].language_code,
            [d.main_keyword for d in drafts],
        )
        unlabelled = [d.main_keyword for d in drafts if d.main_keyword not in labelled]
        await db.commit()
        labels = await label_keywords(caller, website_of(site), unlabelled) if unlabelled else {}
        drafts = [
            d.model_copy(update=labels[d.main_keyword].model_dump())
            if d.main_keyword in labels
            else d
            for d in drafts
        ]
        return await seo_keyword_clusters.upsert_many(db, user_id, site.id, drafts)

    async def _search_console_queries(self, db: AsyncSession, site_id: str) -> set[str]:
        totals = await site_search_dailies.query_window_totals(db, site_id)
        return {normalize_keyword(t.query) for t in totals}

    async def _meaningful(
        self,
        db: AsyncSession,
        caller: Caller,
        keywords: list[str],
        market: dict,
        min_volume: int | None,
    ) -> tuple[dict[str, KeywordFacts], list[str]]:
        facts = await self._facts(db, caller, keywords, market)
        cores = {f.core_keyword or f.keyword for f in facts.values()}
        missing_cores = [c for c in cores if c not in facts]
        core_facts = {**facts, **await self._facts(db, caller, missing_cores, market)}

        def threshold(fact: KeywordFacts) -> float:
            if min_volume is not None:
                return min_volume
            core = core_facts.get(fact.core_keyword or fact.keyword)
            core_volume = (core.ads_volume if core else None) or fact.ads_volume or 0
            return max(NOISE_SHARE_OF_CORE * core_volume, 1)

        meaningful = [
            f.keyword
            for f in facts.values()
            if f.clickstream_volume is not None and f.clickstream_volume >= threshold(f)
        ]
        return facts, meaningful

    async def _facts(
        self, db: AsyncSession, caller: Caller, keywords: list[str], market: dict
    ) -> dict[str, KeywordFacts]:
        if not keywords:
            return {}
        await db.commit()
        items = await seo_data.keyword_overview(caller, keywords, market)
        facts = [keyword_facts(i) for i in items]
        return {f.keyword: f for f in facts if f.keyword}


keyword_cluster_service = KeywordClusterService()
