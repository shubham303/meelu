import asyncio
import time
from typing import Any

from src.llm.schemas import LlmModelResponse
from src.providers.errors import ProviderRequestError
from src.providers.http import vendor_request
from src.settings import settings

PROVIDER_ID = "openrouter"
WELL_KNOWN_PROVIDERS = frozenset(
    {"anthropic", "openai", "deepseek", "google", "x-ai", "qwen", "moonshotai", "z-ai", "mistralai"}
)


def _per_million(value: Any) -> float | None:
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    return round(price * 1_000_000, 4) if price >= 0 else None


def _listable(entry: dict[str, Any]) -> bool:
    model_id = entry.get("id")
    if not isinstance(model_id, str) or ":" in model_id or model_id.startswith("~"):
        return False
    return "tools" in (entry.get("supported_parameters") or [])


def _model(entry: dict[str, Any], featured: list[str]) -> LlmModelResponse | None:
    pricing = entry.get("pricing") or {}
    input_price = _per_million(pricing.get("prompt"))
    output_price = _per_million(pricing.get("completion"))
    if input_price is None or output_price is None:
        return None
    model_id = entry["id"]
    provider = model_id.split("/", 1)[0]
    tier = (
        "featured"
        if model_id in featured
        else "well_known"
        if provider in WELL_KNOWN_PROVIDERS
        else "other"
    )
    return LlmModelResponse(
        id=model_id,
        name=str(entry.get("name") or model_id),
        provider=provider,
        tier=tier,
        input_usd_per_million=input_price,
        output_usd_per_million=output_price,
        context_length=int(entry.get("context_length") or 0),
    )


def rank(entries: list[dict[str, Any]], featured: list[str]) -> list[LlmModelResponse]:
    models = [m for e in entries if _listable(e) and (m := _model(e, featured))]
    tier_order = {"featured": 0, "well_known": 1, "other": 2}

    def key(m: LlmModelResponse) -> tuple:
        position = featured.index(m.id) if m.id in featured else 0
        return (
            tier_order[m.tier],
            position,
            m.input_usd_per_million + m.output_usd_per_million,
            m.id,
        )

    return sorted(models, key=key)


class ModelCatalog:
    def __init__(self) -> None:
        self._models: list[LlmModelResponse] = []
        self._by_id: dict[str, LlmModelResponse] = {}
        self._fetched_at = 0.0
        self._lock = asyncio.Lock()

    async def download(self) -> list[dict[str, Any]]:
        body = await vendor_request(PROVIDER_ID, f"{settings.openrouter_base_url}/v1/models")
        data = body.get("data") if isinstance(body, dict) else None
        if not isinstance(data, list):
            raise ProviderRequestError(PROVIDER_ID, 502, "OpenRouter returned no model list", body)
        return [e for e in data if isinstance(e, dict)]

    async def models(self) -> list[LlmModelResponse]:
        if self._models and time.monotonic() - self._fetched_at < settings.llm_catalog_ttl_seconds:
            return self._models
        async with self._lock:
            if (
                self._models
                and time.monotonic() - self._fetched_at < settings.llm_catalog_ttl_seconds
            ):
                return self._models
            self._models = rank(await self.download(), settings.llm_featured_models)
            self._by_id = {m.id: m for m in self._models}
            self._fetched_at = time.monotonic()
        return self._models

    async def get(self, model_id: str) -> LlmModelResponse | None:
        await self.models()
        return self._by_id.get(model_id)


model_catalog = ModelCatalog()
