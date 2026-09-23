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


MOCK_URL_HINTS = {
    "legal": ("privacy", "terms", "cookie", "disclaimer"),
    "utility": ("login", "cart", "checkout", "search", "/tag/", "/author/", "thank"),
    "support": ("faq", "help", "docs", "support", "shipping", "returns"),
    "company": ("about", "team", "careers", "press", "contact", "testimonial"),
    "informational": ("blog/", "guide", "glossary", "news", "/vs", "how-to"),
    "hub": ("category", "collection", "/blog", "topics"),
}


def mock_decision(state: Any, questions: dict[str, Question]) -> VendorResponse:
    url = str(state.get("url", "")).lower() if isinstance(state, dict) else ""
    answers: dict[str, Any] = {}
    for key, q in questions.items():
        if q["type"] == "choice":
            options = list(q["criteria"])
            picked = next(
                (
                    t
                    for t, hints in MOCK_URL_HINTS.items()
                    if t in options and any(h in url for h in hints)
                ),
                options[0],
            )
            probabilities = {o: 0.1 / max(len(options) - 1, 1) for o in options}
            probabilities[picked] = 0.9
            answers[key] = {
                "type": "choice",
                "choice": picked,
                "probabilities": probabilities,
                "confidence": 0.9,
            }
        elif q["type"] == "noul":
            answers[key] = {"type": "noul", "noul": 0.5}
        else:
            levels = q["criteria"]
            answers[key] = {
                "type": "score",
                "score": 0,
                "legend": {str(i): str(l) for i, l in enumerate(levels)},
                "probabilities": {str(i): 1 / len(levels) for i in range(len(levels))},
                "confidence": 0.0,
            }
    return VendorResponse(
        {"model": f"{settings.openrouter_jev_model} (mocked)", "answers": answers}, 21
    )


class OpenRouterJevAdapter(JsonDataExtractorAdapter):
    id = "openrouter-jev"
    name = "OpenRouter · TypeSafe Jev"
    capabilities = frozenset({DECIDE})

    def configured(self) -> bool:
        # MOCKED — always "configured" so the crawl → classify flow can be tested without
        # OpenRouter credits. Restore `return bool(settings.openrouter_api_key)` before going live.
        return True

    def headers(self) -> dict[str, str]:
        return {
            "authorization": f"Bearer {settings.openrouter_api_key.strip()}",
            "x-title": "Meelu",
        }

    async def decide(self, state: Any, questions: dict[str, Question]) -> VendorResponse:
        # MOCKED — TODO before going live: delete this block so the real request below runs
        # against OpenRouter's /alpha/decisions endpoint. The answer is guessed from the URL
        # only so the rest of the pipeline (loop, upsert, cache, credits, UI) can be exercised.
        return mock_decision(state, questions)

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
