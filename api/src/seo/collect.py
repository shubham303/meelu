from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.providers.errors import ConflictError, SpendCeilingError
from src.providers.registry import Caller, SpendMeter
from src.providers.seo_data.service import seo_data
from src.providers.seo_data.shape import own_domain
from src.seo import repository as repo
from src.seo.constants import (
    FACTS_FRESH_DAYS,
    MAX_BRAND_TERMS,
    RANKED_FRESH_DAYS,
    RIVALS_FRESH_DAYS,
    SERP_FRESH_DAYS,
    SERP_KEEP,
)
from src.seo.precompute import embed
from src.seo.schemas import CollectResult, fields

TOP_QUERIES_SQL = """
select keyword from seo_keywords
where site_id = :site_id and not branded and impressions_28d > 0
order by impressions_28d desc limit :limit
"""

CLUSTER_HEADS_SQL = """
select hk.keyword from seo_keyword_clusters c
join seo_keywords hk on hk.id = c.head_keyword_id
where c.site_id = :site_id and c.owner_page_id is not null and not hk.branded
order by c.volume_sum desc limit :limit
"""

STALE_FACTS_SQL = """
select keyword from seo_keywords
where site_id = :site_id and id = any(cast(:ids as text[]))
  and (facts_fetched_at is null or facts_fetched_at < :cutoff)
order by keyword
"""

WORKSPACE_KEYWORDS_SQL = (
    'select distinct keyword from "{schema}"."{table}" where keyword is not null'
)

APPLY_FACTS_SQL = """
update seo_keywords set volume = :volume, difficulty = :difficulty, cpc = :cpc, intent = :intent,
  facts_fetched_at = :at, updated_at = :at
where site_id = :site_id and keyword = :keyword
"""

APPLY_RANKED_SQL = """
update seo_keywords set our_position = :position, our_url = :url,
  volume = coalesce(volume, :volume), difficulty = coalesce(difficulty, :difficulty),
  cpc = coalesce(cpc, :cpc), intent = coalesce(intent, :intent),
  facts_fetched_at = coalesce(facts_fetched_at, :at), updated_at = :at
where site_id = :site_id and keyword = :keyword
"""

UPSERT_COMPETITOR_KEYWORD_SQL = """
insert into seo_competitor_keywords (id, user_id, site_id, competitor_id, keyword_id, position,
  url, etv, fetched_at, created_at, updated_at)
values (:id, :user_id, :site_id, :competitor_id, :keyword_id, :position, :url, :etv, :at, :at, :at)
on conflict (competitor_id, keyword_id) do update set position = excluded.position,
  url = excluded.url, etv = excluded.etv, fetched_at = excluded.fetched_at, updated_at = excluded.updated_at
"""

FRESH_SERP_SQL = """
select keyword_id from seo_serp_snapshots
where site_id = :site_id and device = :device and fetched_at > :cutoff
  and keyword_id = any(cast(:ids as text[]))
"""

PRUNE_SERPS_SQL = """
delete from seo_serp_snapshots s where s.id in (
  select id from (
    select id, row_number() over (partition by keyword_id, device order by fetched_at desc) as rn
    from seo_serp_snapshots where site_id = :site_id and keyword_id = :keyword_id
  ) r where rn > :keep
)
"""

JOB_HEAD_KEYWORDS_SQL = """
select distinct k.id from seo_page_suggestions s
join seo_keywords k on k.site_id = s.site_id and k.keyword = s.topic_key
where s.site_id = :site_id and s.id = any(cast(:ids as text[]))
"""

DRAFT_HEAD_KEYWORDS_SQL = """
select k.id from seo_page_suggestions s
join seo_keywords k on k.site_id = s.site_id and k.keyword = s.topic_key
where s.site_id = :site_id and s.job_id = :job_id and s.state in ('draft', 'reviewed')
order by s.search_score desc nulls last
"""


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


async def _settle(
    db: AsyncSession, job_id: str, meter: SpendMeter, result: CollectResult
) -> CollectResult:
    await repo.add_spend(db, job_id, meter.calls, meter.micros)
    result.vendor_calls = meter.calls
    result.spent_micros = meter.micros
    result.cache_hits = meter.cache_hits
    return result


async def workspace_keywords(db: AsyncSession, user_id: str, table: str) -> list[str]:
    from src.agent.context import tenant_names

    _, schema = tenant_names(user_id)
    rows = await db.execute(text(WORKSPACE_KEYWORDS_SQL.format(schema=schema, table=table)))
    return fields.keywords([r[0] for r in rows])


async def default_seeds(db: AsyncSession, site_id: str, limit: int) -> list[str]:
    queries = [
        r[0] for r in await db.execute(text(TOP_QUERIES_SQL), {"site_id": site_id, "limit": limit})
    ]
    heads = [
        r[0]
        for r in await db.execute(text(CLUSTER_HEADS_SQL), {"site_id": site_id, "limit": limit})
    ]
    return fields.keywords(queries + heads)[:limit]


async def stale_keywords(db: AsyncSession, site_id: str, ids: list[str]) -> list[str]:
    cutoff = _now() - timedelta(days=FACTS_FRESH_DAYS)
    rows = await db.execute(
        text(STALE_FACTS_SQL), {"site_id": site_id, "ids": ids, "cutoff": cutoff}
    )
    return [r[0] for r in rows]


async def apply_facts(db: AsyncSession, site_id: str, facts: list[dict[str, Any]]) -> int:
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
    if params:
        await db.execute(text(APPLY_FACTS_SQL), params)
    return len(params)


async def collect_keywords(
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
    job = await repo.get_job(db, site_id, job_id)
    assert job is not None
    state = await repo.ensure_state(db, user_id, site_id)
    site = await repo.site_domain(db, site_id)
    meter = _meter(job)
    caller = _caller(user_id, site_id, meter)
    result = CollectResult()
    locale = {"location_code": state.location_code, "language_code": state.language_code}

    wanted: list[str] = []
    if keyword_ids:
        wanted += await stale_keywords(db, site_id, keyword_ids)
    if source_table:
        table_terms = await workspace_keywords(db, user_id, fields.workspace_table(source_table))
        added = await repo.insert_keywords(db, user_id, site_id, table_terms, "user")
        result.added += len(added)
        wanted += table_terms

    seed_terms = fields.keywords(seeds or [])
    if not seed_terms and not keyword_ids and not source_table and from_gsc:
        seed_terms = await default_seeds(db, site_id, max_seeds)
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
        added = await repo.insert_keywords(
            db, user_id, site_id, fields.keywords([r["keyword"] for r in rows]), "ranked"
        )
        result.added += len(added)
        at = _now()
        if rows:
            await db.execute(
                text(APPLY_RANKED_SQL),
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
        seed_id = (await repo.keyword_ids_for(db, site_id, [seed])).get(seed)
        if seed_id is None:
            seed_id = (await repo.insert_keywords(db, user_id, site_id, [seed], "user") or [None])[
                0
            ]
        ideas = await seo_data.keyword_ideas(db, caller, [seed], limit=ideas_per_seed, **locale)
        rows = ideas.get("ideas") or []
        terms = fields.keywords([r["keyword"] for r in rows])
        added = await repo.insert_keywords(
            db, user_id, site_id, terms, "ideas", seed_keyword_id=seed_id
        )
        result.added += len(added)
        result.refreshed += await apply_facts(db, site_id, rows)
        wanted.append(seed)

    ids = list((await repo.keyword_ids_for(db, site_id, fields.keywords(wanted))).values())
    stale = await stale_keywords(db, site_id, ids) if ids else []
    if stale:
        facts = await seo_data.keyword_facts(db, caller, sorted(stale), **locale)
        result.refreshed += await apply_facts(db, site_id, facts.get("facts") or [])

    await db.flush()
    result.embedded = await embed.embed_pending(db, user_id, site_id)
    return await _settle(db, job_id, meter, result)


async def collect_competitors(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    job_id: str,
    limit: int,
    keyword_ids: list[str] | None,
) -> CollectResult:
    job = await repo.get_job(db, site_id, job_id)
    assert job is not None
    state = await repo.ensure_state(db, user_id, site_id)
    site = await repo.site_domain(db, site_id)
    meter = _meter(job)
    caller = _caller(user_id, site_id, meter)
    result = CollectResult()
    locale = {"location_code": state.location_code, "language_code": state.language_code}
    fresh = [
        c
        for c in await repo.list_competitors(db, site_id, None)
        if c.fetched_at and c.fetched_at > _now() - timedelta(days=RIVALS_FRESH_DAYS)
    ]
    if fresh and not keyword_ids:
        result.competitors = [c.domain for c in fresh][:limit]
        return await _settle(db, job_id, meter, result)

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
        terms = [
            k.keyword for k in [await repo.get_keyword(db, site_id, i) for i in keyword_ids] if k
        ]
    else:
        terms = await default_seeds(db, site_id, 20)
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
        await repo.upsert_competitor(
            db,
            user_id,
            site_id,
            {"domain": domain, "brand_terms": brand, "fetched_at": at, **values},
        )
        result.added += 1
        result.competitors.append(domain)
    return await _settle(db, job_id, meter, result)


async def collect_competitor_keywords(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    job_id: str,
    competitor_ids: list[str] | None,
    limit: int,
) -> CollectResult:
    job = await repo.get_job(db, site_id, job_id)
    assert job is not None
    state = await repo.ensure_state(db, user_id, site_id)
    meter = _meter(job)
    caller = _caller(user_id, site_id, meter)
    result = CollectResult()
    locale = {"location_code": state.location_code, "language_code": state.language_code}
    cutoff = _now() - timedelta(days=RANKED_FRESH_DAYS)
    competitors = [
        c
        for c in await repo.list_competitors(db, site_id, "confirmed")
        if (not competitor_ids or c.id in competitor_ids)
    ]
    from src.core.ids import uid

    for competitor in competitors:
        latest = await repo.competitor_keywords_fetched_at(db, competitor.id)
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
        added = await repo.insert_keywords(db, user_id, site_id, terms, "competitor")
        result.added += len(added)
        result.refreshed += await apply_facts(
            db,
            site_id,
            [r for r in rows if r.get("volume") is not None or r.get("difficulty") is not None],
        )
        ids = await repo.keyword_ids_for(db, site_id, terms)
        at = _now()
        params = [
            {
                "id": uid("ckw"),
                "user_id": user_id,
                "site_id": site_id,
                "competitor_id": competitor.id,
                "keyword_id": ids[fields.keyword(r["keyword"])],
                "position": r.get("rankGroup"),
                "url": r.get("url"),
                "etv": r.get("etv"),
                "at": at,
            }
            for r in rows
            if fields.keyword(r["keyword"]) in ids
        ]
        if params:
            await db.execute(text(UPSERT_COMPETITOR_KEYWORD_SQL), params)
        await repo.patch_competitor(db, site_id, competitor.id, {"fetched_at": at})
    await db.flush()
    result.embedded = await embed.embed_pending(db, user_id, site_id)
    return await _settle(db, job_id, meter, result)


async def resolve_serp_targets(
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
        await repo.insert_keywords(db, user_id, site_id, cleaned, "user")
        ids += list((await repo.keyword_ids_for(db, site_id, cleaned)).values())
    if source_table:
        cleaned = await workspace_keywords(db, user_id, fields.workspace_table(source_table))
        await repo.insert_keywords(db, user_id, site_id, cleaned, "user")
        ids += list((await repo.keyword_ids_for(db, site_id, cleaned)).values())
    if suggestion_ids:
        ids += [
            r[0]
            for r in await db.execute(
                text(JOB_HEAD_KEYWORDS_SQL), {"site_id": site_id, "ids": suggestion_ids}
            )
        ]
    if not ids and not (keyword_ids or terms or source_table or suggestion_ids):
        ids = [
            r[0]
            for r in await db.execute(
                text(DRAFT_HEAD_KEYWORDS_SQL), {"site_id": site_id, "job_id": job_id}
            )
        ]
    return list(dict.fromkeys(ids))


async def collect_serps(
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
    job = await repo.get_job(db, site_id, job_id)
    assert job is not None
    state = await repo.ensure_state(db, user_id, site_id)
    site = own_domain(await repo.site_domain(db, site_id) or "")
    meter = _meter(job)
    caller = _caller(user_id, site_id, meter)
    result = CollectResult()
    locale = {"location_code": state.location_code, "language_code": state.language_code}
    targets = await resolve_serp_targets(
        db, user_id, site_id, job_id, keyword_ids, terms, suggestion_ids, source_table
    )
    if len(targets) > max_keywords:
        raise ConflictError(
            f"{len(targets)} keywords asked but max is {max_keywords}; narrow the set or raise max."
        )
    cutoff = _now() - timedelta(days=SERP_FRESH_DAYS)
    fresh = {
        r[0]
        for r in await db.execute(
            text(FRESH_SERP_SQL),
            {"site_id": site_id, "device": device, "cutoff": cutoff, "ids": targets},
        )
    }
    from src.core.ids import uid

    for keyword_id in targets:
        if keyword_id in fresh:
            result.skipped += 1
            continue
        keyword = await repo.get_keyword(db, site_id, keyword_id)
        if keyword is None:
            continue
        snapshot = (
            await seo_data.serp_snapshot(
                db, caller, keyword.keyword, device=device, depth=10, **locale
            )
        ).get("snapshot") or {}
        at = _now()
        snapshot_id = await repo.insert_serp_snapshot(
            db,
            user_id,
            site_id,
            keyword_id,
            device,
            at,
            [t for t in snapshot.get("itemTypes") or []],
            [
                {
                    "id": uid("srp"),
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
            added = await repo.insert_keywords(
                db, user_id, site_id, fields.keywords(values), source, seed_keyword_id=keyword_id
            )
            result.added += len(added)
        await db.execute(
            text(PRUNE_SERPS_SQL), {"site_id": site_id, "keyword_id": keyword_id, "keep": SERP_KEEP}
        )
        result.refreshed += 1 if snapshot_id else 0
    await db.flush()
    result.embedded = await embed.embed_pending(db, user_id, site_id)
    return await _settle(db, job_id, meter, result)
