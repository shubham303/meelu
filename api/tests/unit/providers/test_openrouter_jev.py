import pytest

from src.providers.errors import ProviderRequestError
from src.providers.json_data_extractor import openrouter_jev
from src.providers.json_data_extractor.openrouter_jev import OpenRouterJevAdapter, micros_of


def test_cost_prefers_reported_then_input_tokens():
    assert micros_of({"cost": 0.00004}) == 40
    assert micros_of({"input_tokens": 1_000_000}) == 42_000
    assert micros_of({}) == 0


@pytest.mark.skip(reason="decide() is mocked until the OpenRouter endpoint goes live")
async def test_decide_posts_to_decisions_and_returns_answers(monkeypatch):
    seen = {}

    async def fake_request(provider_id, url, **kw):
        seen.update(url=url, body=kw["json_body"], headers=kw["headers"])
        return {
            "model": "~typesafe/jev-latest",
            "answers": {"page_type": {"type": "choice", "choice": "money", "confidence": 0.8}},
            "usage": {"input_tokens": 500, "output_tokens": 0},
        }

    monkeypatch.setattr(openrouter_jev, "vendor_request", fake_request)
    monkeypatch.setattr(openrouter_jev.settings, "openrouter_api_key", "k")
    adapter = OpenRouterJevAdapter()
    assert adapter.configured()
    questions = {"page_type": {"type": "choice", "instructions": "?", "criteria": {"money": "m"}}}
    res = await adapter.decide({"url": "u"}, questions)
    assert seen["url"].endswith("/alpha/decisions")
    assert seen["body"] == {
        "model": "~typesafe/jev-latest",
        "state": {"url": "u"},
        "questions": questions,
    }
    assert seen["headers"]["authorization"] == "Bearer k"
    assert res.data["answers"]["page_type"]["choice"] == "money"
    assert res.cost_micros == 21


@pytest.mark.skip(reason="decide() is mocked until the OpenRouter endpoint goes live")
async def test_decide_rejects_unanswered_questions(monkeypatch):
    async def fake_request(provider_id, url, **kw):
        return {"answers": {}, "usage": {}}

    monkeypatch.setattr(openrouter_jev, "vendor_request", fake_request)
    with pytest.raises(ProviderRequestError):
        await OpenRouterJevAdapter().decide("s", {"q": {"type": "noul", "instructions": "?"}})


async def test_mocked_decide_guesses_from_url():
    questions = {
        "page_type": {
            "type": "choice",
            "instructions": "?",
            "criteria": {"money": "m", "legal": "l"},
        }
    }
    res = await OpenRouterJevAdapter().decide({"url": "https://x.com/privacy"}, questions)
    assert res.data["answers"]["page_type"]["choice"] == "legal"
    assert "mocked" in res.data["model"]
