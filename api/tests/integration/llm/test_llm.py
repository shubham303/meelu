import asyncio
import json
import time

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from src.credits.limiter import paid_calls
from src.llm import service as llm_module
from src.llm.catalog import ModelCatalog
from src.llm.schemas import LlmModelResponse
from src.llm.service import CallContext, llm_service
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
        self.generation_cost: float | None = None

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            if self.generation_cost is None:
                return httpx.Response(404, json={"error": {"message": "not found"}})
            return httpx.Response(200, json={"data": {"total_cost": self.generation_cost}})
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

    await settled()
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
    call = await latest_call(client)
    assert call["chargedMicros"] == 2000


async def test_upstream_errors_pass_through_and_cost_nothing(client, email, openrouter):
    await signup(client, email)
    before = await balance_usd(client)
    r = await client.post(
        "/api/v1/llm/v1/messages",
        json={"model": "openai/gpt-6-luna", "stream": True, "max_tokens": 10, "messages": []},
    )
    assert r.status_code == 429
    assert r.json() == {"error": {"message": "rate limited"}}
    assert await balance_usd(client) == before
    call = await latest_call(client)
    assert (call["status"], call["chargedMicros"]) == ("error", 0)


async def test_unknown_model_and_empty_balance_are_refused(client, email, openrouter):
    await signup(client, email)
    r = await client.post(
        "/api/v1/llm/v1/messages", json={"model": "openai/no-tools", "messages": []}
    )
    assert r.status_code == 400
    assert r.json()["error"]["type"] == "invalid_request_error"

    await set_balance(await user_id_of(client), 0.05)
    r = await client.post("/api/v1/llm/v1/messages", json={"max_tokens": 10, "messages": []})
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


async def settled():
    await asyncio.gather(*llm_service._settling)


async def usage_entries(client):
    await settled()
    r = await client.get("/api/v1/credits/ledger?page_size=50")
    return [e["deltaMicros"] for e in r.json()["data"] if e["kind"] == "usage"]


async def latest_call(client):
    await settled()
    return (await client.get("/api/v1/llm/calls")).json()["data"][0]


PRICEY = LlmModelResponse(
    id="x/pricey",
    name="Pricey",
    provider="x",
    tier="other",
    input_usd_per_million=1.0,
    output_usd_per_million=600.0,
    context_length=0,
)


async def start_call(user_id, model=None):
    model = model or await llm_module.model_catalog.get("anthropic/claude-haiku-5.5")
    await paid_calls.acquire(user_id)
    return CallContext(user_id, None, "agent", model, time.monotonic())


def slot_freed(user_id):
    return user_id not in paid_calls._slots


def frames(*events):
    return "".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n" for e in events).encode()


async def chunks(*parts):
    for part in parts:
        yield part


async def relay(call, *parts):
    out = b"".join(
        [
            chunk
            async for chunk in llm_service._relay(call, httpx.Response(200, content=chunks(*parts)))
        ]
    )
    await asyncio.gather(*llm_service._settling)
    return out.decode()


async def test_only_known_message_fields_reach_openrouter(client, email, openrouter):
    await signup(client, email)
    r = await client.post(
        "/api/v1/llm/v1/messages",
        json={
            "max_tokens": 5,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": "hi"}],
            "models": ["openai/gpt-6-luna"],
            "provider": {"order": ["somewhere"]},
            "plugins": [{"id": "web"}],
            "service_tier": "priority",
        },
    )
    assert r.status_code == 200, r.text
    sent = json.loads(openrouter.requests[-1].content)
    assert set(sent) == {"model", "max_tokens", "temperature", "messages"}


async def test_max_tokens_above_the_cap_is_lowered_before_openrouter(
    client, email, openrouter, monkeypatch
):
    monkeypatch.setattr(settings, "llm_max_output_tokens", 1000)
    await signup(client, email)
    r = await client.post(
        "/api/v1/llm/v1/messages",
        json={"max_tokens": 1_000_000, "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 200, r.text
    assert json.loads(openrouter.requests[-1].content)["max_tokens"] == 1000


async def test_a_request_over_the_size_limit_is_refused(client, email, openrouter, monkeypatch):
    monkeypatch.setattr(settings, "llm_max_request_mb", 0.01)
    await signup(client, email)
    r = await client.post(
        "/api/v1/llm/v1/messages",
        json={"max_tokens": 5, "messages": [{"role": "user", "content": "x" * 20_000}]},
    )
    assert r.status_code == 413
    assert r.json()["error"]["type"] == "request_too_large"
    assert openrouter.requests == []


async def test_a_message_without_max_tokens_is_refused(client, email, openrouter):
    await signup(client, email)
    for max_tokens in (None, 0, "50", True):
        body = {"messages": [{"role": "user", "content": "hi"}]}
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        r = await client.post("/api/v1/llm/v1/messages", json=body)
        assert r.status_code == 400, max_tokens
    assert openrouter.requests == []


async def test_a_message_frees_its_slot(client, email, openrouter):
    await signup(client, email)
    r = await client.post(
        "/api/v1/llm/v1/messages",
        json={"max_tokens": 5, "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 200, r.text
    assert slot_freed(await user_id_of(client))


async def test_a_workspace_below_the_minimum_is_refused(client, email, openrouter):
    await signup(client, email)
    user_id = await user_id_of(client)
    await set_balance(user_id, 0.19)

    r = await client.post(
        "/api/v1/llm/v1/messages",
        json={"max_tokens": 5, "messages": [{"role": "user", "content": "hi"}]},
    )
    assert r.status_code == 402
    assert r.json()["error"]["type"] == "billing_error"
    assert openrouter.requests == []
    assert slot_freed(user_id)


async def test_a_message_past_the_parallel_limit_waits_for_a_slot(
    client, email, openrouter, monkeypatch
):
    monkeypatch.setattr(settings, "credits_parallel_calls_per_user", 1)
    await signup(client, email)
    user_id = await user_id_of(client)
    await paid_calls.acquire(user_id)

    waiting = asyncio.create_task(
        client.post(
            "/api/v1/llm/v1/messages",
            json={"max_tokens": 5, "messages": [{"role": "user", "content": "hi"}]},
        )
    )
    await asyncio.sleep(0.2)
    assert not waiting.done()
    assert openrouter.requests == []

    paid_calls.release(user_id)
    r = await asyncio.wait_for(waiting, 5)
    assert r.status_code == 200, r.text
    assert slot_freed(user_id)


LONG_ANSWER = frames(
    {
        "type": "message_start",
        "message": {"id": "gen-long", "usage": {"input_tokens": 10, "output_tokens": 1}},
    },
    {
        "type": "content_block_delta",
        "index": 0,
        "delta": {"type": "text_delta", "text": "a" * 3000},
    },
)
LONG_ANSWER_END = frames(
    {"type": "message_delta", "usage": {"input_tokens": 10, "output_tokens": 1000, "cost": 0.9}},
    {"type": "message_stop"},
)


async def test_a_message_that_gets_no_slot_in_time_is_refused(
    client, email, openrouter, monkeypatch
):
    monkeypatch.setattr(settings, "credits_parallel_calls_per_user", 1)
    monkeypatch.setattr(settings, "credits_slot_wait_seconds", 0.1)
    await signup(client, email)
    user_id = await user_id_of(client)
    await paid_calls.acquire(user_id)
    try:
        r = await client.post(
            "/api/v1/llm/v1/messages",
            json={"max_tokens": 5, "messages": [{"role": "user", "content": "hi"}]},
        )
    finally:
        paid_calls.release(user_id)

    assert r.status_code == 429
    assert r.json()["error"]["type"] == "rate_limit_error"
    assert openrouter.requests == []
    assert slot_freed(user_id)


async def test_a_long_stream_is_charged_once_what_openrouter_reports(client, email, openrouter):
    await signup(client, email)
    user_id = await user_id_of(client)
    await set_balance(user_id, 0.5)

    out = await relay(await start_call(user_id, PRICEY), LONG_ANSWER, LONG_ANSWER_END)

    assert "message_stop" in out and "billing_error" not in out
    call = await latest_call(client)
    assert (call["status"], call["chargedMicros"]) == ("ok", 900_000)
    assert await usage_entries(client) == [-900_000]
    assert await balance_usd(client) == pytest.approx(-0.4)
    assert slot_freed(user_id)


DROPPED = sse(
    {
        "type": "message_start",
        "message": {"id": "gen-dropped", "usage": {"input_tokens": 1200, "output_tokens": 1}},
    },
    {
        "type": "content_block_delta",
        "index": 0,
        "delta": {"type": "text_delta", "text": "Hello world"},
    },
)


async def drop_stream_after_first_chunk(user_id):
    call = await start_call(user_id)
    stream = llm_service._relay(call, httpx.Response(200, content=DROPPED.encode()))
    await stream.__anext__()
    await stream.aclose()
    await asyncio.gather(*llm_service._settling)


async def test_a_dropped_stream_is_charged_what_openrouter_billed(
    client, email, openrouter, monkeypatch
):
    monkeypatch.setattr("src.llm.service.GENERATION_POLL_DELAYS", (0.0,))
    openrouter.generation_cost = 0.03
    await signup(client, email)
    user_id = await user_id_of(client)
    before = await balance_usd(client)

    await drop_stream_after_first_chunk(user_id)

    call = await latest_call(client)
    assert (call["status"], call["chargedMicros"]) == ("cancelled", 30_000)
    assert await usage_entries(client) == [-30_000]
    assert slot_freed(user_id)
    assert await balance_usd(client) == pytest.approx(before - 0.03)


async def test_a_dropped_stream_openrouter_never_prices_is_not_charged(
    client, email, openrouter, monkeypatch
):
    monkeypatch.setattr("src.llm.service.GENERATION_POLL_DELAYS", (0.0,))
    await signup(client, email)
    user_id = await user_id_of(client)
    before = await balance_usd(client)

    await drop_stream_after_first_chunk(user_id)

    call = await latest_call(client)
    assert (call["status"], call["chargedMicros"]) == ("cancelled", 0)
    assert await usage_entries(client) == []
    assert await balance_usd(client) == pytest.approx(before)
    assert slot_freed(user_id)


async def test_a_finished_message_without_a_cost_is_charged_the_generation_cost(
    client, email, openrouter, monkeypatch
):
    def no_cost(request):
        if request.url.path.endswith("/generation"):
            return httpx.Response(200, json={"data": {"total_cost": 0.002}})
        return httpx.Response(
            200,
            json={
                "id": "msg_free",
                "type": "message",
                "content": [{"type": "text", "text": "ok"}],
                "usage": {"input_tokens": 10, "output_tokens": 5},
            },
        )

    monkeypatch.setattr("src.llm.service.GENERATION_POLL_DELAYS", (0.0,))
    await signup(client, email)
    before = await balance_usd(client)
    upstream = httpx.AsyncClient(transport=httpx.MockTransport(no_cost))
    monkeypatch.setattr("src.llm.service.client", lambda: upstream)

    r = await client.post(
        "/api/v1/llm/v1/messages",
        json={"max_tokens": 5, "messages": [{"role": "user", "content": "hi"}]},
    )

    assert r.status_code == 200, r.text
    assert (await latest_call(client))["chargedMicros"] == 2000
    assert await balance_usd(client) == pytest.approx(before - 0.002)
    assert slot_freed(await user_id_of(client))


async def test_a_stream_past_the_time_limit_is_cut_off(client, email, openrouter, monkeypatch):
    monkeypatch.setattr(settings, "llm_stream_max_seconds", 0.0)
    await signup(client, email)
    user_id = await user_id_of(client)

    out = await relay(await start_call(user_id), LONG_ANSWER, LONG_ANSWER_END)

    assert "api_error" in out and "message_stop" not in out
    assert (await latest_call(client))["status"] == "error"
    assert slot_freed(user_id)
