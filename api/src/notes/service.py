from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.embed_worker.models import embed_model, embed_passage, embed_query
from src.notes import repository as repo
from src.notes.schemas import (
    SEARCH_MODES,
    NoteCreateRequest,
    NoteListFilters,
    NoteRecord,
    NoteSearchResult,
    NoteUpdateRequest,
)

DEFAULT_SEARCH_LIMIT = 10
MAX_SEARCH_LIMIT = 50


async def _embedded(note: str) -> tuple[list[float] | None, str | None]:
    vector = await embed_passage(note)
    if vector:
        return vector, embed_model()
    return None, None


async def list_notes(
    db: AsyncSession, site_id: str, filters: NoteListFilters, paging: PaginationParams
) -> PaginatedApiResponse[NoteRecord]:
    return await repo.list_notes(db, site_id, filters, paging)


async def get_note(db: AsyncSession, site_id: str, note_id: str) -> NoteRecord:
    record = await repo.get_note(db, site_id, note_id)
    if record is None:
        raise HTTPException(404, "Not found")
    return record


async def create_note(
    db: AsyncSession, user_id: str, site_id: str, body: NoteCreateRequest
) -> NoteRecord:
    embedding, embed_model = await _embedded(body.note)
    return await repo.create_note(
        db, user_id, site_id, body.note, body.kind, embedding, embed_model
    )


async def update_note(
    db: AsyncSession, site_id: str, note_id: str, body: NoteUpdateRequest
) -> NoteRecord:
    existing = await get_note(db, site_id, note_id)
    values: dict = body.changes()
    if not values:
        raise HTTPException(400, "Nothing to save.")
    if "note" in values and values["note"] != existing.note:
        values["embedding"], values["embed_model"] = await _embedded(values["note"])
    return await repo.update_note(db, existing.id, values)


async def delete_note(db: AsyncSession, site_id: str, note_id: str) -> NoteRecord:
    record = await get_note(db, site_id, note_id)
    await repo.delete_note(db, record.id)
    return record


async def search(
    db: AsyncSession,
    site_id: str,
    query: str,
    *,
    mode: str | None = None,
    kind: str | None = None,
    limit: int | None = None,
) -> NoteSearchResult:
    q = query.strip()
    if not q:
        raise HTTPException(400, "Pass something to search for.")

    requested = mode if mode in SEARCH_MODES else "auto"

    coverage = await repo.embed_coverage(db, site_id)
    vector = None if requested == "keyword" or coverage.done == 0 else await embed_query(q)
    if requested == "keyword" or not vector:
        ran = "keyword"
    elif requested == "semantic":
        ran = "semantic"
    else:
        ran = "hybrid"

    hits = await repo.search(
        db,
        site_id,
        q,
        vector,
        mode=requested,
        kind=kind,
        limit=min(limit if limit is not None else DEFAULT_SEARCH_LIMIT, MAX_SEARCH_LIMIT),
        model=embed_model(),
    )

    note: str | None = None
    if ran == "keyword" and requested != "keyword":
        note = (
            "Keyword search only — no notes are embedded for this website yet."
            if coverage.total == 0
            else "Keyword search only — semantic search is unavailable "
            f"({coverage.done} of {coverage.total} notes embedded)."
        )
    elif coverage.total > 0 and coverage.done < coverage.total:
        note = f"Semantic coverage is partial: {coverage.done} of {coverage.total} notes embedded."

    return NoteSearchResult(hits=hits, mode=ran, embedded=coverage, note=note)
