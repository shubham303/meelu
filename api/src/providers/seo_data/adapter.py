from typing import Any

from src.providers.registry import ProviderAdapter, VendorResponse

SEO_CAPABILITIES = frozenset(
    {
        "keywords.overview",
        "keywords.ideas",
        "keywords.suggestions",
        "keywords.related",
        "backlinks.pages_summary",
        "keywords.trends",
        "domains.ranked_keywords",
        "domains.competitors",
        "backlinks.list",
        "backlinks.domain_ranks",
        "backlinks.spam_scores",
        "serp.history",
        "domains.relevant_pages",
        "serp.organic",
        "serp.autocomplete",
        "serp.competitors",
        "pages.lighthouse",
        "llm.mentions",
    }
)

DEFAULT_LOCALE = {"location_code": 2840, "language_code": "en"}


class SeoDataAdapter(ProviderAdapter):
    def keyword_overview(self, keywords: list[str], locale: dict) -> dict:
        raise self.unsupported("keywords.overview")

    def keyword_ideas(self, seeds: list[str], locale: dict, limit: int) -> dict:
        raise self.unsupported("keywords.ideas")

    def keyword_suggestions(self, seed: str, locale: dict, limit: int) -> dict:
        raise self.unsupported("keywords.suggestions")

    def related_keywords(self, seed: str, locale: dict, limit: int) -> dict:
        raise self.unsupported("keywords.related")

    def bulk_pages_summary(self, targets: list[str]) -> dict:
        raise self.unsupported("backlinks.pages_summary")

    def trends_explore(self, keywords: list[str], locale: dict) -> dict:
        raise self.unsupported("keywords.trends")

    def ranked_keywords(self, target: str, locale: dict, limit: int, filters: list | None) -> dict:
        raise self.unsupported("domains.ranked_keywords")

    def competitors_domain(self, target: str, locale: dict, limit: int) -> dict:
        raise self.unsupported("domains.competitors")

    def backlinks_list(self, target: str, limit: int) -> dict:
        raise self.unsupported("backlinks.list")

    def bulk_ranks(self, targets: list[str]) -> dict:
        raise self.unsupported("backlinks.domain_ranks")

    def bulk_spam_scores(self, targets: list[str]) -> dict:
        raise self.unsupported("backlinks.spam_scores")

    def historical_serps(self, keyword: str, locale: dict, date_from: str) -> dict:
        raise self.unsupported("serp.history")

    def relevant_pages(self, target: str, locale: dict, limit: int) -> dict:
        raise self.unsupported("domains.relevant_pages")

    def serp_organic(self, keyword: str, locale: dict, device: str, depth: int) -> dict:
        raise self.unsupported("serp.organic")

    def serp_autocomplete(self, keyword: str, locale: dict) -> dict:
        raise self.unsupported("serp.autocomplete")

    def serp_competitors(self, keywords: list[str], locale: dict, limit: int) -> dict:
        raise self.unsupported("serp.competitors")

    def lighthouse(self, url: str, for_mobile: bool) -> dict:
        raise self.unsupported("pages.lighthouse")

    def llm_mentions(
        self, targets: list[dict[str, Any]], platform: str, locale: dict, limit: int
    ) -> dict:
        raise self.unsupported("llm.mentions")

    async def send(self, query: dict) -> VendorResponse:
        raise NotImplementedError
