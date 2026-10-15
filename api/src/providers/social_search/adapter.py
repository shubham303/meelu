from src.providers.registry import ProviderAdapter, VendorResponse


def search_result(posts: list[dict], failed_keywords: list[str]) -> dict:
    return {"posts": posts, "failedKeywords": failed_keywords}


class SocialSearchAdapter(ProviderAdapter):
    def vendor_query(self, platform: str, query: dict) -> dict:
        return {
            "platform": platform,
            "keywords": query.get("keywords"),
            "since": str(query.get("since") or "")[:10],
            "per_keyword": query.get("per_keyword"),
        }

    async def search_posts(self, platform: str, query: dict) -> VendorResponse:
        raise self.unsupported(f"search.{platform}")
