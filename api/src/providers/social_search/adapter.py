from src.providers.registry import ProviderAdapter, VendorResponse


class SocialSearchAdapter(ProviderAdapter):
    async def search_posts(self, platform: str, query: dict) -> VendorResponse:
        raise self.unsupported(f"search.{platform}")
