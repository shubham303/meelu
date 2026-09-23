from src.providers.registry import ProviderAdapter, VendorResponse


class ProspectSourcesAdapter(ProviderAdapter):
    async def search_prospects(self, source: str, query: dict) -> VendorResponse:
        raise self.unsupported(f"prospects.{source}")
