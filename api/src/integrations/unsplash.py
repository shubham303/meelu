from typing import Any

import httpx
from pydantic import BaseModel, model_validator

from src.integrations.base import HttpIntegration, IntegrationError
from src.settings import settings

API_URL = "https://api.unsplash.com"
UTM = "utm_source=meelu&utm_medium=referral"

NOT_CONFIGURED_MESSAGE = (
    "Unsplash search isn't configured. Set UNSPLASH_ACCESS_KEY on the dashboard "
    "(get a key at https://unsplash.com/oauth/applications), or upload an image instead."
)


class UnsplashPhoto(BaseModel):
    id: str
    thumb_url: str
    url: str
    alt: str
    width: int
    height: int
    color: str
    credit_name: str
    credit_url: str
    download_location: str

    @model_validator(mode="before")
    @classmethod
    def _from_api(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "urls" not in data:
            return data
        return {
            "id": data["id"],
            "thumb_url": data["urls"]["small"],
            "url": data["urls"]["regular"],
            "alt": data.get("alt_description") or data.get("description") or "",
            "width": data["width"],
            "height": data["height"],
            "color": data.get("color") or "#e6e1d1",
            "credit_name": data["user"]["name"],
            "credit_url": f"https://unsplash.com/@{data['user']['username']}?{UTM}",
            "download_location": data["links"]["download_location"],
        }


class UnsplashSearchResult(BaseModel):
    photos: list[UnsplashPhoto] = []
    total: int = 0
    total_pages: int = 0

    @model_validator(mode="before")
    @classmethod
    def _from_api(cls, data: Any) -> Any:
        if not isinstance(data, dict) or "results" not in data:
            return data
        return {
            "photos": data.get("results") or [],
            "total": data.get("total") or 0,
            "total_pages": data.get("total_pages") or 0,
        }


class UnsplashClient(HttpIntegration):
    name = "unsplash"
    base_url = API_URL

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        super().__init__()
        self._transport = transport

    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                transport=self._transport,
            )
        return self._client

    @property
    def configured(self) -> bool:
        return bool(settings.unsplash_access_key)

    def auth_headers(self) -> dict[str, str]:
        if not settings.unsplash_access_key:
            raise IntegrationError(501, NOT_CONFIGURED_MESSAGE)
        return {"Authorization": f"Client-ID {settings.unsplash_access_key}"}

    async def search_photos(
        self,
        query: str,
        *,
        page: int = 1,
        per_page: int = 24,
        orientation: str | None = None,
    ) -> UnsplashSearchResult:
        params = {
            "query": query,
            "page": str(page),
            "per_page": str(min(per_page, 30)),
            "content_filter": "high",
        }
        if orientation:
            params["orientation"] = orientation
        raw = await self.request("GET", "/search/photos", params=params)
        return UnsplashSearchResult.model_validate(raw)

    async def trigger_download(self, download_location: str) -> None:
        if not download_location.startswith(f"{API_URL}/photos/"):
            raise IntegrationError(400, "That is not an Unsplash download location.")
        try:
            await self.request("GET", download_location)
        except IntegrationError as e:
            self._log.warning("download_trigger_failed", location=download_location, error=str(e))


unsplash = UnsplashClient()
