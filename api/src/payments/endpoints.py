from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import current_user_id
from src.core.database import get_db
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.pagination.utils import get_pagination_params
from src.payments.schemas import (
    CheckoutRequest,
    CheckoutResponse,
    PaymentResponse,
    WebhookResponse,
)
from src.payments.service import payment_service

router = APIRouter()


@router.post("/payments/checkout", status_code=201)
async def create_checkout(
    body: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
) -> CheckoutResponse:
    return await payment_service.create_checkout(db, user_id, body)


@router.get("/payments")
async def list_payments(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
    paging: PaginationParams = Depends(get_pagination_params),
) -> PaginatedApiResponse[PaymentResponse]:
    return await payment_service.list(db, user_id, paging)


@router.get("/payments/{payment_id}")
async def get_payment(
    payment_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(current_user_id),
) -> PaymentResponse:
    return await payment_service.get(db, user_id, payment_id)


@router.post("/payments/webhooks/dodo")
async def dodo_webhook(request: Request, db: AsyncSession = Depends(get_db)) -> WebhookResponse:
    await payment_service.handle_webhook(
        db, await request.body(), {k.lower(): v for k, v in request.headers.items()}
    )
    return WebhookResponse()
