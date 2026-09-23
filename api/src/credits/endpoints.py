from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import current_user_id, require_superuser
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.credits import billing, service
from src.credits.schemas import (
    BalanceResponse,
    GrantRequest,
    LedgerEntryResponse,
    SiteBillingResponse,
    SweepResult,
)
from src.sites import repository as sites_repository

router = APIRouter()


@router.get("/credits")
async def get_balance(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
) -> BalanceResponse:
    return await service.balance(db, user_id)


@router.get("/credits/ledger")
async def list_ledger(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[LedgerEntryResponse]:
    return await service.ledger(db, user_id, paging)


@router.post("/credits/grant")
async def grant_credits(
    body: GrantRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(require_superuser),
) -> BalanceResponse:
    return await service.grant(db, user_id, body)


@router.get("/credits/sites/{site_id}")
async def get_site_billing(
    site_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
) -> SiteBillingResponse:
    site = await sites_repository.get_site(db, user_id, site_id)
    if site is None:
        raise HTTPException(404, "Not found")
    return await service.site_billing_state(db, user_id, site.id, site.domain, site.status)


@router.post("/credits/sweep")
async def run_sweep(
    user_id: str = Depends(require_superuser),
) -> SweepResult:
    return await billing.sweep()
