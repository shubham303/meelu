from typing import Any

from pydantic import Field, field_validator

from src.core.schemas import EntityModel, RequestModel


class UnsplashPhotoResponse(EntityModel):
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


class UnsplashSearchResponse(EntityModel):
    configured: bool
    photos: list[UnsplashPhotoResponse] = Field(default_factory=list)
    total: int = 0
    total_pages: int = 0


class UnsplashDownloadRequest(RequestModel):
    download_location: str

    @field_validator("download_location", mode="before")
    @classmethod
    def _required(cls, v: Any) -> str:
        location = "" if v is None else str(v)
        if not location:
            raise ValueError("Missing downloadLocation.")
        return location


class UnsplashDownloadResponse(EntityModel):
    ok: bool = Field(default=True)
