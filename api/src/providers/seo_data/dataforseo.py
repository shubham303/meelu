from typing import Any

from src.providers.errors import ProviderRequestError
from src.providers.http import vendor_request
from src.providers.registry import VendorResponse
from src.providers.seo_data.adapter import SEO_CAPABILITIES, SeoDataAdapter
from src.settings import settings

ENDPOINTS = {
    "ranked_keywords": "/v3/dataforseo_labs/google/ranked_keywords/live",
    "competitors": "/v3/dataforseo_labs/google/competitors_domain/live",
    "serp": "/v3/serp/google/organic/live/advanced",
    "autocomplete": "/v3/serp/google/autocomplete/live/advanced",
    "trends": "/v3/keywords_data/google_trends/explore/live",
    "ideas": "/v3/dataforseo_labs/google/keyword_ideas/live",
    "suggestions": "/v3/dataforseo_labs/google/keyword_suggestions/live",
    "related": "/v3/dataforseo_labs/google/related_keywords/live",
    "bulk_pages_summary": "/v3/backlinks/bulk_pages_summary/live",
    "keyword_overview": "/v3/dataforseo_labs/google/keyword_overview/live",
    "historical_serps": "/v3/dataforseo_labs/google/historical_serps/live",
    "backlinks": "/v3/backlinks/backlinks/live",
    "bulk_ranks": "/v3/backlinks/bulk_ranks/live",
    "bulk_spam_score": "/v3/backlinks/bulk_spam_score/live",
    "serp_competitors": "/v3/dataforseo_labs/google/serp_competitors/live",
    "relevant_pages": "/v3/dataforseo_labs/google/relevant_pages/live",
    "lighthouse": "/v3/on_page/lighthouse/live/json",
    "llm_mentions": "/v3/ai_optimization/llm_mentions/search/live",
    "chat_gpt_answer": "/v3/ai_optimization/chat_gpt/llm_responses/live",
    "claude_answer": "/v3/ai_optimization/claude/llm_responses/live",
}

LIMITS = {
    "keywords_per_request": 1000,
    "overview_keywords_per_request": 700,
    "trends_per_request": 5,
    "seeds_per_request": 200,
    "discovered_per_request": 1000,
    "summary_targets": 1000,
    "serp_competitor_keywords": 100,
    "backlinks_per_request": 1000,
    "bulk_targets": 1000,
}

AI_PROMPT_CHARS = 500
FORCED_WEB_SEARCH = frozenset({"claude"})
OK = 20000


def clamp(limit: int | None, cap: int) -> int:
    return min(max(int(limit or 1), 1), cap)


def micros(cost: Any) -> int:
    return round(cost * 1_000_000) if isinstance(cost, (int, float)) else 0


def envelope_cost(envelope: dict) -> int:
    if isinstance(envelope.get("cost"), (int, float)):
        return micros(envelope["cost"])
    return sum(micros((t or {}).get("cost")) for t in envelope.get("tasks") or [])


def query(endpoint: str, task: dict[str, Any]) -> dict[str, Any]:
    return {"endpoint": ENDPOINTS[endpoint], "task": task}


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
        return bool(settings.dataforseo_auth)

    def headers(self) -> dict[str, str]:
        return {"authorization": f"Basic {settings.dataforseo_auth.strip()}"}

    async def send(self, query: dict) -> VendorResponse:
        envelope, cost = await self.post(query["endpoint"], query["task"])
        return VendorResponse(envelope, cost)

    async def post(self, path: str, task: dict[str, Any]) -> tuple[dict, int]:
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

    def keyword_overview(self, keywords, locale):
        return query(
            "keyword_overview",
            {
                "keywords": keywords[: LIMITS["overview_keywords_per_request"]],
                "include_clickstream_data": True,
                **locale,
            },
        )

    def keyword_ideas(self, seeds, locale, limit):
        return query(
            "ideas",
            {
                "keywords": seeds[: LIMITS["seeds_per_request"]],
                "limit": clamp(limit, LIMITS["discovered_per_request"]),
                **locale,
            },
        )

    def keyword_suggestions(self, seed, locale, limit):
        return query(
            "suggestions",
            {"keyword": seed, "limit": clamp(limit, LIMITS["discovered_per_request"]), **locale},
        )

    def related_keywords(self, seed, locale, limit):
        return query(
            "related",
            {"keyword": seed, "limit": clamp(limit, LIMITS["discovered_per_request"]), **locale},
        )

    def bulk_pages_summary(self, targets):
        return query("bulk_pages_summary", {"targets": targets[: LIMITS["summary_targets"]]})

    def trends_explore(self, keywords, locale):
        return query(
            "trends",
            {"keywords": keywords[: LIMITS["trends_per_request"]], "type": "web", **locale},
        )

    def ranked_keywords(self, target, locale, limit, filters):
        return query(
            "ranked_keywords",
            {
                "target": target,
                "limit": clamp(limit, 1000),
                **({"filters": filters} if filters else {}),
                **locale,
            },
        )

    def competitors_domain(self, target, locale, limit):
        return query("competitors", {"target": target, "limit": clamp(limit, 1000), **locale})

    def backlinks_list(self, target, limit):
        return query(
            "backlinks",
            {
                "target": target,
                "mode": "one_per_domain",
                "limit": clamp(limit, LIMITS["backlinks_per_request"]),
                "order_by": ["domain_from_rank,desc"],
                "backlinks_status_type": "live",
                "include_subdomains": True,
                "exclude_internal_backlinks": True,
                "rank_scale": "one_thousand",
            },
        )

    def bulk_ranks(self, targets):
        return query(
            "bulk_ranks",
            {"targets": targets[: LIMITS["bulk_targets"]], "rank_scale": "one_thousand"},
        )

    def bulk_spam_scores(self, targets):
        return query("bulk_spam_score", {"targets": targets[: LIMITS["bulk_targets"]]})

    def historical_serps(self, keyword, locale, date_from):
        return query("historical_serps", {"keyword": keyword, "date_from": date_from, **locale})

    def relevant_pages(self, target, locale, limit):
        return query(
            "relevant_pages",
            {
                "target": target,
                "limit": clamp(limit, 1000),
                "order_by": ["metrics.organic.etv,desc"],
                **locale,
            },
        )

    def serp_competitors(self, keywords, locale, limit):
        return query(
            "serp_competitors",
            {
                "keywords": keywords[: LIMITS["serp_competitor_keywords"]],
                "limit": clamp(limit, 100),
                **locale,
            },
        )

    def serp_organic(self, keyword, locale, device, depth):
        return query("serp", {"keyword": keyword, "device": device, "depth": depth, **locale})

    def serp_autocomplete(self, keyword, locale):
        return query("autocomplete", {"keyword": keyword, **locale})

    def lighthouse(self, url, for_mobile):
        return query(
            "lighthouse",
            {
                "url": url,
                "for_mobile": for_mobile,
                "categories": ["performance", "accessibility", "best_practices", "seo"],
            },
        )

    def llm_mentions(self, targets, platform, locale, limit):
        return query(
            "llm_mentions",
            {
                "target": [llm_target(t) for t in targets],
                "platform": platform,
                "limit": clamp(limit, 1000),
                **locale,
            },
        )

    def ai_answer(self, platform, prompt, country, model):
        return query(
            f"{platform}_answer",
            {
                "user_prompt": prompt[:AI_PROMPT_CHARS],
                "model_name": model,
                "web_search": True,
                **({"force_web_search": True} if platform in FORCED_WEB_SEARCH else {}),
                **({"web_search_country_iso_code": country.upper()} if country else {}),
            },
        )

    async def ai_models(self, platform):
        url = (
            settings.dataforseo_base_url.rstrip("/")
            + f"/v3/ai_optimization/{platform}/llm_responses/models"
        )
        body = await vendor_request(self.id, url, headers=self.headers(), timeout_s=30)
        found = [
            m
            for t in (body or {}).get("tasks") or []
            for m in (t or {}).get("result") or []
            if isinstance(m, dict)
        ]
        return [
            str(m["model_name"])
            for m in found
            if m.get("model_name") and m.get("web_search_supported")
        ]

    def serp_ai_overview(self, keyword, locale):
        return query(
            "serp",
            {"keyword": keyword, "depth": 10, "load_async_ai_overview": True, **locale},
        )
