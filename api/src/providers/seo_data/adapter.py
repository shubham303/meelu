from typing import Any

from src.providers.registry import ProviderAdapter, VendorResponse

SEO_CAPABILITIES = frozenset(
    {
        "keywords.overview",
        "keywords.ideas",
        "keywords.trends",
        "domains.ranked_keywords",
        "domains.competitors",
        "domains.overview",
        "domains.relevant_pages",
        "serp.organic",
        "serp.competitors",
        "pages.lighthouse",
        "llm.mentions",
    }
)

DEFAULT_LOCALE = {"location_code": 2840, "language_code": "en"}


class SeoDataAdapter(ProviderAdapter):
    async def keyword_overview(self, keywords: list[str], locale: dict) -> VendorResponse:
        raise self.unsupported("keywords.overview")

    async def keyword_ideas(self, seeds: list[str], locale: dict, limit: int) -> VendorResponse:
        raise self.unsupported("keywords.ideas")

    async def trends_explore(self, keywords: list[str], locale: dict) -> VendorResponse:
        raise self.unsupported("keywords.trends")

    async def ranked_keywords(
        self, target: str, locale: dict, limit: int, filters: list | None
    ) -> VendorResponse:
        raise self.unsupported("domains.ranked_keywords")

    async def competitors_domain(self, target: str, locale: dict, limit: int) -> VendorResponse:
        raise self.unsupported("domains.competitors")

    async def domain_rank_overview(self, target: str, locale: dict) -> VendorResponse:
        raise self.unsupported("domains.overview")

    async def relevant_pages(self, target: str, locale: dict, limit: int) -> VendorResponse:
        raise self.unsupported("domains.relevant_pages")

    async def serp_organic(self, keyword: str, locale: dict, options: dict) -> VendorResponse:
        raise self.unsupported("serp.organic")

    async def serp_competitors(
        self, keywords: list[str], locale: dict, limit: int
    ) -> VendorResponse:
        raise self.unsupported("serp.competitors")

    async def lighthouse(self, url: str, for_mobile: bool) -> VendorResponse:
        raise self.unsupported("pages.lighthouse")

    async def llm_mentions(
        self, targets: list[dict[str, Any]], platform: str, locale: dict, limit: int
    ) -> VendorResponse:
        raise self.unsupported("llm.mentions")
