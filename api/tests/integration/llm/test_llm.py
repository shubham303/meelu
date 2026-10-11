import json

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from src.llm.catalog import ModelCatalog
from src.settings import settings
from tests.conftest import signup
from tests.integration.credits.test_site_billing import balance_usd, set_balance, user_id_of

ENTRIES = [
    {
        "id": "zeta/tiny",
        "name": "Tiny",
        "pricing": {"prompt": "0.00000001", "completion": "0.00000002"},
        "context_length": 8000,
        "supported_parameters": ["tools"],
    },
    {
        "id": "openai/gpt-6-luna",
        "name": "Luna",
        "pricing": {"prompt": "0.0000001", "completion": "0.0000005"},
        "context_length": 1050000,
        "supported_parameters": ["tools"],
    },
    {
        "id": "openai/gpt-cheap",
        "name": "Cheap",
        "pricing": {"prompt": "0.00000001", "completion": "0.00000001"},
        "context_length": 1000,
        "supported_parameters": ["tools"],
    },
    {
        "id": "anthropic/claude-haiku-5.5",
        "name": "Haiku",
        "pricing": {"prompt": "0.0000001", "completion": "0.0000005"},
        "context_length": 1000000,
        "supported_parameters": ["tools", "max_tokens"],
    },
    {
        "id": "anthropic/claude-haiku-5.5:batch",
        "name": "Haiku batch",
        "pricing": {"prompt": "0.00000005", "completion": "0.00000025"},
        "supported_parameters": ["tools"],
    },
    {
        "id": "openai/no-tools",
        "name": "No tools",
        "pricing": {"prompt": "0", "completion": "0"},
        "supported_parameters": [],
    },
]


def sse(*events):
    frames = [f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events]
    return "".join(frames) + "event: data\ndata: [DONE]\n\n"


STREAM = sse(
    {
        "type": "message_start",
        "message": {"id": "msg_gen1", "usage": {"input_tokens": 1200, "output_tokens": 1}},
    },
    {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hi"}},
    {
        "type": "message_delta",
        "delta": {"stop_reason": "end_turn"},
        "usage": {
            "input_tokens": 1200,
            "output_tokens": 40,
            "cache_read_input_tokens": 300,
            "cost": 0.0125,
        },
    },
    {"type": "message_stop"},
)


class FakeOpenRouter:
    def __init__(self):
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        body = json.loads(request.content)
        if body["model"] == "openai/gpt-6-luna":
            return httpx.Response(429, json={"error": {"message": "rate limited"}})
        if body.get("stream"):
            return httpx.Response(
                200, content=STREAM.encode(), headers={"content-type": "text/event-stream"}
            )
        return httpx.Response(
            200,
            json={
                "id": "msg_gen2",
                "type": "message",
                "content": [{"type": "text", "text": "ok"}],
                "usage": {"input_tokens": 10, "output_tokens": 5, "cost": 0.002},
            },
        )


@pytest.fixture
def openrouter(monkeypatch):
    fake = FakeOpenRouter()
    catalog = ModelCatalog()

    async def download():
        return ENTRIES

    monkeypatch.setattr(catalog, "download", download)
    monkeypatch.setattr("src.llm.service.model_catalog", catalog)
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(fake))
    monkeypatch.setattr("src.llm.service.client", lambda: upstream)
    monkeypatch.setattr(settings, "openrouter_api_key", "sk-or-server")
    return fake


async def api_key(client):
    r = await client.post("/api/v1/keys", json={"name": "harness"})
    assert r.status_code == 201, r.text
    return r.json()["data"]["key"]


async def bearer_client(key):
    from src.app import app

    return AsyncClient(
        transport=ASGITransport(app=app),
        base_url="https://test",
        headers={"authorization": f"Bearer {key}", "anthropic-version": "2023-06-01"},
    )


async def test_models_put_the_featured_ones_first(client, email, openrouter):
    await signup(client, email)
    r = await client.get("/api/v1/llm/models")
    assert r.status_code == 200, r.text
    models = r.json()["data"]
    assert [m["id"] for m in models] == [
        "anthropic/claude-haiku-5.5",
        "openai/gpt-6-luna",
        "openai/gpt-cheap",
        "zeta/tiny",
    ]
    assert models[0] == {
        "id": "anthropic/claude-haiku-5.5",
        "name": "Haiku",
        "provider": "anthropic",
        "tier": "featured",
        "inputUsdPerMillion": 0.1,
        "outputUsdPerMillion": 0.5,
        "contextLength": 1000000,
    }
    assert [m["tier"] for m in models[2:]] == ["well_known", "other"]


async def test_preference_defaults_to_haiku_and_only_takes_offered_models(
    client, email, openrouter
):
    await signup(client, email)
    r = await client.get("/api/v1/llm/preference")
    assert r.json()["data"] == {"defaultModel": "anthropic/claude-haiku-5.5"}

    r = await client.put("/api/v1/llm/preference", json={"defaultModel": "openai/no-tools"})
    assert r.status_code == 400

    r = await client.put("/api/v1/llm/preference", json={"defaultModel": "zeta/tiny"})
    assert r.status_code == 200
    assert (await client.get("/api/v1/llm/preference")).json()["data"] == {
        "defaultModel": "zeta/tiny"
    }


async def test_streamed_message_relays_anthropic_events_and_charges_the_cost(
    client, email, openrouter
):
    await signup(client, email)
    key = await api_key(client)
    before = await balance_usd(client)

    async with await bearer_client(key) as harness:
        r = await harness.post(
            "/api/v1/llm/v1/messages",
            headers={"x-meelu-purpose": "social_listening"},
            json={
                "model": "anthropic/claude-haiku-5.5",
                "stream": True,
                "max_tokens": 50,
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/event-stream")
    assert "[DONE]" not in r.text
    assert '"type": "message_stop"' in r.text

    sent = openrouter.requests[-1]
    assert sent.headers["authorization"] == "Bearer sk-or-server"
    assert sent.headers["anthropic-version"] == "2023-06-01"

    assert await balance_usd(client) == pytest.approx(before - 0.0125)
    r = await client.get("/api/v1/llm/calls")
    call = r.json()["data"][0]
    assert call["model"] == "anthropic/claude-haiku-5.5"
    assert call["purpose"] == "social_listening"
    assert call["status"] == "ok"
    assert (call["inputTokens"], call["outputTokens"], call["cacheReadTokens"]) == (1200, 40, 300)
    assert call["costMicros"] == call["chargedMicros"] == 12500


async def test_single_message_comes_back_unwrapped(client, email, openrouter):
    await signup(client, email)
    key = await api_key(client)
    async with await bearer_client(key) as harness:
        r = await harness.post(
            "/api/v1/llm/v1/messages",
            json={"max_tokens": 5, "messages": [{"role": "user", "content": "hi"}]},
        )
    assert r.status_code == 200, r.text
    assert r.json()["id"] == "msg_gen2"
    assert json.loads(openrouter.requests[-1].content)["model"] == "anthropic/claude-haiku-5.5"
    call = (await client.get("/api/v1/llm/calls")).json()["data"][0]
    assert call["chargedMicros"] == 2000


async def test_upstream_errors_pass_through_and_cost_nothing(client, email, openrouter):
    await signup(client, email)
    before = await balance_usd(client)
    r = await client.post(
        "/api/v1/llm/v1/messages",
        json={"model": "openai/gpt-6-luna", "stream": True, "messages": []},
    )
    assert r.status_code == 429
    assert r.json() == {"error": {"message": "rate limited"}}
    assert await balance_usd(client) == before
    call = (await client.get("/api/v1/llm/calls")).json()["data"][0]
    assert (call["status"], call["chargedMicros"]) == ("error", 0)


async def test_unknown_model_and_empty_balance_are_refused(client, email, openrouter):
    await signup(client, email)
    r = await client.post(
        "/api/v1/llm/v1/messages", json={"model": "openai/no-tools", "messages": []}
    )
    assert r.status_code == 400
    assert r.json()["error"]["type"] == "invalid_request_error"

    await set_balance(await user_id_of(client), 0.05)
    r = await client.post("/api/v1/llm/v1/messages", json={"messages": []})
    assert r.status_code == 402
    assert r.json()["type"] == "error"
    assert r.json()["error"]["type"] == "billing_error"
    assert openrouter.requests == []


async def test_messages_need_a_key_or_session(openrouter):
    from src.app import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as anon:
        r = await anon.post("/api/v1/llm/v1/messages", json={"messages": []})
        assert r.status_code == 401
        r = await anon.post(
            "/api/v1/llm/v1/messages",
            json={"messages": []},
            headers={"authorization": "Bearer emcp_wrong"},
        )
        assert r.status_code == 401
