from typing import Any

from src.providers.errors import ProviderRequestError
from src.providers.http import vendor_request
from src.providers.json_data_extractor.adapter import DECIDE, JsonDataExtractorAdapter, Question
from src.providers.registry import VendorResponse
from src.settings import settings

INPUT_USD_PER_MILLION = 0.042


def micros_of(usage: dict[str, Any]) -> int:
    cost = usage.get("cost")
    if isinstance(cost, (int, float)):
        return round(cost * 1_000_000)
    tokens = usage.get("input_tokens")
    if isinstance(tokens, (int, float)):
        return round(tokens * INPUT_USD_PER_MILLION)
    return 0


class OpenRouterJevAdapter(JsonDataExtractorAdapter):
    id = "openrouter-jev"
    name = "OpenRouter · TypeSafe Jev"
    capabilities = frozenset({DECIDE})

    def configured(self) -> bool:
        return bool(settings.openrouter_api_key)

    def headers(self) -> dict[str, str]:
        return {
            "authorization": f"Bearer {settings.openrouter_api_key.strip()}",
            "x-title": "Meelu",
        }

    async def decide(self, state: Any, questions: dict[str, Question]) -> VendorResponse:
        body = await vendor_request(
            self.id,
            settings.openrouter_base_url.rstrip("/") + "/alpha/decisions",
            method="POST",
            headers=self.headers(),
            json_body={
                "model": settings.openrouter_jev_model,
                "state": state,
                "questions": questions,
            },
            timeout_s=60,
        )
        answers = body.get("answers") if isinstance(body, dict) else None
        if not isinstance(answers, dict):
            raise ProviderRequestError(self.id, 502, "OpenRouter returned no answers", body)
        missing = [k for k in questions if k not in answers]
        if missing:
            raise ProviderRequestError(
                self.id, 502, f"OpenRouter left {', '.join(missing)} unanswered", body
            )
        return VendorResponse(
            {"model": body.get("model"), "answers": answers}, micros_of(body.get("usage") or {})
        )
