from src.providers.registry import ProviderAdapter, VendorResponse


class PeopleSearchAdapter(ProviderAdapter):
    def vendor_query(self, capability: str, query: dict) -> dict:
        return {"capability": capability, **query}

    async def search_people(self, query: dict) -> VendorResponse:
        raise self.unsupported("search.linkedin")

    async def activity(self, platform: str, query: dict) -> VendorResponse:
        raise self.unsupported(f"activity.{platform}")
