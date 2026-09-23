import json
from typing import Any

from src.providers.errors import ProviderRequestError
from src.providers.http import vendor_request
from src.providers.llm_judge.adapter import JUDGE, JsonSchema, LlmJudgeAdapter
from src.providers.registry import VendorResponse
from src.settings import settings


def micros_of(usage: dict[str, Any]) -> int:
    cost = usage.get("cost")
    if isinstance(cost, (int, float)):
        return round(cost * 1_000_000)
    return 0


class OpenRouterChatJudge(LlmJudgeAdapter):
    id = "openrouter-chat"
    name = "OpenRouter · chat model with JSON schema output"
    capabilities = frozenset({JUDGE})

    def configured(self) -> bool:
        return bool(settings.openrouter_api_key)

    def headers(self) -> dict[str, str]:
        return {
            "authorization": f"Bearer {settings.openrouter_api_key.strip()}",
            "x-title": "Meelu",
        }

    async def judge(self, instructions: str, state: Any, schema: JsonSchema) -> VendorResponse:
        body = await vendor_request(
            self.id,
            settings.openrouter_base_url.rstrip("/") + "/v1/chat/completions",
            method="POST",
            headers=self.headers(),
            json_body={
                "model": settings.openrouter_review_model,
                "messages": [
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": json.dumps(state, ensure_ascii=False)},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": "judgement", "strict": True, "schema": schema},
                },
                "usage": {"include": True},
                "temperature": 0,
            },
            timeout_s=90,
        )
        try:
            content = body["choices"][0]["message"]["content"]
            answer = json.loads(content) if isinstance(content, str) else content
        except (KeyError, IndexError, TypeError, ValueError):
            raise ProviderRequestError(self.id, 502, "OpenRouter returned no JSON answer", body)
        if not isinstance(answer, dict):
            raise ProviderRequestError(self.id, 502, "OpenRouter answer is not an object", body)
        return VendorResponse(
            {"model": body.get("model"), "answer": answer}, micros_of(body.get("usage") or {})
        )
