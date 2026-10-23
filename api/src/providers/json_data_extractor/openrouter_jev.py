from typing import Any

from src.providers.errors import ProviderRequestError
from src.providers.http import vendor_request
from src.providers.json_data_extractor.adapter import CLASSIFY, JsonDataExtractorAdapter, Question
from src.providers.json_data_extractor.openrouter_deepseek import micros_of
from src.providers.registry import VendorResponse
from src.settings import settings


def read_answer(provider_id: str, body: Any, key: str, question: Question) -> dict[str, Any]:
    answer = ((body or {}).get("answers") or {}).get(key) or {}
    if question["type"] == "noul" and isinstance(answer.get("noul"), (int, float)):
        return {"type": "noul", "noul": min(max(float(answer["noul"]), 0.0), 1.0)}
    if question["type"] == "choice" and answer.get("choice") in question["criteria"]:
        confidence = answer.get("confidence")
        return {
            "type": "choice",
            "choice": answer["choice"],
            "confidence": float(confidence) if isinstance(confidence, (int, float)) else None,
        }
    raise ProviderRequestError(provider_id, 502, f"Jev gave no valid answer for {key}", body)


class OpenRouterJevAdapter(JsonDataExtractorAdapter):
    id = "openrouter-jev"
    name = "OpenRouter · Jev"
    capabilities = frozenset({CLASSIFY})

    def configured(self) -> bool:
        return bool(settings.openrouter_api_key)

    async def classify(self, state: Any, questions: dict[str, Question]) -> VendorResponse:
        body = await vendor_request(
            self.id,
            settings.openrouter_base_url.rstrip("/") + "/alpha/decisions",
            method="POST",
            headers={
                "authorization": f"Bearer {settings.openrouter_api_key.strip()}",
                "x-title": "Meelu",
            },
            json_body={
                "model": settings.openrouter_decision_model,
                "state": state,
                "questions": questions,
            },
            timeout_s=120,
        )
        answers = {key: read_answer(self.id, body, key, q) for key, q in questions.items()}
        return VendorResponse(
            {"model": body.get("model"), "answers": answers},
            micros_of(body.get("usage") or {}),
        )
