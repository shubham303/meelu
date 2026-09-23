from src.core.schemas import EntityModel, JsDateTime


class AdapterStatus(EntityModel):
    id: str
    name: str
    configured: bool
    capabilities: list[str]


class DomainStatus(EntityModel):
    domain: str
    label: str
    adapters: list[AdapterStatus]


class ProviderCallResponse(EntityModel):
    id: str
    site_id: str | None
    domain: str
    capability: str
    provider: str | None
    cache_hit: bool
    vendor_cost_micros: int
    charged_micros: int
    status: str
    error: str | None
    duration_ms: int
    created_at: JsDateTime
