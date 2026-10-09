from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.payments.models.payment import Payment
from src.payments.schemas import PaymentRecord


class PaymentRepository:
    ID_PREFIX = "pay"

    async def create(
        self, db: AsyncSession, user_id: str, credit_micros: int, status: str
    ) -> PaymentRecord:
        now = datetime.now(UTC)
        row = Payment(
            id=uid(self.ID_PREFIX),
            user_id=user_id,
            status=status,
            credit_micros=credit_micros,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.flush()
        return PaymentRecord.model_validate(row)

    async def get(self, db: AsyncSession, user_id: str, payment_id: str) -> PaymentRecord | None:
        result = await db.execute(
            select(Payment).where(Payment.user_id == user_id, Payment.id == payment_id)
        )
        row = result.scalar_one_or_none()
        return None if row is None else PaymentRecord.model_validate(row)

    async def find(self, db: AsyncSession, payment_id: str) -> PaymentRecord | None:
        row = await db.get(Payment, payment_id)
        return None if row is None else PaymentRecord.model_validate(row)

    async def find_by_checkout_session(
        self, db: AsyncSession, session_id: str
    ) -> PaymentRecord | None:
        result = await db.execute(
            select(Payment).where(Payment.checkout_session_id == session_id).limit(1)
        )
        row = result.scalar_one_or_none()
        return None if row is None else PaymentRecord.model_validate(row)

    async def list(
        self, db: AsyncSession, user_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[PaymentRecord]:
        query = select(Payment).where(Payment.user_id == user_id).order_by(Payment.seq.desc())
        return await PaginationService.paginate_query(
            db, query, paging.page, paging.page_size, PaymentRecord
        )

    async def update(self, db: AsyncSession, payment_id: str, values: dict[str, Any]) -> None:
        await db.execute(
            update(Payment)
            .where(Payment.id == payment_id)
            .values(**values, updated_at=datetime.now(UTC))
        )

    async def transition(
        self,
        db: AsyncSession,
        payment_id: str,
        from_statuses: tuple[str, ...],
        values: dict[str, Any],
    ) -> PaymentRecord | None:
        result = await db.execute(
            update(Payment)
            .where(Payment.id == payment_id, Payment.status.in_(from_statuses))
            .values(**values, updated_at=datetime.now(UTC))
            .returning(Payment)
        )
        row = result.scalar_one_or_none()
        return None if row is None else PaymentRecord.model_validate(row)


payments = PaymentRepository()
