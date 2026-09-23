import base64
from typing import Any

from src.providers.errors import ProviderRequestError
from src.providers.http import vendor_request
from src.providers.registry import VendorResponse
from src.providers.seo_data.adapter import SEO_CAPABILITIES, SeoDataAdapter
from src.settings import settings

ENDPOINTS = {
    "ideas": "/v3/dataforseo_labs/google/keyword_ideas/live",
    "ranked_keywords": "/v3/dataforseo_labs/google/ranked_keywords/live",
    "competitors": "/v3/dataforseo_labs/google/competitors_domain/live",
    "serp": "/v3/serp/google/organic/live/advanced",
    "trends": "/v3/keywords_data/google_trends/explore/live",
    "keyword_overview": "/v3/dataforseo_labs/google/keyword_overview/live",
    "domain_overview": "/v3/dataforseo_labs/google/domain_rank_overview/live",
    "serp_competitors": "/v3/dataforseo_labs/google/serp_competitors/live",
    "relevant_pages": "/v3/dataforseo_labs/google/relevant_pages/live",
    "lighthouse": "/v3/on_page/lighthouse/live/json",
    "llm_mentions": "/v3/ai_optimization/llm_mentions/search/live",
}

LIMITS = {
    "keywords_per_request": 1000,
    "seeds_per_request": 200,
    "trends_per_request": 5,
    "ideas_per_request": 1000,
    "serp_competitor_keywords": 100,
}

OK = 20000


def clamp(limit: int | None, cap: int) -> int:
    return min(max(int(limit or 1), 1), cap)


def micros(cost: Any) -> int:
    return round(cost * 1_000_000) if isinstance(cost, (int, float)) else 0


def envelope_cost(envelope: dict) -> int:
    if isinstance(envelope.get("cost"), (int, float)):
        return micros(envelope["cost"])
    return sum(micros((t or {}).get("cost")) for t in envelope.get("tasks") or [])


def results(envelope: dict) -> list:
    return [r for t in envelope.get("tasks") or [] for r in ((t or {}).get("result") or [])]


def bundle_items(envelope: dict) -> list:
    return [i for r in results(envelope) if isinstance(r, dict) for i in (r.get("items") or [])]


def llm_target(target: dict[str, Any]) -> dict[str, Any]:
    if target.get("domain"):
        return {
            "domain": target["domain"],
            "include_subdomains": True,
            "search_filter": "include",
            "search_scope": ["any"],
        }
    return {
        "keyword": target["keyword"],
        "search_filter": "include",
        "search_scope": ["any"],
        "match_type": "word_match",
    }


class DataForSeoAdapter(SeoDataAdapter):
    id = "dataforseo"
    name = "DataForSEO"
    capabilities = SEO_CAPABILITIES

    def configured(self) -> bool:
        return bool(settings.dataforseo_login and settings.dataforseo_password)

    def headers(self) -> dict[str, str]:
        raw = f"{settings.dataforseo_login.strip()}:{settings.dataforseo_password.strip()}"
        return {"authorization": f"Basic {base64.b64encode(raw.encode()).decode()}"}

    async def post(self, endpoint: str, task: dict[str, Any]) -> tuple[dict, int]:
        path = ENDPOINTS[endpoint]
        url = settings.dataforseo_base_url.rstrip("/") + path
        try:
            body = await vendor_request(
                self.id, url, method="POST", headers=self.headers(), json_body=[task], timeout_s=120
            )
        except ProviderRequestError as exc:
            raise self.describe(path, exc) from exc
        if not isinstance(body, dict):
            raise ProviderRequestError(
                self.id, 502, f"DataForSEO returned non-JSON from {path}", body
            )
        if body.get("status_code") not in (None, OK):
            raise ProviderRequestError(
                self.id,
                502,
                f"DataForSEO refused {path} ({body.get('status_code')}): "
                f"{body.get('status_message') or 'no message'}",
                body,
            )
        failed = next(
            (t for t in body.get("tasks") or [] if (t or {}).get("status_code") != OK), None
        )
        if failed:
            raise ProviderRequestError(
                self.id,
                502,
                f"DataForSEO task failed on {path} ({failed.get('status_code')}): "
                f"{failed.get('status_message') or 'no message'}",
                body,
            )
        return body, envelope_cost(body)

    def describe(self, path: str, err: ProviderRequestError) -> ProviderRequestError:
        if err.status == 401:
            return ProviderRequestError(
                self.id, 502, "DataForSEO rejected the server credentials (401).", err.body
            )
        if err.status == 402:
            return ProviderRequestError(
                self.id,
                502,
                "DataForSEO returned 402 — the account balance does not cover this call.",
                err.body,
            )
        if err.status == 403:
            return ProviderRequestError(
                self.id,
                502,
                "DataForSEO returned 403 — the account may not call this endpoint.",
                err.body,
            )
        if isinstance(err.body, dict) and err.body.get("status_code") not in (None, OK):
            return ProviderRequestError(
                self.id,
                502,
                f"DataForSEO refused {path} ({err.body.get('status_code')}): "
                f"{err.body.get('status_message') or 'no message'}",
                err.body,
            )
        if err.status is None:
            return err
        return ProviderRequestError(
            self.id,
            502,
            f"DataForSEO {err.status} on {path}: {str(err.body or '')[:200]}",
            err.body,
        )

    async def items(self, endpoint: str, task: dict, *, bundles: bool = True) -> VendorResponse:
        envelope, cost = await self.post(endpoint, task)
        return VendorResponse(bundle_items(envelope) if bundles else results(envelope), cost)

    async def first(self, endpoint: str, task: dict, *, bundles: bool = False) -> VendorResponse:
        envelope, cost = await self.post(endpoint, task)
        rows = bundle_items(envelope) if bundles else results(envelope)
        return VendorResponse(rows[0] if rows else None, cost)

    async def keyword_overview(self, keywords, locale):
        return await self.items(
            "keyword_overview", {"keywords": keywords[: LIMITS["keywords_per_request"]], **locale}
        )

    async def keyword_ideas(self, seeds, locale, limit):
        return await self.items(
            "ideas",
            {
                "keywords": seeds[: LIMITS["seeds_per_request"]],
                "limit": clamp(limit, LIMITS["ideas_per_request"]),
                **locale,
            },
        )

    async def trends_explore(self, keywords, locale):
        return await self.items(
            "trends",
            {"keywords": keywords[: LIMITS["trends_per_request"]], "type": "web", **locale},
        )

    async def ranked_keywords(self, target, locale, limit, filters):
        return await self.items(
            "ranked_keywords",
            {
                "target": target,
                "limit": clamp(limit, 1000),
                **({"filters": filters} if filters else {}),
                **locale,
            },
        )

    async def competitors_domain(self, target, locale, limit):
        return await self.items(
            "competitors", {"target": target, "limit": clamp(limit, 1000), **locale}
        )

    async def domain_rank_overview(self, target, locale):
        return await self.first(
            "domain_overview", {"target": target, "limit": 1, **locale}, bundles=True
        )

    async def relevant_pages(self, target, locale, limit):
        return await self.items(
            "relevant_pages",
            {
                "target": target,
                "limit": clamp(limit, 1000),
                "order_by": ["metrics.organic.etv,desc"],
                **locale,
            },
        )

    async def serp_competitors(self, keywords, locale, limit):
        return await self.items(
            "serp_competitors",
            {
                "keywords": keywords[: LIMITS["serp_competitor_keywords"]],
                "limit": clamp(limit, 100),
                **locale,
            },
        )

    async def serp_organic(self, keyword, locale, options):
        stop = options.get("stop_on_domain")
        return await self.first(
            "serp",
            {
                "keyword": keyword,
                "device": options.get("device", "desktop"),
                "depth": options.get("depth", 10),
                **(
                    {
                        "stop_crawl_on_match": [
                            {"match_value": stop, "match_type": "with_subdomains"}
                        ],
                        "find_targets_in": ["organic"],
                    }
                    if stop
                    else {}
                ),
                **locale,
            },
        )

    async def lighthouse(self, url, for_mobile):
        return await self.first(
            "lighthouse",
            {
                "url": url,
                "for_mobile": for_mobile,
                "categories": ["performance", "accessibility", "best_practices", "seo"],
            },
        )

    async def llm_mentions(self, targets, platform, locale, limit):
        return await self.items(
            "llm_mentions",
            {
                "target": [llm_target(t) for t in targets],
                "platform": platform,
                "limit": clamp(limit, 1000),
                **locale,
            },
        )
