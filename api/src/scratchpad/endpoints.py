from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import require
from src.core.database import get_db
from src.scratchpad.schemas import (
    ClaimRequest,
    ClaimResult,
    FailedRowsResult,
    NextRequest,
    NextResult,
    RowsAppended,
    ScratchpadAppendRequest,
    ScratchpadCreated,
    ScratchpadCreateRequest,
    ScratchpadDeleted,
    ScratchpadInfo,
    ScratchpadMetrics,
    SearchableStatus,
    SearchResult,
    StatusUpdateRequest,
    StatusUpdateResult,
)
from src.scratchpad.service import scratchpad_service

router = APIRouter(prefix="/scratchpads")


@router.post("", status_code=201)
async def create_scratchpad(
    body: ScratchpadCreateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("scratchpad", "write")),
) -> ScratchpadCreated:
    return await scratchpad_service.create_scratchpad(
        db, user_id, body.tool_name, body.items, body.priorities
    )


@router.get("/{scratchpad_id}")
async def get_scratchpad(
    scratchpad_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("scratchpad", "read")),
) -> ScratchpadInfo:
    return await scratchpad_service.get_scratchpad(db, user_id, scratchpad_id)


@router.delete("/{scratchpad_id}")
async def delete_scratchpad(
    scratchpad_id: str,
    force: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("scratchpad", "write")),
) -> ScratchpadDeleted:
    return await scratchpad_service.delete_scratchpad(db, user_id, scratchpad_id, force)


@router.post("/{scratchpad_id}/rows")
async def append_rows(
    scratchpad_id: str,
    body: ScratchpadAppendRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("scratchpad", "write")),
) -> RowsAppended:
    return await scratchpad_service.append_rows(
        db, user_id, scratchpad_id, body.items, body.priorities
    )


@router.get("/{scratchpad_id}/metrics")
async def get_metrics(
    scratchpad_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("scratchpad", "read")),
) -> ScratchpadMetrics:
    return await scratchpad_service.get_metrics(db, user_id, scratchpad_id)


@router.post("/{scratchpad_id}/next")
async def next_rows(
    scratchpad_id: str,
    body: NextRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("scratchpad", "write")),
) -> NextResult:
    return await scratchpad_service.next(db, user_id, scratchpad_id, body.n)


@router.post("/{scratchpad_id}/claim")
async def claim_rows(
    scratchpad_id: str,
    body: ClaimRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("scratchpad", "write")),
) -> ClaimResult:
    return await scratchpad_service.claim_rows(db, user_id, scratchpad_id, body.row_ids)


@router.post("/{scratchpad_id}/status")
async def update_status(
    scratchpad_id: str,
    body: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("scratchpad", "write")),
) -> StatusUpdateResult:
    return await scratchpad_service.update_status(db, user_id, scratchpad_id, body.updates)


@router.get("/{scratchpad_id}/failed")
async def get_failed(
    scratchpad_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("scratchpad", "read")),
) -> FailedRowsResult:
    return await scratchpad_service.get_failed(db, user_id, scratchpad_id, offset, limit)


@router.get("/{scratchpad_id}/search")
async def search(
    scratchpad_id: str,
    q: str = Query(...),
    status: SearchableStatus | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("scratchpad", "read")),
) -> SearchResult:
    return await scratchpad_service.search(db, user_id, scratchpad_id, q, status, offset, limit)
