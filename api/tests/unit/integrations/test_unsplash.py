import httpx
import pytest

from src.integrations.base import IntegrationError, TransientIntegrationError
from src.integrations.unsplash import UnsplashClient
from src.settings import settings

SEARCH_PAYLOAD = {
    "total": 133,
    "total_pages": 6,
    "results": [
        {
            "id": "eOLpJytrbsQ",
            "width": 5245,
            "height": 3497,
            "color": "#60544D",
            "alt_description": "A pour-over brewer on a wooden counter",
            "description": None,
            "urls": {
                "raw": "https://images.unsplash.com/photo-1?ixid=raw",
                "full": "https://images.unsplash.com/photo-1?q=85",
                "regular": "https://images.unsplash.com/photo-1?w=1080",
                "small": "https://images.unsplash.com/photo-1?w=400",
                "thumb": "https://images.unsplash.com/photo-1?w=200",
            },
            "user": {"name": "Jeff Sheldon", "username": "ugmonk"},
            "links": {
                "download_location": "https://api.unsplash.com/photos/eOLpJytrbsQ/download?ixid=abc"
            },
        },
        {
            "id": "K9nxgkYf-eQ",
            "width": 4000,
            "height": 6000,
            "color": None,
            "alt_description": None,
            "description": "Steam rising from a ceramic mug",
            "urls": {
                "regular": "https://images.unsplash.com/photo-2?w=1080",
                "small": "https://images.unsplash.com/photo-2?w=400",
            },
            "user": {"name": "Nathan Dumlao", "username": "nate_dumlao"},
            "links": {
                "download_location": "https://api.unsplash.com/photos/K9nxgkYf-eQ/download?ixid=def"
            },
        },
    ],
}


@pytest.fixture(autouse=True)
def unsplash_settings(monkeypatch):
    monkeypatch.setattr(settings, "unsplash_access_key", "unsplash-test-key")


def make_client(handler):
    return UnsplashClient(transport=httpx.MockTransport(handler))


async def test_search_photos():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("authorization")
        seen["path"] = request.url.path
        seen["params"] = dict(request.url.params)
        return httpx.Response(200, json=SEARCH_PAYLOAD)

    result = await make_client(handler).search_photos(
        "coffee grinder", page=2, per_page=50, orientation="landscape"
    )
    assert seen["auth"] == "Client-ID unsplash-test-key"
    assert seen["path"] == "/search/photos"
    assert seen["params"] == {
        "query": "coffee grinder",
        "page": "2",
        "per_page": "30",
        "content_filter": "high",
        "orientation": "landscape",
    }
    assert result.total == 133
    assert result.total_pages == 6
    assert len(result.photos) == 2

    first = result.photos[0]
    assert first.id == "eOLpJytrbsQ"
    assert first.thumb_url == "https://images.unsplash.com/photo-1?w=400"
    assert first.url == "https://images.unsplash.com/photo-1?w=1080"
    assert first.alt == "A pour-over brewer on a wooden counter"
    assert first.width == 5245
    assert first.height == 3497
    assert first.color == "#60544D"
    assert first.credit_name == "Jeff Sheldon"
    assert first.credit_url == "https://unsplash.com/@ugmonk?utm_source=meelu&utm_medium=referral"
    assert (
        first.download_location == "https://api.unsplash.com/photos/eOLpJytrbsQ/download?ixid=abc"
    )

    second = result.photos[1]
    assert second.alt == "Steam rising from a ceramic mug"
    assert second.color == "#e6e1d1"


async def test_search_defaults():
    seen = {}

    def handler(request):
        seen["params"] = dict(request.url.params)
        return httpx.Response(200, json={"results": [], "total": 0, "total_pages": 0})

    result = await make_client(handler).search_photos("espresso")
    assert seen["params"] == {
        "query": "espresso",
        "page": "1",
        "per_page": "24",
        "content_filter": "high",
    }
    assert result.photos == []
    assert result.total == 0


async def test_trigger_download():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        return httpx.Response(200, json={"url": "https://images.unsplash.com/photo-1"})

    await make_client(handler).trigger_download(
        "https://api.unsplash.com/photos/eOLpJytrbsQ/download?ixid=abc"
    )
    assert seen["url"] == "https://api.unsplash.com/photos/eOLpJytrbsQ/download?ixid=abc"
    assert seen["auth"] == "Client-ID unsplash-test-key"


async def test_trigger_download_rejects_foreign_location():
    def handler(request):
        raise AssertionError("request should not be sent")

    with pytest.raises(IntegrationError) as err:
        await make_client(handler).trigger_download("https://evil.example.com/photos/x/download")
    assert err.value.status == 400


async def test_trigger_download_swallows_request_failure():
    def handler(request):
        return httpx.Response(404, json={"errors": ["Couldn't find Photo"]})

    await make_client(handler).trigger_download("https://api.unsplash.com/photos/gone/download")


async def test_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "unsplash_access_key", "")

    def handler(request):
        raise AssertionError("request should not be sent")

    client = make_client(handler)
    assert client.configured is False
    with pytest.raises(IntegrationError) as err:
        await client.search_photos("coffee")
    assert err.value.status == 501


async def test_4xx_maps_to_integration_error():
    def handler(request):
        return httpx.Response(
            403, text="Rate Limit Exceeded", headers={"x-ratelimit-remaining": "0"}
        )

    with pytest.raises(IntegrationError) as err:
        await make_client(handler).search_photos("coffee")
    assert err.value.status == 403
    assert not isinstance(err.value, TransientIntegrationError)
    assert err.value.body == "Rate Limit Exceeded"


async def test_5xx_retries_then_succeeds():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(503, text="upstream unavailable")
        return httpx.Response(200, json={"results": [], "total": 0, "total_pages": 0})

    result = await make_client(handler).search_photos("coffee")
    assert calls["n"] == 2
    assert result.total == 0
