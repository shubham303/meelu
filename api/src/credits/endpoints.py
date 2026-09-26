from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import current_user_id, require_superuser
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.credits.billing import site_billing_service
from src.credits.service import credit_service
from src.credits.schemas import (
    BalanceResponse,
    GrantRequest,
    LedgerEntryResponse,
    SiteBillingResponse,
    SweepResult,
)

router = APIRouter()


@router.get("/credits")
async def get_balance(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
) -> BalanceResponse:
    return await credit_service.balance(db, user_id)


@router.get("/credits/ledger")
async def list_ledger(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[LedgerEntryResponse]:
    return await credit_service.ledger(db, user_id, paging)


@router.post("/credits/grant")
async def grant_credits(
    body: GrantRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_superuser),
) -> BalanceResponse:
    return await credit_service.grant(db, user_id, body)


@router.get("/credits/sites/{site_id}")
async def get_site_billing(
    site_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
) -> SiteBillingResponse:
    return await credit_service.site_billing_state(db, user_id, site_id)


@router.post("/credits/sweep")
async def run_sweep(
    user_id: str = Depends(require_superuser),
) -> SweepResult:
    return await site_billing_service.sweep()
