from typing import Any

from pydantic import field_validator

from src.core.schemas import RequestModel


class PageEditsRequest(RequestModel):
    job_id: str
    evidence: str = "all"
    page_ids: list[str] | None = None
    keyword_ids: list[str] | None = None
    min_position: float = 4
    max_position: float = 20
    min_impressions: int = 100
    min_questions: int = 3
    min_drop: float = 0.3

    @field_validator("evidence", mode="before")
    @classmethod
    def _evidence(cls, value: Any) -> str:
        chosen = str(value or "all")
        allowed = ("all", "gsc", "cluster", "ctr", "questions", "decay")
        if chosen not in allowed:
            raise ValueError(f'Invalid evidence "{chosen}". Allowed values: {", ".join(allowed)}.')
        return chosen


class CannibalisationRequest(RequestModel):
    job_id: str
    page_ids: list[str] | None = None
    min_shared_impressions: int = 50
