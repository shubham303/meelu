import json
from typing import Any

from src.providers.errors import ProviderRequestError
from src.providers.http import vendor_request
from src.providers.json_data_extractor.adapter import (
    DECIDE,
    EXTRACT,
    JsonDataExtractorAdapter,
    Question,
)
from src.providers.registry import VendorResponse
from src.settings import settings

SYSTEM_PROMPT = (
    "You answer classification questions about the data in the user message. "
    "For each question pick exactly one of its allowed choices, judged against the criteria "
    "given for each choice, and give your confidence from 0 to 1 that the choice is right. "
    "Answer with JSON only."
)

EXTRACT_SYSTEM_PROMPT = (
    "You read the data in the user message and answer the instructions given with it. "
    "Use only what the data says. Answer with JSON that matches the schema, and nothing else."
)


def micros_of(usage: dict[str, Any]) -> int:
    cost = usage.get("cost")
    return round(cost * 1_000_000) if isinstance(cost, (int, float)) else 0


def answer_schema(questions: dict[str, Question]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            key: {
                "type": "object",
                "properties": {
                    "choice": {"type": "string", "enum": list(question["criteria"])},
                    "confidence": {"type": "number"},
                },
                "required": ["choice", "confidence"],
                "additionalProperties": False,
            }
            for key, question in questions.items()
        },
        "required": list(questions),
        "additionalProperties": False,
    }


def user_prompt(state: Any, questions: dict[str, Question]) -> str:
    asked = {
        key: {"question": question["instructions"], "choices": question["criteria"]}
        for key, question in questions.items()
    }
    return json.dumps({"data": state, "questions": asked}, ensure_ascii=False)


def read_answers(
    provider_id: str, body: Any, questions: dict[str, Question]
) -> dict[str, dict[str, Any]]:
    try:
        content = body["choices"][0]["message"]["content"]
        parsed = json.loads(content)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ProviderRequestError(
            provider_id, 502, "OpenRouter returned no JSON answer", body
        ) from exc
    answers: dict[str, dict[str, Any]] = {}
    for key, question in questions.items():
        answer = parsed.get(key) if isinstance(parsed, dict) else None
        choice = (answer or {}).get("choice")
        if choice not in question["criteria"]:
            raise ProviderRequestError(
                provider_id, 502, f"OpenRouter gave no valid choice for {key}", body
            )
        confidence = answer.get("confidence")
        answers[key] = {
            "type": "choice",
            "choice": choice,
            "confidence": min(max(float(confidence), 0.0), 1.0)
            if isinstance(confidence, (int, float))
            else None,
        }
    return answers


def read_json(provider_id: str, body: Any) -> Any:
    try:
        return json.loads(body["choices"][0]["message"]["content"])
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ProviderRequestError(
            provider_id, 502, "OpenRouter returned no JSON answer", body
        ) from exc


class OpenRouterDeepSeekAdapter(JsonDataExtractorAdapter):
    id = "openrouter-deepseek"
    name = "OpenRouter · DeepSeek"
    capabilities = frozenset({DECIDE, EXTRACT})

    def configured(self) -> bool:
        return bool(settings.openrouter_api_key)

    def headers(self) -> dict[str, str]:
        return {
            "authorization": f"Bearer {settings.openrouter_api_key.strip()}",
            "x-title": "Meelu",
        }

    async def complete(
        self,
        system: str,
        user: str,
        name: str,
        schema: dict[str, Any],
        timeout_s: float,
        reasoning: bool,
    ) -> Any:
        return await vendor_request(
            self.id,
            settings.openrouter_base_url.rstrip("/") + "/v1/chat/completions",
            method="POST",
            headers=self.headers(),
            json_body={
                "model": settings.openrouter_model,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": name, "strict": True, "schema": schema},
                },
                "usage": {"include": True},
                "reasoning": {"enabled": reasoning},
            },
            timeout_s=timeout_s,
        )

    async def decide(self, state: Any, questions: dict[str, Question]) -> VendorResponse:
        body = await self.complete(
            SYSTEM_PROMPT,
            user_prompt(state, questions),
            "answers",
            answer_schema(questions),
            120,
            reasoning=False,
        )
        answers = read_answers(self.id, body, questions)
        return VendorResponse(
            {"model": body.get("model"), "answers": answers},
            micros_of(body.get("usage") or {}),
        )

    async def extract(self, instructions: str, data: Any, schema: dict[str, Any]) -> VendorResponse:
        body = await self.complete(
            EXTRACT_SYSTEM_PROMPT,
            json.dumps({"instructions": instructions, "data": data}, ensure_ascii=False),
            "result",
            schema,
            300,
            reasoning=True,
        )
        return VendorResponse(
            {"model": body.get("model"), "result": read_json(self.id, body)},
            micros_of(body.get("usage") or {}),
        )
