import re
from typing import Any

from pydantic import Field

from src.core.schemas import EntityModel
from src.site_structure.constants import WORKSPACE_TABLE

MAX_PROMPT_CHARS = 20_000


def review_prompt(value: Any) -> str:
    text = str(value if value is not None else "").strip()
    if not text:
        raise ValueError("A review needs the prompt it runs.")
    return text[:MAX_PROMPT_CHARS]


def workspace_table(value: Any) -> str:
    name = str(value if value is not None else "").strip()
    if not re.match(WORKSPACE_TABLE, name):
        raise ValueError("Name a workspace table: lowercase letters, digits and underscores.")
    return name


class ScreenResult(EntityModel):
    screened: int = 0
    approved: int = 0
    rejected: int = 0
    failed: int = 0
    stopped: str | None = None


class ReviewItem(EntityModel):
    id: str
    state: dict[str, Any]


class ReviewBatch(EntityModel):
    instructions: str
    schema_: dict[str, Any] = Field(alias="schema")
    items: list[ReviewItem]


class ReviewResult(EntityModel):
    reviewed: int = 0
    approved: int = 0
    rejected: int = 0
    failed: int = 0


class RankResult(EntityModel):
    scored: int = 0
    kept: int = 0
    removed: int = 0
