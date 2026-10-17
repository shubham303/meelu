from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from src.providers.errors import ConflictError
from src.providers.registry import Caller, ProviderFacade
from src.providers.seo_data.adapter import SeoDataAdapter
from src.providers.seo_data.dataforseo import DataForSeoAdapter
from src.providers.seo_data.shape import (
    brand_filters,
    bundle_items,
    chunk,
    first_result,
    locale_of,
    normalize_keywords,
    own_domain,
    pick,
    prompt_of,
    ranked_row,
    trend_points,
)

MAX_BRAND_EXCLUSIONS = 8
OVERVIEW_KEYWORDS_PER_REQUEST = 700
TRENDS_PER_REQUEST = 5
MAX_TREND_KEYWORDS = 50
MAX_LLM_TARGETS = 10
SERP_COMPETITOR_KEYWORDS = 100
BULK_TARGETS = 1000

TTL = timedelta(days=7)
PAGE_RANK_TTL = timedelta(days=30)


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


class SeoDataProvider(ProviderFacade):
    domain = "seo-data"
    label = "search data"

    async def _fetch(
        self,
        caller: Caller,
        capability: str,
        build: Callable[[SeoDataAdapter], dict],
        ttl: timedelta | None = TTL,
        refresh: bool = False,
    ) -> dict:
        return await self.fetch(caller, capability, build, lambda a: a.send(build(a)), ttl, refresh)

    async def _keyword_items(
        self,
        caller: Caller,
        capability: str,
        keywords: list[str],
        per_request: int,
        build: Callable[[SeoDataAdapter, list[str]], dict],
    ) -> list[dict]:
        items: list[dict] = []
        for part in chunk(keywords, per_request):
            envelope = await self._fetch(
                caller, capability, lambda a, part=part: build(a, part), ttl=None
            )
            items.extend(i for i in bundle_items(envelope) if i and i.get("keyword"))
        return items

    async def keyword_overview(
        self, caller: Caller, keywords: list[str], locale: dict
    ) -> list[dict]:
        return await self._keyword_items(
            caller,
            "keywords.overview",
            keywords,
            OVERVIEW_KEYWORDS_PER_REQUEST,
            lambda a, part: a.keyword_overview(part, locale),
        )

    async def discover_keywords(
        self, caller: Caller, seeds: list[str], limit: int, locale: dict
    ) -> list[str]:
        found: dict[str, None] = {}
        ideas = await self._fetch(
            caller, "keywords.ideas", lambda a: a.keyword_ideas(seeds, locale, limit)
        )
        found.update(
            dict.fromkeys(i["keyword"] for i in bundle_items(ideas) if i and i.get("keyword"))
        )
        for seed in seeds:
            suggested = await self._fetch(
                caller,
                "keywords.suggestions",
                lambda a, seed=seed: a.keyword_suggestions(seed, locale, limit),
            )
            found.update(
                dict.fromkeys(
                    i["keyword"] for i in bundle_items(suggested) if i and i.get("keyword")
                )
            )
            related = await self._fetch(
                caller,
                "keywords.related",
                lambda a, seed=seed: a.related_keywords(seed, locale, limit),
            )
            found.update(
                dict.fromkeys(
                    d["keyword"]
                    for i in bundle_items(related)
                    if (d := (i or {}).get("keyword_data")) and d.get("keyword")
                )
            )
        return list(found)

    async def pages_summary(self, caller: Caller, targets: list[str]) -> dict[str, dict]:
        found: dict[str, dict] = {}
        for part in chunk(sorted(set(targets)), BULK_TARGETS):
            envelope = await self._fetch(
                caller,
                "backlinks.pages_summary",
                lambda a, part=part: a.bulk_pages_summary(part),
                ttl=PAGE_RANK_TTL,
            )
            found.update({str(i["url"]): i for i in bundle_items(envelope) if i and i.get("url")})
        return found

    async def ranked_keywords(
        self,
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
        items = bundle_items(
            await self._fetch(
                caller,
                "domains.ranked_keywords",
                lambda a: a.ranked_keywords(target, locale, limit, filters),
            )
        )
        rankings = [r for r in (ranked_row(i, target) for i in items) if r]
        rankings.sort(key=lambda r: r["rankGroup"])
        return {"rankings": rankings[:limit], "fetchedAt": now_iso()}

    async def rival_domains(
        self,
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
        items = bundle_items(
            await self._fetch(
                caller,
                "domains.competitors",
                lambda a: a.competitors_domain(target, locale, limit),
            )
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

    async def serp_organic(
        self,
        caller: Caller,
        keyword: str,
        device: str,
        depth: int,
        locale: dict,
        ttl: timedelta | None = None,
        refresh: bool = False,
    ) -> dict | None:
        envelope = await self._fetch(
            caller,
            "serp.organic",
            lambda a: a.serp_organic(keyword, locale, device, depth),
            ttl=ttl,
            refresh=refresh,
        )
        return first_result(envelope)

    async def serp_autocomplete(
        self,
        caller: Caller,
        keyword: str,
        locale: dict,
        ttl: timedelta | None = None,
        refresh: bool = False,
    ) -> dict | None:
        envelope = await self._fetch(
            caller,
            "serp.autocomplete",
            lambda a: a.serp_autocomplete(keyword, locale),
            ttl=ttl,
            refresh=refresh,
        )
        return first_result(envelope)

    async def backlinks(self, caller: Caller, target: str, limit: int) -> list[dict]:
        found = first_result(
            await self._fetch(caller, "backlinks.list", lambda a: a.backlinks_list(target, limit))
        )
        return [i for i in (found or {}).get("items") or [] if isinstance(i, dict)]

    async def domain_ranks(self, caller: Caller, domains: list[str]) -> dict[str, int]:
        return await self._per_domain(
            caller, "backlinks.domain_ranks", domains, lambda a, part: a.bulk_ranks(part), "rank"
        )

    async def domain_spam_scores(self, caller: Caller, domains: list[str]) -> dict[str, int]:
        return await self._per_domain(
            caller,
            "backlinks.spam_scores",
            domains,
            lambda a, part: a.bulk_spam_scores(part),
            "spam_score",
        )

    async def _per_domain(
        self,
        caller: Caller,
        capability: str,
        domains: list[str],
        build: Callable[[SeoDataAdapter, list[str]], dict],
        field: str,
    ) -> dict[str, int]:
        found: dict[str, int] = {}
        for part in chunk(sorted({own_domain(d) for d in domains if own_domain(d)}), BULK_TARGETS):
            envelope = await self._fetch(
                caller, capability, lambda a, part=part: build(a, part), ttl=PAGE_RANK_TTL
            )
            for item in bundle_items(envelope):
                value = pick((item or {}).get(field))
                if value is not None and item.get("target"):
                    found[own_domain(item["target"])] = round(value)
        return found

    async def historical_serps(
        self,
        caller: Caller,
        keyword: str,
        locale: dict,
        date_from: str,
        ttl: timedelta | None = None,
    ) -> list[dict]:
        envelope = await self._fetch(
            caller,
            "serp.history",
            lambda a: a.historical_serps(keyword, locale, date_from),
            ttl=ttl,
        )
        snapshots = [s for s in bundle_items(envelope) if s and s.get("datetime")]
        return sorted(snapshots, key=lambda s: s["datetime"])

    async def trend(
        self,
        caller: Caller,
        keywords: list[str],
        location_code: int | None = None,
        language_code: str | None = None,
    ) -> dict:
        locale = locale_of(location_code, language_code)
        wanted = normalize_keywords(keywords)
        if len(wanted) > MAX_TREND_KEYWORDS:
            raise ConflictError(
                f"At most {MAX_TREND_KEYWORDS} keywords per trend pull and {len(wanted)} were "
                f"given. Pick the keywords that matter and split the rest into later pulls."
            )
        trends: dict[str, list] = {}
        for part in chunk(wanted, TRENDS_PER_REQUEST):
            items = bundle_items(
                await self._fetch(
                    caller,
                    "keywords.trends",
                    lambda a, part=part: a.trends_explore(part, locale),
                )
            )
            graph = next((i for i in items if i and i.get("type") == "google_trends_graph"), None)
            if not graph:
                continue
            for seat, keyword in enumerate(part):
                trends[keyword] = trend_points(graph, keyword, seat)
        return {"trends": trends}

    async def serp_competitors(
        self,
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
        items = bundle_items(
            await self._fetch(
                caller,
                "serp.competitors",
                lambda a: a.serp_competitors(sampled, locale, limit),
            )
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
        caller: Caller,
        domain: str,
        limit: int = 100,
        location_code: int | None = None,
        language_code: str | None = None,
    ) -> dict:
        locale = locale_of(location_code, language_code)
        target = own_domain(domain)
        items = bundle_items(
            await self._fetch(
                caller,
                "domains.relevant_pages",
                lambda a: a.relevant_pages(target, locale, limit),
            )
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

    async def lighthouse(self, caller: Caller, url: str, strategy: str = "mobile") -> dict:
        report = first_result(
            await self._fetch(
                caller,
                "pages.lighthouse",
                lambda a: a.lighthouse(url, strategy == "mobile"),
            )
        )
        return {"url": url, "strategy": strategy, "report": report}

    async def llm_mentions(
        self,
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
        if len(clean) > MAX_LLM_TARGETS:
            raise ConflictError(
                f"At most {MAX_LLM_TARGETS} targets per mentions pull and {len(clean)} were given."
            )
        items = bundle_items(
            await self._fetch(
                caller,
                "llm.mentions",
                lambda a: a.llm_mentions(clean, platform, locale, limit),
            )
        )
        prompts = [p for p in (prompt_of(i, platform) for i in items if i) if p["question"]]
        prompts.sort(
            key=lambda p: -(p["aiSearchVolume"] if p["aiSearchVolume"] is not None else -1)
        )
        return {"platform": platform, "prompts": prompts}


seo_data = SeoDataProvider([DataForSeoAdapter()])
