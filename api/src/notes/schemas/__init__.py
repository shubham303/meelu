from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel

NOTE_KINDS = ("note", "feedback")
NOTE_SORTS = ("created", "updated")
SEARCH_MODES = ("auto", "keyword", "semantic")
MAX_NOTE_CHARS = 4000

NoteKind = Literal["note", "feedback"]
NoteSort = Literal["created", "updated"]
SearchMode = Literal["auto", "keyword", "semantic"]


def _kind(value: Any) -> str:
    kind = str(value)
    if kind not in NOTE_KINDS:
        raise ValueError(f'Invalid kind "{kind}". Allowed values: {", ".join(NOTE_KINDS)}.')
    return kind


def _note_text(value: Any) -> str:
    note = ("" if value is None else str(value)).strip()
    if not note:
        raise ValueError("A note needs some text.")
    if len(note) > MAX_NOTE_CHARS:
        raise ValueError(
            f"That note is {len(note)} characters — keep it under {MAX_NOTE_CHARS}. "
            "A note is a standing rule or a correction, not a document."
        )
    return note


class NoteCreateRequest(RequestModel):
    note: str
    kind: str = "note"

    @field_validator("note", mode="before")
    @classmethod
    def _validate_note(cls, v: Any) -> str:
        return _note_text(v)

    @field_validator("kind", mode="before")
    @classmethod
    def _validate_kind(cls, v: Any) -> str:
        return "note" if v is None else _kind(v)


class NoteUpdateRequest(RequestModel):
    note: str | None = None
    kind: str | None = None

    @field_validator("note", mode="before")
    @classmethod
    def _validate_note(cls, v: Any) -> str | None:
        return None if v is None else _note_text(v)

    @field_validator("kind", mode="before")
    @classmethod
    def _validate_kind(cls, v: Any) -> str | None:
        return None if v is None else _kind(v)

    def changes(self) -> dict[str, str]:
        return self.model_dump(exclude_none=True)


class NoteListFilters(RequestModel):
    kinds: list[str] | None = None
    contains: str | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    sort: NoteSort | None = None

    @field_validator("kinds", mode="before")
    @classmethod
    def _validate_kinds(cls, v: Any) -> list[str] | None:
        if not v:
            return None
        return [_kind(k) for k in v]


class NoteRecord(EntityModel):
    id: str
    site_id: str
    note: str
    kind: str
    created_at: JsDateTime
    updated_at: JsDateTime


class NoteHitRecord(EntityModel):
    keep_null = frozenset({"similarity"})

    id: str
    site_id: str
    note: str
    kind: str
    created_at: JsDateTime
    updated_at: JsDateTime
    score: float
    similarity: float | None = None


class NoteEmbedCoverage(EntityModel):
    done: int
    total: int


class NoteSearchResult(EntityModel):
    hits: list[NoteHitRecord]
    mode: str
    embedded: NoteEmbedCoverage
    note: str | None = None


class NoteResponse(EntityModel):
    id: str
    site_id: str
    note: str
    kind: str
    created_at: JsDateTime
    updated_at: JsDateTime


class NoteListItemResponse(EntityModel):
    id: str
    site_id: str
    note: str
    kind: str
    created_at: JsDateTime
    updated_at: JsDateTime


class NoteDeleteResponse(EntityModel):
    id: str
    deleted: bool = Field(default=True)


class NoteHitResponse(EntityModel):
    keep_null = frozenset({"similarity"})

    id: str
    site_id: str
    note: str
    kind: str
    created_at: JsDateTime
    updated_at: JsDateTime
    score: float
    similarity: float | None = None


class NoteSearchResponse(EntityModel):
    hits: list[NoteHitResponse]
    mode: str
    embedded: NoteEmbedCoverage
    note: str | None = None
