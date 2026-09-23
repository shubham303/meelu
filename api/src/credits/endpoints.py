from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import require
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.credits import service
from src.credits.schemas import BalanceResponse, GrantRequest, LedgerEntryResponse

router = APIRouter()


@router.get("/credits")
async def get_balance(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("credits", "read")),
) -> BalanceResponse:
    return await service.balance(db, user_id)


@router.get("/credits/ledger")
async def list_ledger(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("credits", "read")),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[LedgerEntryResponse]:
    return await service.ledger(db, user_id, paging)


@router.post("/credits/grant")
async def grant_credits(
    body: GrantRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require("credits", "write")),
) -> BalanceResponse:
    return await service.grant(db, user_id, body)
