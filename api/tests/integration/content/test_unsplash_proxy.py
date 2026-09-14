import httpx
import pytest

from src.integrations.unsplash import unsplash
from src.settings import settings

SEARCH_PAYLOAD = {
    "total": 2,
    "total_pages": 1,
    "results": [
        {
            "id": "eOLpJytrbsQ",
            "width": 5245,
            "height": 3497,
            "color": "#60544D",
            "alt_description": "A pour-over brewer on a wooden counter",
            "description": None,
            "urls": {
                "regular": "https://images.unsplash.com/photo-1?w=1080",
                "small": "https://images.unsplash.com/photo-1?w=400",
            },
            "user": {"name": "Jeff Sheldon", "username": "ugmonk"},
            "links": {"download_location": "https://api.unsplash.com/photos/eOLpJytrbsQ/download"},
        }
    ],
}


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.setattr(settings, "unsplash_access_key", "unsplash-test-key")


@pytest.fixture
def transport(monkeypatch):
    calls: list[httpx.Request] = []

    def install(handler):
        def record(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            return handler(request)

        client = httpx.AsyncClient(
            base_url="https://api.unsplash.com",
            transport=httpx.MockTransport(record),
        )
        monkeypatch.setattr(unsplash, "_client", client)
        monkeypatch.setattr(unsplash, "attempts", 1)
        return calls

    return install


async def test_search_returns_camel_case_photos(client, workspace, transport):
    calls = transport(lambda request: httpx.Response(200, json=SEARCH_PAYLOAD))

    r = await client.get(
        "/api/v1/content/unsplash", params={"q": "coffee", "orientation": "landscape"}
    )
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    assert body["configured"] is True
    assert body["total"] == 2
    assert body["totalPages"] == 1
    assert body["photos"] == [
        {
            "id": "eOLpJytrbsQ",
            "thumbUrl": "https://images.unsplash.com/photo-1?w=400",
            "url": "https://images.unsplash.com/photo-1?w=1080",
            "alt": "A pour-over brewer on a wooden counter",
            "width": 5245,
            "height": 3497,
            "color": "#60544D",
            "creditName": "Jeff Sheldon",
            "creditUrl": "https://unsplash.com/@ugmonk?utm_source=meelu&utm_medium=referral",
            "downloadLocation": ("https://api.unsplash.com/photos/eOLpJytrbsQ/download"),
        }
    ]

    assert calls[0].url.params["query"] == "coffee"
    assert calls[0].url.params["orientation"] == "landscape"
    assert calls[0].headers["authorization"] == "Client-ID unsplash-test-key"


async def test_search_without_a_term_never_calls_unsplash(client, workspace, transport):
    calls = transport(lambda request: httpx.Response(200, json=SEARCH_PAYLOAD))

    r = await client.get("/api/v1/content/unsplash")
    assert r.status_code == 200
    assert r.json()["data"] == {
        "configured": True,
        "photos": [],
        "total": 0,
        "totalPages": 0,
    }
    assert calls == []


async def test_search_reports_not_configured(client, workspace, monkeypatch, transport):
    transport(lambda request: httpx.Response(200, json=SEARCH_PAYLOAD))
    monkeypatch.setattr(settings, "unsplash_access_key", "")

    r = await client.get("/api/v1/content/unsplash")
    assert r.json()["data"]["configured"] is False

    r = await client.get("/api/v1/content/unsplash", params={"q": "coffee"})
    assert r.status_code == 501
    assert r.json()["error"]["message"].startswith("Unsplash search isn't configured.")


async def test_search_maps_upstream_failures(client, workspace, transport):
    transport(lambda request: httpx.Response(403, json={"errors": ["Rate Limit Exceeded"]}))
    r = await client.get("/api/v1/content/unsplash", params={"q": "coffee"})
    assert r.status_code == 429
    assert r.json()["error"]["message"] == (
        "Unsplash's hourly search limit is used up. Try again later, or upload an image instead."
    )

    transport(lambda request: httpx.Response(403, json={"errors": ["OAuth error"]}))
    r = await client.get("/api/v1/content/unsplash", params={"q": "coffee"})
    assert r.status_code == 502
    assert r.json()["error"]["message"] == ("Unsplash refused the request. Check the access key.")

    transport(lambda request: httpx.Response(404, json={"errors": ["Not found"]}))
    r = await client.get("/api/v1/content/unsplash", params={"q": "coffee"})
    assert r.status_code == 502
    assert r.json()["error"]["message"] == "Unsplash search failed (404)."

    def unreachable(request):
        raise httpx.ConnectError("no route", request=request)

    transport(unreachable)
    r = await client.get("/api/v1/content/unsplash", params={"q": "coffee"})
    assert r.status_code == 502
    assert r.json()["error"]["message"] == (
        "Could not reach Unsplash. Check the connection and try again."
    )


async def test_download_trigger(client, workspace, transport):
    calls = transport(lambda request: httpx.Response(200, json={"url": "x"}))

    r = await client.post("/api/v1/content/unsplash", json={})
    assert r.status_code == 400
    assert r.json()["error"]["message"] == "Missing downloadLocation."

    r = await client.post(
        "/api/v1/content/unsplash",
        json={"downloadLocation": "https://example.com/photos/1/download"},
    )
    assert r.status_code == 400
    assert r.json()["error"]["message"] == ("That is not an Unsplash download location.")
    assert calls == []

    r = await client.post(
        "/api/v1/content/unsplash",
        json={"downloadLocation": "https://api.unsplash.com/photos/eOLpJytrbsQ/download"},
    )
    assert r.status_code == 200
    assert r.json() == {"data": {"ok": True}}
    assert len(calls) == 1


async def test_download_swallows_upstream_errors(client, workspace, transport):
    transport(lambda request: httpx.Response(500, json={"errors": ["boom"]}))

    r = await client.post(
        "/api/v1/content/unsplash",
        json={"downloadLocation": "https://api.unsplash.com/photos/eOLpJytrbsQ/download"},
    )
    assert r.status_code == 200
    assert r.json() == {"data": {"ok": True}}
