from src.providers.registry import ProviderAdapter, VendorResponse


class SocialSearchAdapter(ProviderAdapter):
    def vendor_query(self, platform: str, query: dict) -> dict:
        return {
            "platform": platform,
            "keywords": query.get("keywords"),
            "since": str(query.get("since") or "")[:10],
            "limit": query.get("limit"),
        }

    async def search_posts(self, platform: str, query: dict) -> VendorResponse:
        raise self.unsupported(f"search.{platform}")
