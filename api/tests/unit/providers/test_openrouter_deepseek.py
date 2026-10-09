import json

import pytest

from src.providers.errors import ProviderRequestError
from src.providers.json_data_extractor import openrouter_deepseek
from src.providers.json_data_extractor.openrouter_deepseek import (
    OpenRouterDeepSeekAdapter,
    micros_of,
)

QUESTIONS = {
    "page_type": {
        "type": "choice",
        "instructions": "What is this page for?",
        "criteria": {"money": "sells", "legal": "terms or privacy"},
    }
}


def completion(content: dict | str, cost: float = 0.0002) -> dict:
    text = content if isinstance(content, str) else json.dumps(content)
    return {
        "model": "deepseek/deepseek-v4.1-flash",
        "choices": [{"message": {"role": "assistant", "content": text}}],
        "usage": {"prompt_tokens": 300, "completion_tokens": 20, "cost": cost},
    }


def test_cost_comes_from_reported_usage():
    assert micros_of({"cost": 0.00004}) == 40
    assert micros_of({}) == 0


async def test_decide_posts_a_strict_schema_and_reads_the_choice(monkeypatch):
    seen = {}

    async def fake_request(provider_id, url, **kw):
        seen.update(url=url, body=kw["json_body"], headers=kw["headers"])
        return completion({"page_type": {"choice": "legal", "confidence": 0.92}})

    monkeypatch.setattr(openrouter_deepseek, "vendor_request", fake_request)
    monkeypatch.setattr(openrouter_deepseek.settings, "openrouter_api_key", "k")
    adapter = OpenRouterDeepSeekAdapter()
    assert adapter.configured()

    res = await adapter.decide({"url": "https://x.com/privacy"}, QUESTIONS)

    assert seen["url"].endswith("/v1/chat/completions")
    assert seen["headers"]["authorization"] == "Bearer k"
    assert seen["body"]["model"] == openrouter_deepseek.settings.openrouter_model
    schema = seen["body"]["response_format"]["json_schema"]["schema"]
    choice = schema["properties"]["page_type"]["properties"]["choice"]
    assert choice["enum"] == ["money", "legal"]
    assert res.data["answers"]["page_type"] == {
        "type": "choice",
        "choice": "legal",
        "confidence": 0.92,
    }
    assert res.cost_micros == 200


async def test_decide_rejects_a_choice_outside_the_criteria(monkeypatch):
    async def fake_request(provider_id, url, **kw):
        return completion({"page_type": {"choice": "blog", "confidence": 0.9}})

    monkeypatch.setattr(openrouter_deepseek, "vendor_request", fake_request)
    with pytest.raises(ProviderRequestError):
        await OpenRouterDeepSeekAdapter().decide({"url": "u"}, QUESTIONS)


async def test_decide_rejects_text_that_is_not_json(monkeypatch):
    async def fake_request(provider_id, url, **kw):
        return completion("It is a legal page.")

    monkeypatch.setattr(openrouter_deepseek, "vendor_request", fake_request)
    with pytest.raises(ProviderRequestError):
        await OpenRouterDeepSeekAdapter().decide({"url": "u"}, QUESTIONS)
