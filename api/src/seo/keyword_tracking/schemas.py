from datetime import date

from pydantic import BaseModel, Field, field_validator

from src.core.schemas import EntityModel
from src.seo.keyword_tracking.constants import MAX_TRACK_KEYWORDS


def normalize_keyword(raw: str) -> str:
    return " ".join(str(raw or "").lower().split())


class TrackKeywordsRequest(BaseModel):
    keywords: list[str] = Field(min_length=1)

    @field_validator("keywords")
    @classmethod
    def _keywords(cls, value: list[str]) -> list[str]:
        cleaned = [k for k in dict.fromkeys(normalize_keyword(v) for v in value) if k]
        if not cleaned:
            raise ValueError("Pass at least one keyword.")
        if len(cleaned) > MAX_TRACK_KEYWORDS:
            raise ValueError(f"At most {MAX_TRACK_KEYWORDS} keywords per call.")
        return cleaned


class VolumeRow(BaseModel):
    keyword: str
    location_code: int
    language_code: str
    month: date
    search_volume: int | None = None
    clickstream_volume: int | None = None
    cpc: float | None = None
    competition: float | None = None


class VolumesTracked(EntityModel):
    keywords: int
    months: int
    rows: int
    without_data: list[str]


class TrackedKeyword(EntityModel):
    keyword: str
    position: float | None = None
    previous_position: float | None = None
    change: float | None = None
    url: str | None = None
    history: list[float | None]
    volume: int | None = None
    demand: str | None = None


class TrackedStats(EntityModel):
    tracked: int
    top_ten: int
    moved: int
    not_ranking: int


class Market(EntityModel):
    location_code: int
    language_code: str
    country: str | None = None


class TrackedOverview(EntityModel):
    location_code: int
    language_code: str
    markets: list[Market]
    months: list[date]
    stats: TrackedStats
    keywords: list[TrackedKeyword]
