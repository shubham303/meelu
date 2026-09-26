from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.context import tenant_names
from src.agent.workspace import workspace_tables
from src.providers.errors import ConflictError, SpendCeilingError
from src.providers.registry import Caller, SpendMeter
from src.providers.seo_data.service import seo_data
from src.providers.seo_data.shape import own_domain
from src.seo.clusters.repository import seo_keyword_clusters
from src.seo.collect.schemas import (
    CollectCompetitorKeywordsRequest,
    CollectCompetitorsRequest,
    CollectKeywordsRequest,
    CollectResult,
    CollectSerpsRequest,
)
from src.seo.common import fields
from src.seo.competitor_keywords.repository import seo_competitor_keywords
from src.seo.competitors.repository import seo_competitors
from src.seo.constants import (
    FACTS_FRESH_DAYS,
    MAX_BRAND_TERMS,
    RANKED_FRESH_DAYS,
    RIVALS_FRESH_DAYS,
    SERP_FRESH_DAYS,
    SERP_KEEP,
)
from src.seo.jobs.repository import seo_jobs
from src.seo.jobs.service import seo_job_service
from src.seo.keywords.repository import seo_keywords
from src.seo.keywords.schemas import KeywordRecord
from src.seo.page_suggestions.repository import seo_page_suggestions
from src.seo.precompute.embed import seo_embed_service
from src.seo.serp_results.repository import seo_serp_results
from src.seo.serp_snapshots.repository import seo_serp_snapshots
from src.seo.state.repository import seo_site_states
from src.sites.repository import sites


def _now() -> datetime:
    return datetime.now(UTC)


def _meter(job) -> SpendMeter:
    if job.vendor_ceiling_micros <= 0:
        return SpendMeter()
    remaining = job.vendor_ceiling_micros - job.vendor_micros
    if remaining <= 0:
        raise SpendCeilingError(job.vendor_micros, job.vendor_ceiling_micros)
    return SpendMeter(ceiling_micros=remaining)


def _caller(user_id: str, site_id: str, meter: SpendMeter) -> Caller:
    return Caller(user_id=user_id, site_id=site_id, spend=meter)


class SeoCollectService:
    async def _settle(
        self, db: AsyncSession, job_id: str, meter: SpendMeter, result: CollectResult
    ) -> CollectResult:
        await seo_jobs.add_spend(db, job_id, meter.calls, meter.micros)
        result.vendor_calls = meter.calls
        result.spent_micros = meter.micros
        result.cache_hits = meter.cache_hits
        return result

    async def workspace_keywords(self, db: AsyncSession, user_id: str, table: str) -> list[str]:
        _, schema = tenant_names(user_id)
        rows = await workspace_tables.rows(db, schema, table)
        values = dict.fromkeys(r.get("keyword") for r in rows)
        return fields.keywords([v for v in values if v is not None])

    async def default_seeds(self, db: AsyncSession, site_id: str, limit: int) -> list[str]:
        queries = await seo_keywords.top_query_terms(db, site_id, limit)
        clusters = await seo_keyword_clusters.list_owned(db, site_id)
        heads = {
            k.id: k
            for k in await seo_keywords.list_by_ids(
                db, site_id, [c.head_keyword_id for c in clusters]
            )
        }
        head_terms = [
            heads[c.head_keyword_id].keyword
            for c in clusters
            if c.head_keyword_id in heads and not heads[c.head_keyword_id].branded
        ][:limit]
        return fields.keywords(queries + head_terms)[:limit]

    async def site_domain(self, db: AsyncSession, user_id: str, site_id: str) -> str | None:
        site = await sites.get(db, user_id, site_id)
        return None if site is None else site.domain

    async def keywords_in_order(
        self, db: AsyncSession, site_id: str, keyword_ids: list[str]
    ) -> list[KeywordRecord]:
        found = {k.id: k for k in await seo_keywords.list_by_ids(db, site_id, keyword_ids)}
        return [found[i] for i in keyword_ids if i in found]

    async def stale_keywords(self, db: AsyncSession, site_id: str, ids: list[str]) -> list[str]:
        cutoff = _now() - timedelta(days=FACTS_FRESH_DAYS)
        return await seo_keywords.stale_terms(db, site_id, ids, cutoff)

    async def apply_facts(self, db: AsyncSession, site_id: str, facts: list[dict[str, Any]]) -> int:
        at = _now()
        params = [
            {
                "site_id": site_id,
                "keyword": f["keyword"],
                "volume": f.get("volume"),
                "difficulty": f.get("difficulty"),
                "cpc": f.get("cpc"),
                "intent": f.get("intent"),
                "at": at,
            }
            for f in facts
            if f.get("keyword")
        ]
        await seo_keywords.apply_facts(db, params)
        return len(params)

    async def gather_keywords(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        job_id: str,
        seeds: list[str] | None,
        keyword_ids: list[str] | None,
        source_table: str | None,
        from_gsc: bool,
        from_ranked: bool,
        max_seeds: int,
        ideas_per_seed: int,
        dry_run: bool,
    ) -> CollectResult:
        job = await seo_jobs.get(db, site_id, job_id)
        assert job is not None
        state = await seo_site_states.ensure(db, user_id, site_id)
        site = await self.site_domain(db, user_id, site_id)
        meter = _meter(job)
        caller = _caller(user_id, site_id, meter)
        result = CollectResult()
        locale = {"location_code": state.location_code, "language_code": state.language_code}

        wanted: list[str] = []
        if keyword_ids:
            wanted += await self.stale_keywords(db, site_id, keyword_ids)
        if source_table:
            table_terms = await self.workspace_keywords(
                db, user_id, fields.workspace_table(source_table)
            )
            added = await seo_keywords.insert_many(db, user_id, site_id, table_terms, "user")
            result.added += len(added)
            wanted += table_terms

        seed_terms = fields.keywords(seeds or [])
        if not seed_terms and not keyword_ids and not source_table and from_gsc:
            seed_terms = await self.default_seeds(db, site_id, max_seeds)
        seed_terms = seed_terms[:max_seeds]

        plan = {
            "ideas_seeds": len(seed_terms),
            "ranked": bool(from_ranked and site),
            "facts_pending": len(set(wanted)),
        }
        if dry_run:
            result.plan = plan
            return result

        if from_ranked and site:
            ranked = await seo_data.ranked_keywords(
                db,
                caller,
                site,
                limit=500,
                exclude_brand_terms=list(state.brand_terms)[:MAX_BRAND_TERMS],
                **locale,
            )
            rows = ranked.get("rankings") or []
            added = await seo_keywords.insert_many(
                db, user_id, site_id, fields.keywords([r["keyword"] for r in rows]), "ranked"
            )
            result.added += len(added)
            at = _now()
            if rows:
                await seo_keywords.apply_ranked(
                    db,
                    [
                        {
                            "site_id": site_id,
                            "keyword": fields.keyword(r["keyword"]),
                            "position": r.get("rankGroup"),
                            "url": r.get("url"),
                            "volume": r.get("volume"),
                            "difficulty": r.get("difficulty"),
                            "cpc": r.get("cpc"),
                            "intent": r.get("intent"),
                            "at": at,
                        }
                        for r in rows
                    ],
                )
                result.refreshed += len(rows)

        for seed in seed_terms:
            seed_id = (await seo_keywords.ids_for(db, site_id, [seed])).get(seed)
            if seed_id is None:
                seed_id = (
                    await seo_keywords.insert_many(db, user_id, site_id, [seed], "user") or [None]
                )[0]
            ideas = await seo_data.keyword_ideas(db, caller, [seed], limit=ideas_per_seed, **locale)
            rows = ideas.get("ideas") or []
            terms = fields.keywords([r["keyword"] for r in rows])
            added = await seo_keywords.insert_many(
                db, user_id, site_id, terms, "ideas", seed_keyword_id=seed_id
            )
            result.added += len(added)
            result.refreshed += await self.apply_facts(db, site_id, rows)
            wanted.append(seed)

        ids = list((await seo_keywords.ids_for(db, site_id, fields.keywords(wanted))).values())
        stale = await self.stale_keywords(db, site_id, ids) if ids else []
        if stale:
            facts = await seo_data.keyword_facts(db, caller, sorted(stale), **locale)
            result.refreshed += await self.apply_facts(db, site_id, facts.get("facts") or [])

        await db.flush()
        result.embedded = await seo_embed_service.embed_pending(db, user_id, site_id)
        return await self._settle(db, job_id, meter, result)

    async def _collect_competitors(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        job_id: str,
        limit: int,
        keyword_ids: list[str] | None,
    ) -> CollectResult:
        job = await seo_jobs.get(db, site_id, job_id)
        assert job is not None
        state = await seo_site_states.ensure(db, user_id, site_id)
        site = await self.site_domain(db, user_id, site_id)
        meter = _meter(job)
        caller = _caller(user_id, site_id, meter)
        result = CollectResult()
        locale = {"location_code": state.location_code, "language_code": state.language_code}
        fresh = [
            c
            for c in await seo_competitors.list(db, site_id, None)
            if c.fetched_at and c.fetched_at > _now() - timedelta(days=RIVALS_FRESH_DAYS)
        ]
        if fresh and not keyword_ids:
            result.competitors = [c.domain for c in fresh][:limit]
            return await self._settle(db, job_id, meter, result)

        found: dict[str, dict[str, Any]] = {}
        if site:
            rivals = await seo_data.rival_domains(db, caller, site, limit=limit, **locale)
            for r in rivals.get("rivals") or []:
                found[r["domain"]] = {
                    "first_source": "rival",
                    "intersections": r.get("intersections"),
                    "avg_position": r.get("avgPosition"),
                }
        if keyword_ids:
            terms = [k.keyword for k in await self.keywords_in_order(db, site_id, keyword_ids)]
        else:
            terms = await self.default_seeds(db, site_id, 20)
        if terms:
            sampled = await seo_data.serp_competitors(db, caller, terms, limit=limit, **locale)
            for c in sampled.get("competitors") or []:
                domain = c["domain"]
                if domain == own_domain(site or ""):
                    continue
                found.setdefault(
                    domain,
                    {
                        "first_source": "serp",
                        "intersections": c.get("keywordsCount"),
                        "avg_position": c.get("avgPosition"),
                    },
                )
        at = _now()
        for domain, values in list(found.items())[:limit]:
            brand = fields.brand_terms([domain.split(".")[0]])
            await seo_competitors.upsert(
                db,
                user_id,
                site_id,
                {"domain": domain, "brand_terms": brand, "fetched_at": at, **values},
            )
            result.added += 1
            result.competitors.append(domain)
        return await self._settle(db, job_id, meter, result)

    async def _collect_competitor_keywords(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        job_id: str,
        competitor_ids: list[str] | None,
        limit: int,
    ) -> CollectResult:
        job = await seo_jobs.get(db, site_id, job_id)
        assert job is not None
        state = await seo_site_states.ensure(db, user_id, site_id)
        meter = _meter(job)
        caller = _caller(user_id, site_id, meter)
        result = CollectResult()
        locale = {"location_code": state.location_code, "language_code": state.language_code}
        cutoff = _now() - timedelta(days=RANKED_FRESH_DAYS)
        competitors = [
            c
            for c in await seo_competitors.list(db, site_id, "confirmed")
            if (not competitor_ids or c.id in competitor_ids)
        ]
        for competitor in competitors:
            latest = await seo_competitor_keywords.latest_fetched_at(db, competitor.id)
            if latest and latest > cutoff:
                continue
            ranked = await seo_data.ranked_keywords(
                db,
                caller,
                competitor.domain,
                limit=limit,
                exclude_brand_terms=list(competitor.brand_terms)[:MAX_BRAND_TERMS],
                **locale,
            )
            rows = [
                r for r in ranked.get("rankings") or [] if (r.get("intent") or "") != "navigational"
            ]
            terms = fields.keywords([r["keyword"] for r in rows])
            added = await seo_keywords.insert_many(db, user_id, site_id, terms, "competitor")
            result.added += len(added)
            result.refreshed += await self.apply_facts(
                db,
                site_id,
                [r for r in rows if r.get("volume") is not None or r.get("difficulty") is not None],
            )
            ids = await seo_keywords.ids_for(db, site_id, terms)
            at = _now()
            await seo_competitor_keywords.upsert_many(
                db,
                user_id,
                site_id,
                competitor.id,
                [
                    {
                        "keyword_id": ids[fields.keyword(r["keyword"])],
                        "position": r.get("rankGroup"),
                        "url": r.get("url"),
                        "etv": r.get("etv"),
                    }
                    for r in rows
                    if fields.keyword(r["keyword"]) in ids
                ],
                at,
            )
            await seo_competitors.patch(db, site_id, competitor.id, {"fetched_at": at})
        await db.flush()
        result.embedded = await seo_embed_service.embed_pending(db, user_id, site_id)
        return await self._settle(db, job_id, meter, result)

    async def resolve_serp_targets(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        job_id: str,
        keyword_ids: list[str] | None,
        terms: list[str] | None,
        suggestion_ids: list[str] | None,
        source_table: str | None,
    ) -> list[str]:
        ids: list[str] = list(keyword_ids or [])
        if terms:
            cleaned = fields.keywords(terms)
            await seo_keywords.insert_many(db, user_id, site_id, cleaned, "user")
            ids += list((await seo_keywords.ids_for(db, site_id, cleaned)).values())
        if source_table:
            cleaned = await self.workspace_keywords(
                db, user_id, fields.workspace_table(source_table)
            )
            await seo_keywords.insert_many(db, user_id, site_id, cleaned, "user")
            ids += list((await seo_keywords.ids_for(db, site_id, cleaned)).values())
        if suggestion_ids:
            topics = await seo_page_suggestions.topic_keys(db, site_id, suggestion_ids)
            ids += list((await seo_keywords.ids_for(db, site_id, topics)).values())
        if not ids and not (keyword_ids or terms or source_table or suggestion_ids):
            topics = await seo_page_suggestions.job_topic_keys(
                db, site_id, job_id, ("draft", "reviewed")
            )
            heads = await seo_keywords.ids_for(db, site_id, topics)
            ids = [heads[t] for t in topics if t in heads]
        return list(dict.fromkeys(ids))

    async def _collect_serps(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        job_id: str,
        keyword_ids: list[str] | None,
        terms: list[str] | None,
        suggestion_ids: list[str] | None,
        source_table: str | None,
        device: str,
        max_keywords: int,
    ) -> CollectResult:
        job = await seo_jobs.get(db, site_id, job_id)
        assert job is not None
        state = await seo_site_states.ensure(db, user_id, site_id)
        site = own_domain(await self.site_domain(db, user_id, site_id) or "")
        meter = _meter(job)
        caller = _caller(user_id, site_id, meter)
        result = CollectResult()
        locale = {"location_code": state.location_code, "language_code": state.language_code}
        targets = await self.resolve_serp_targets(
            db, user_id, site_id, job_id, keyword_ids, terms, suggestion_ids, source_table
        )
        if len(targets) > max_keywords:
            raise ConflictError(
                f"{len(targets)} keywords asked but max is {max_keywords}; narrow the set or raise max."
            )
        cutoff = _now() - timedelta(days=SERP_FRESH_DAYS)
        fresh = await seo_serp_snapshots.fresh_keyword_ids(db, site_id, device, cutoff, targets)
        result.skipped += len([t for t in targets if t in fresh])
        for keyword in await self.keywords_in_order(
            db, site_id, [t for t in targets if t not in fresh]
        ):
            keyword_id = keyword.id
            snapshot = (
                await seo_data.serp_snapshot(
                    db, caller, keyword.keyword, device=device, depth=10, **locale
                )
            ).get("snapshot") or {}
            at = _now()
            saved = await seo_serp_snapshots.create(
                db,
                user_id,
                site_id,
                keyword_id,
                device,
                at,
                [t for t in snapshot.get("itemTypes") or []],
            )
            await seo_serp_results.create_many(
                db,
                user_id,
                site_id,
                saved.id,
                at,
                [
                    {
                        "rank": r["rankAbsolute"],
                        "domain": own_domain(r.get("domain") or ""),
                        "url": r.get("url") or "",
                        "title": r.get("title"),
                        "description": r.get("description"),
                        "is_ours": bool(site) and own_domain(r.get("domain") or "") == site,
                    }
                    for r in snapshot.get("results") or []
                    if r.get("type") == "organic" and r.get("url")
                ][:10],
            )
            for source, values in (
                ("serp_paa", snapshot.get("questions") or []),
                ("serp_related", snapshot.get("relatedSearches") or []),
            ):
                added = await seo_keywords.insert_many(
                    db,
                    user_id,
                    site_id,
                    fields.keywords(values),
                    source,
                    seed_keyword_id=keyword_id,
                )
                result.added += len(added)
            await seo_serp_snapshots.prune(db, site_id, keyword_id, SERP_KEEP)
            result.refreshed += 1
        await db.flush()
        result.embedded = await seo_embed_service.embed_pending(db, user_id, site_id)
        return await self._settle(db, job_id, meter, result)

    async def collect_keywords(
        self, db: AsyncSession, user_id: str, site_id: str, body: CollectKeywordsRequest
    ) -> CollectResult:
        await seo_job_service.get(db, site_id, body.job_id)
        return await self.gather_keywords(
            db,
            user_id,
            site_id,
            body.job_id,
            body.seeds,
            body.keyword_ids,
            body.source_table,
            body.from_gsc,
            body.from_ranked,
            body.max_seeds,
            body.ideas_per_seed,
            body.dry_run,
        )

    async def collect_competitors(
        self, db: AsyncSession, user_id: str, site_id: str, body: CollectCompetitorsRequest
    ) -> CollectResult:
        await seo_job_service.get(db, site_id, body.job_id)
        return await self._collect_competitors(
            db, user_id, site_id, body.job_id, body.limit, body.keyword_ids
        )

    async def collect_competitor_keywords(
        self, db: AsyncSession, user_id: str, site_id: str, body: CollectCompetitorKeywordsRequest
    ) -> CollectResult:
        await seo_job_service.get(db, site_id, body.job_id)
        return await self._collect_competitor_keywords(
            db, user_id, site_id, body.job_id, body.competitor_ids, body.limit
        )

    async def collect_serps(
        self, db: AsyncSession, user_id: str, site_id: str, body: CollectSerpsRequest
    ) -> CollectResult:
        await seo_job_service.get(db, site_id, body.job_id)
        return await self._collect_serps(
            db,
            user_id,
            site_id,
            body.job_id,
            body.keyword_ids,
            body.terms,
            body.suggestion_ids,
            body.source_table,
            body.device,
            body.max_keywords,
        )


seo_collect_service = SeoCollectService()
