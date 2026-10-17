from datetime import date

from pydantic import Field, field_validator

from src.core.schemas import EntityModel, RequestModel
from src.seo.keyword_tracking.schemas import normalize_keyword


class SerpHistoryRequest(RequestModel):
    keyword: str = Field(min_length=1)
    location_code: int | None = None

    @field_validator("keyword")
    @classmethod
    def _keyword(cls, value: str) -> str:
        cleaned = normalize_keyword(value)
        if not cleaned:
            raise ValueError("Pass a keyword.")
        return cleaned


class DomainPresence(EntityModel):
    domain: str
    appearances: int
    presence: float
    best_position: int
    average_position: float
    latest_position: int | None = None
    top_url: str
    saved: bool = False


class SerpHistory(EntityModel):
    keyword: str
    location_code: int
    language_code: str
    snapshots: int
    first_day: date | None = None
    last_day: date | None = None
    top_positions: int
    consistent_share: float
    competitors: list[DomainPresence]
    sporadic: int
    ours: DomainPresence | None = None
