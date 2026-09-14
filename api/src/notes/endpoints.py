from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.notes import service
from src.notes.schemas import (
    NoteCreateRequest,
    NoteDeleteResponse,
    NoteKind,
    NoteListFilters,
    NoteListItemResponse,
    NoteResponse,
    NoteSearchResponse,
    NoteSort,
    NoteUpdateRequest,
    SearchMode,
)

router = APIRouter()


@router.get("/notes")
async def list_notes(
    q: str | None = Query(None),
    mode: SearchMode | None = Query(None),
    limit: int | None = Query(None, ge=1),
    kind: list[NoteKind] | None = Query(None),
    contains: str | None = Query(None),
    created_after: datetime | None = Query(None, alias="createdAfter"),
    created_before: datetime | None = Query(None, alias="createdBefore"),
    sort: NoteSort | None = Query(None),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[NoteListItemResponse] | NoteSearchResponse:
    if q:
        result = await service.search(
            db,
            ctx.site_id,
            q,
            mode=mode,
            kind=kind[0] if kind and len(kind) == 1 else None,
            limit=limit,
        )
        return NoteSearchResponse.model_validate(result, from_attributes=True)

    filters = NoteListFilters(
        kinds=kind,
        contains=contains,
        created_after=created_after,
        created_before=created_before,
        sort=sort,
    )
    page = await service.list_notes(db, ctx.site_id, filters, paging)
    return PaginatedApiResponse[NoteListItemResponse](
        data=[NoteListItemResponse.model_validate(n) for n in page.data],
        pagination=page.pagination,
    )


@router.post("/notes", status_code=201)
async def create_note(
    body: NoteCreateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> NoteResponse:
    record = await service.create_note(db, ctx.user_id, ctx.site_id, body)
    return NoteResponse.model_validate(record)


@router.get("/notes/{note_id}")
async def get_note(
    note_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> NoteResponse:
    return NoteResponse.model_validate(await service.get_note(db, ctx.site_id, note_id))


@router.put("/notes/{note_id}")
async def put_note(
    note_id: str,
    body: NoteUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> NoteResponse:
    record = await service.update_note(db, ctx.site_id, note_id, body)
    return NoteResponse.model_validate(record)


@router.patch("/notes/{note_id}")
async def patch_note(
    note_id: str,
    body: NoteUpdateRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> NoteResponse:
    record = await service.update_note(db, ctx.site_id, note_id, body)
    return NoteResponse.model_validate(record)


@router.delete("/notes/{note_id}")
async def delete_note(
    note_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> NoteDeleteResponse:
    record = await service.delete_note(db, ctx.site_id, note_id)
    return NoteDeleteResponse(id=record.id)
