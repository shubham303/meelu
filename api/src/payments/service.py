import json
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.credits.ledger import credit_ledger_service
from src.payments import dodo
from src.payments.repository import payments
from src.payments.schemas import (
    CheckoutRequest,
    CheckoutResponse,
    PaymentRecord,
    PaymentResponse,
)
from src.profile.repository import users
from src.settings import settings

log = get_logger("payments")

PENDING = "pending"
SUCCEEDED = "succeeded"
FAILED = "failed"
CANCELLED = "cancelled"

UNSETTLED = (PENDING, FAILED, CANCELLED)
SETTLEMENT_CURRENCY = "USD"
MICROS_PER_CENT = 10_000
FAILURE_EVENTS = {"payment.failed": FAILED, "payment.cancelled": CANCELLED}


class PaymentService:
    async def create_checkout(
        self, db: AsyncSession, user_id: str, body: CheckoutRequest
    ) -> CheckoutResponse:
        if not dodo.is_configured():
            raise HTTPException(503, "Payments are not configured on this server.")
        low, high = settings.payments_min_topup_usd, settings.payments_max_topup_usd
        if not low <= body.amount_usd <= high:
            raise HTTPException(400, f"Top-ups must be between ${low:.2f} and ${high:.2f}.")

        user = await users.get(db, user_id)
        if user is None:
            raise HTTPException(404, "Not found")

        amount_cents = round(body.amount_usd * 100)
        payment = await payments.create(db, user_id, amount_cents * MICROS_PER_CENT, PENDING)
        try:
            checkout = await dodo.create_checkout(
                amount_cents,
                user.email,
                user.name or "",
                {"meelu_payment_id": payment.id, "meelu_user_id": user_id},
            )
        except dodo.DodoError as e:
            log.error("dodo_checkout_failed", user_id=user_id, error=str(e))
            raise HTTPException(502, str(e)) from e

        await payments.update(
            db,
            payment.id,
            {"checkout_session_id": checkout.session_id, "checkout_url": checkout.checkout_url},
        )
        return CheckoutResponse(payment_id=payment.id, checkout_url=checkout.checkout_url)

    async def get(self, db: AsyncSession, user_id: str, payment_id: str) -> PaymentResponse:
        record = await payments.get(db, user_id, payment_id)
        if record is None:
            raise HTTPException(404, "Not found")
        return PaymentResponse.model_validate(record)

    async def list(
        self, db: AsyncSession, user_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[PaymentResponse]:
        page = await payments.list(db, user_id, paging)
        return PaginatedApiResponse[PaymentResponse](
            data=[PaymentResponse.model_validate(p) for p in page.data],
            pagination=page.pagination,
        )

    async def handle_webhook(
        self, db: AsyncSession, raw_body: bytes, headers: dict[str, str]
    ) -> None:
        try:
            dodo.verify_webhook(raw_body, headers)
        except dodo.DodoSignatureError as e:
            log.warning("dodo_webhook_rejected", error=str(e))
            raise HTTPException(401, "Invalid webhook signature.") from e

        event = json.loads(raw_body)
        kind = event.get("type", "")
        data = event.get("data") or {}
        if kind != "payment.succeeded" and kind not in FAILURE_EVENTS:
            return

        payment = await self._match(db, data)
        if payment is None:
            log.warning("dodo_webhook_unmatched", type=kind, payment_id=data.get("payment_id"))
            return

        settled = {
            "dodo_payment_id": data.get("payment_id"),
            "paid_amount": data.get("total_amount"),
            "paid_currency": data.get("currency"),
        }
        if kind == "payment.succeeded":
            if not self._paid_in_full(payment, settled):
                log.error(
                    "dodo_webhook_amount_mismatch",
                    payment_id=payment.id,
                    expected_cents=payment.credit_micros // MICROS_PER_CENT,
                    paid_amount=settled["paid_amount"],
                    paid_currency=settled["paid_currency"],
                )
                return
            await self._credit(db, payment, settled)
        else:
            await payments.transition(
                db, payment.id, (PENDING, FAILED), {**settled, "status": FAILURE_EVENTS[kind]}
            )

    def _paid_in_full(self, payment: PaymentRecord, settled: dict[str, Any]) -> bool:
        amount = settled["paid_amount"]
        return (
            settled["paid_currency"] == SETTLEMENT_CURRENCY
            and isinstance(amount, int)
            and not isinstance(amount, bool)
            and amount >= payment.credit_micros // MICROS_PER_CENT
        )

    async def _match(self, db: AsyncSession, data: dict[str, Any]) -> PaymentRecord | None:
        payment_id = (data.get("metadata") or {}).get("meelu_payment_id")
        if payment_id:
            return await payments.find(db, payment_id)
        session_id = data.get("checkout_session_id")
        if session_id:
            return await payments.find_by_checkout_session(db, session_id)
        return None

    async def _credit(
        self, db: AsyncSession, payment: PaymentRecord, settled: dict[str, Any]
    ) -> None:
        now = datetime.now(UTC)
        updated = await payments.transition(
            db, payment.id, UNSETTLED, {**settled, "status": SUCCEEDED, "credited_at": now}
        )
        if updated is None:
            return
        await credit_ledger_service.apply(
            db,
            updated.user_id,
            updated.credit_micros,
            "purchase",
            f"Top-up ${updated.credit_micros / 1_000_000:.2f} · {updated.dodo_payment_id}",
        )
        log.info("credits_purchased", user_id=updated.user_id, payment_id=updated.id)


payment_service = PaymentService()
