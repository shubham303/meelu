from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.providers.errors import ConflictError
from src.providers.registry import Caller, ProviderFacade
from src.providers.seo_data.dataforseo import DataForSeoAdapter
from src.providers.seo_data.shape import (
    brand_filters,
    chunk,
    cited_urls,
    fact_from_overview,
    idea_of,
    locale_of,
    normalize_keywords,
    own_domain,
    pick,
    prompt_of,
    ranked_row,
    round_value,
    serp_questions,
    serp_related,
    trend_points,
)

MAX_BRAND_EXCLUSIONS = 8
FEATURE_TYPES = ("ai_overview", "featured_snippet", "people_also_ask", "local_pack")
KEYWORDS_PER_REQUEST = 1000
SEEDS_PER_REQUEST = 200
TRENDS_PER_REQUEST = 5
SERP_COMPETITOR_KEYWORDS = 100

TTL = {
    "keywords.overview": timedelta(days=30),
    "keywords.ideas": timedelta(days=30),
    "keywords.trends": timedelta(days=7),
    "domains.ranked_keywords": timedelta(days=7),
    "domains.competitors": timedelta(days=7),
    "domains.overview": timedelta(days=7),
    "domains.relevant_pages": timedelta(days=7),
    "serp.organic": timedelta(days=1),
    "serp.competitors": timedelta(days=7),
    "pages.lighthouse": timedelta(days=1),
    "llm.mentions": timedelta(days=7),
}


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class SeoDataProvider(ProviderFacade):
    domain = "seo-data"
    label = "search data"

    async def _fetch(self, db, caller, capability, request, call) -> Any:
        return await self.fetch(db, caller, capability, request, call, TTL[capability])

    async def keyword_facts(
        self,
        db: AsyncSession,
        caller: Caller,
        keywords: list[str],
        location_code: int | None = None,
        language_code: str | None = None,
    ) -> dict:
        locale = locale_of(location_code, language_code)
        wanted = normalize_keywords(keywords)
        if not wanted:
            return {"facts": []}
        at = now_iso()
        facts = []
        for part in chunk(wanted, KEYWORDS_PER_REQUEST):
            items = await self._fetch(
                db,
                caller,
                "keywords.overview",
                {"keywords": part, **locale},
                lambda a, part=part: a.keyword_overview(part, locale),
            )
            facts.extend(fact_from_overview(i, at) for i in items if i and i.get("keyword"))
        return {"facts": facts}

    async def keyword_ideas(
        self,
        db: AsyncSession,
        caller: Caller,
        seeds: list[str],
        limit: int = 200,
        location_code: int | None = None,
        language_code: str | None = None,
    ) -> dict:
        locale = locale_of(location_code, language_code)
        wanted = normalize_keywords(seeds)
        if not wanted:
            return {"ideas": []}
        found: dict[str, dict] = {}
        for part in chunk(wanted, SEEDS_PER_REQUEST):
            if len(found) >= limit:
                break
            items = await self._fetch(
                db,
                caller,
                "keywords.ideas",
                {"seeds": part, "limit": limit, **locale},
                lambda a, part=part: a.keyword_ideas(part, locale, limit),
            )
            for item in items:
                if item and item.get("keyword"):
                    idea = idea_of(item)
                    found.setdefault(idea["keyword"], idea)
        return {"ideas": list(found.values())[:limit]}

    async def ranked_keywords(
        self,
        db: AsyncSession,
        caller: Caller,
        domain: str,
        limit: int = 100,
        exclude_brand_terms: list[str] | None = None,
        location_code: int | None = None,
        language_code: str | None = None,
    ) -> dict:
        locale = locale_of(location_code, language_code)
        target = own_domain(domain)
        if not target:
            return {"rankings": []}
        exclude = normalize_keywords(exclude_brand_terms)
        if len(exclude) > MAX_BRAND_EXCLUSIONS:
            raise ConflictError(
                f"At most {MAX_BRAND_EXCLUSIONS} brand terms can be excluded per pull — the vendor "
                f"caps a request at {MAX_BRAND_EXCLUSIONS} filter conditions and {len(exclude)} were given."
            )
        filters = brand_filters(exclude) if exclude else None
        items = await self._fetch(
            db,
            caller,
            "domains.ranked_keywords",
            {"target": target, "limit": limit, "exclude": exclude, **locale},
            lambda a: a.ranked_keywords(target, locale, limit, filters),
        )
        rankings = [r for r in (ranked_row(i, target) for i in items) if r]
        rankings.sort(key=lambda r: r["rankGroup"])
        return {"rankings": rankings[:limit], "fetchedAt": now_iso()}

    async def rival_domains(
        self,
        db: AsyncSession,
        caller: Caller,
        domain: str,
        limit: int = 10,
        location_code: int | None = None,
        language_code: str | None = None,
    ) -> dict:
        locale = locale_of(location_code, language_code)
        target = own_domain(domain)
        if not target:
            return {"rivals": []}
        items = await self._fetch(
            db,
            caller,
            "domains.competitors",
            {"target": target, "limit": limit, **locale},
            lambda a: a.competitors_domain(target, locale, limit),
        )
        rivals = [
            {
                "domain": i["domain"],
                "intersections": pick(i.get("intersections")),
                "avgPosition": pick(i.get("avg_position")),
            }
            for i in items
            if i and i.get("domain") and i["domain"] != target
        ]
        return {"rivals": rivals[:limit]}

    async def serp_snapshot(
        self,
        db: AsyncSession,
        caller: Caller,
        keyword: str,
        device: str = "desktop",
        depth: int = 10,
        stop_on_domain: str | None = None,
        location_code: int | None = None,
        language_code: str | None = None,
    ) -> dict:
        locale = locale_of(location_code, language_code)
        term = keyword.strip().lower()
        stop = own_domain(stop_on_domain) if stop_on_domain else None
        options = {"device": device, "depth": depth, "stop_on_domain": stop}
        block = await self._fetch(
            db,
            caller,
            "serp.organic",
            {"keyword": term, **options, **locale},
            lambda a: a.serp_organic(term, locale, options),
        )
        block = block or {}
        item_types = list(block.get("item_types") or [])
        items = block.get("items") or []
        cited = cited_urls(items)
        results = [
            {
                "rankGroup": int(item.get("rank_group") or 0),
                "rankAbsolute": int(item.get("rank_absolute") or 0),
                "type": item.get("type"),
                "domain": item.get("domain"),
                "url": item.get("url"),
                "title": item.get("title"),
                "description": item.get("description"),
                "citedByAiOverview": bool(item.get("url") and item["url"] in cited),
            }
            for item in items
            if item and item.get("rank_absolute") is not None
        ]
        features = {name: name in item_types for name in FEATURE_TYPES}
        return {
            "snapshot": {
                "keyword": term,
                "locationCode": locale["location_code"],
                "languageCode": locale["language_code"],
                "device": device,
                "capturedAt": now_iso(),
                "itemTypes": item_types,
                "aiOverview": features["ai_overview"],
                "featuredSnippet": features["featured_snippet"],
                "peopleAlsoAsk": features["people_also_ask"],
                "localPack": features["local_pack"],
                "organicCount": sum(1 for r in results if r["type"] == "organic"),
                "checkUrl": block.get("check_url"),
                "results": results,
                "questions": serp_questions(items),
                "relatedSearches": serp_related(items),
            }
        }

    async def trend(
        self,
        db: AsyncSession,
        caller: Caller,
        keywords: list[str],
        location_code: int | None = None,
        language_code: str | None = None,
    ) -> dict:
        locale = locale_of(location_code, language_code)
        wanted = normalize_keywords(keywords)
        trends: dict[str, list] = {}
        for part in chunk(wanted, TRENDS_PER_REQUEST):
            items = await self._fetch(
                db,
                caller,
                "keywords.trends",
                {"keywords": part, **locale},
                lambda a, part=part: a.trends_explore(part, locale),
            )
            graph = next((i for i in items if i and i.get("type") == "google_trends_graph"), None)
            if not graph:
                continue
            for seat, keyword in enumerate(part):
                trends[keyword] = trend_points(graph, keyword, seat)
        return {"trends": trends}

    async def domain_overview(
        self,
        db: AsyncSession,
        caller: Caller,
        domain: str,
        location_code: int | None = None,
        language_code: str | None = None,
    ) -> dict:
        locale = locale_of(location_code, language_code)
        target = own_domain(domain)
        item = await self._fetch(
            db,
            caller,
            "domains.overview",
            {"target": target, **locale},
            lambda a: a.domain_rank_overview(target, locale),
        )
        organic = ((item or {}).get("metrics") or {}).get("organic")
        if not organic:
            return {"domain": target, "overview": None}
        return {
            "domain": target,
            "overview": {
                "organicTraffic": round_value(organic.get("etv")),
                "organicKeywords": round_value(organic.get("count")),
                "fetchedAt": now_iso(),
            },
        }

    async def serp_competitors(
        self,
        db: AsyncSession,
        caller: Caller,
        keywords: list[str],
        limit: int = 10,
        location_code: int | None = None,
        language_code: str | None = None,
    ) -> dict:
        locale = locale_of(location_code, language_code)
        sampled = normalize_keywords(keywords)[:SERP_COMPETITOR_KEYWORDS]
        if not sampled:
            raise ConflictError("Pass at least one keyword to sample the results pages with.")
        items = await self._fetch(
            db,
            caller,
            "serp.competitors",
            {"keywords": sampled, "limit": limit, **locale},
            lambda a: a.serp_competitors(sampled, locale, limit),
        )
        competitors = [
            {
                "domain": own_domain((i or {}).get("domain")),
                "visibility": pick((i or {}).get("visibility")),
                "avgPosition": pick((i or {}).get("avg_position")),
                "medianPosition": pick((i or {}).get("median_position")),
                "keywordsCount": pick((i or {}).get("keywords_count")),
                "etv": pick((i or {}).get("etv")),
            }
            for i in items
        ]
        competitors = [c for c in competitors if c["domain"]]
        competitors.sort(key=lambda c: -(c["visibility"] or 0))
        return {"sampled": len(sampled), "competitors": competitors[:limit]}

    async def relevant_pages(
        self,
        db: AsyncSession,
        caller: Caller,
        domain: str,
        limit: int = 100,
        location_code: int | None = None,
        language_code: str | None = None,
    ) -> dict:
        locale = locale_of(location_code, language_code)
        target = own_domain(domain)
        items = await self._fetch(
            db,
            caller,
            "domains.relevant_pages",
            {"target": target, "limit": limit, **locale},
            lambda a: a.relevant_pages(target, locale, limit),
        )
        pages = [
            {
                "url": str(i["page_address"]),
                "organicKeywords": pick(
                    ((i.get("metrics") or {}).get("organic") or {}).get("count")
                ),
                "organicEtv": pick(((i.get("metrics") or {}).get("organic") or {}).get("etv")),
            }
            for i in items
            if i and i.get("page_address")
        ]
        pages.sort(key=lambda p: -(p["organicEtv"] or 0))
        return {"domain": target, "pages": pages}

    async def lighthouse(
        self, db: AsyncSession, caller: Caller, url: str, strategy: str = "mobile"
    ) -> dict:
        report = await self._fetch(
            db,
            caller,
            "pages.lighthouse",
            {"url": url, "strategy": strategy},
            lambda a: a.lighthouse(url, strategy == "mobile"),
        )
        return {"url": url, "strategy": strategy, "report": report}

    async def llm_mentions(
        self,
        db: AsyncSession,
        caller: Caller,
        targets: list[dict[str, Any]],
        platform: str = "google",
        limit: int = 300,
        location_code: int | None = None,
        language_code: str | None = None,
    ) -> dict:
        locale = locale_of(location_code, language_code)
        clean = [
            {k: v for k, v in t.items() if k in ("domain", "keyword") and v}
            for t in targets or []
            if t and (t.get("domain") or t.get("keyword"))
        ]
        if not clean:
            raise ConflictError("Pass at least one target: a domain or a keyword.")
        items = await self._fetch(
            db,
            caller,
            "llm.mentions",
            {"targets": clean, "platform": platform, "limit": limit, **locale},
            lambda a: a.llm_mentions(clean, platform, locale, limit),
        )
        prompts = [p for p in (prompt_of(i, platform) for i in items if i) if p["question"]]
        prompts.sort(
            key=lambda p: -(p["aiSearchVolume"] if p["aiSearchVolume"] is not None else -1)
        )
        return {"platform": platform, "prompts": prompts}


seo_data = SeoDataProvider([DataForSeoAdapter()])
