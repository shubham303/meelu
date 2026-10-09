from datetime import UTC, datetime

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.credits.models.credit_account import CreditAccount
from src.credits.models.credit_ledger import CreditLedgerEntry
from src.credits.models.site_billing import SiteBilling
from src.credits.schemas import LedgerEntryResponse, SiteBillingRecord


class CreditAccountRepository:
    async def lock_spend(self, db: AsyncSession, user_id: str) -> None:
        await db.execute(
            select(func.pg_advisory_xact_lock(func.hashtext(f"credit_spend:{user_id}")))
        )

    async def ensure(self, db: AsyncSession, user_id: str) -> None:
        await db.execute(
            insert(CreditAccount)
            .values(user_id=user_id)
            .on_conflict_do_nothing(index_elements=["user_id"])
        )

    async def balance(self, db: AsyncSession, user_id: str) -> int:
        await self.ensure(db, user_id)
        row = await db.execute(
            select(CreditAccount.balance_micros).where(CreditAccount.user_id == user_id)
        )
        return row.scalar_one()

    async def add(self, db: AsyncSession, user_id: str, delta_micros: int) -> int:
        await self.ensure(db, user_id)
        result = await db.execute(
            update(CreditAccount)
            .where(CreditAccount.user_id == user_id)
            .values(
                balance_micros=CreditAccount.balance_micros + delta_micros,
                updated_at=datetime.now(UTC),
            )
            .returning(CreditAccount.balance_micros)
        )
        return result.scalar_one()


class CreditLedgerEntryRepository:
    ID_PREFIX = "cred"

    async def create(
        self,
        db: AsyncSession,
        user_id: str,
        kind: str,
        delta_micros: int,
        balance_after_micros: int,
        note: str | None = None,
        provider_call_id: str | None = None,
    ) -> LedgerEntryResponse:
        now = datetime.now(UTC)
        entry = CreditLedgerEntry(
            id=uid(self.ID_PREFIX),
            user_id=user_id,
            kind=kind,
            delta_micros=delta_micros,
            balance_after_micros=balance_after_micros,
            provider_call_id=provider_call_id,
            note=note,
            created_at=now,
            updated_at=now,
        )
        db.add(entry)
        await db.flush()
        return LedgerEntryResponse.model_validate(entry)

    async def list(
        self, db: AsyncSession, user_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[LedgerEntryResponse]:
        query = (
            select(CreditLedgerEntry)
            .where(CreditLedgerEntry.user_id == user_id)
            .order_by(CreditLedgerEntry.seq.desc())
        )
        return await PaginationService.paginate_query(
            db, query, paging.page, paging.page_size, LedgerEntryResponse
        )


class SiteBillingRepository:
    async def ensure(self, db: AsyncSession, user_id: str, site_id: str, domain: str) -> None:
        now = datetime.now(UTC)
        await db.execute(
            insert(SiteBilling)
            .values(user_id=user_id, domain=domain, site_id=site_id)
            .on_conflict_do_update(
                index_elements=["user_id", "domain"],
                set_={"site_id": site_id, "updated_at": now},
            )
        )

    async def get(self, db: AsyncSession, user_id: str, domain: str) -> SiteBillingRecord | None:
        result = await db.execute(
            select(SiteBilling)
            .where(SiteBilling.user_id == user_id, SiteBilling.domain == domain)
            .limit(1)
        )
        row = result.scalars().first()
        return None if row is None else SiteBillingRecord.model_validate(row)

    async def list_due(
        self, db: AsyncSession, cutoff: datetime, limit: int
    ) -> list[SiteBillingRecord]:
        result = await db.execute(
            select(SiteBilling)
            .where(SiteBilling.site_id.is_not(None), self._due(cutoff))
            .order_by(SiteBilling.last_charged_at.asc().nulls_first())
            .limit(limit)
        )
        return [SiteBillingRecord.model_validate(r) for r in result.scalars()]

    async def lock_due(self, db: AsyncSession, user_id: str, domain: str, cutoff: datetime) -> bool:
        result = await db.execute(
            select(SiteBilling.domain)
            .where(
                SiteBilling.user_id == user_id,
                SiteBilling.domain == domain,
                self._due(cutoff),
            )
            .with_for_update(skip_locked=True)
        )
        return result.scalars().first() is not None

    async def mark_charged(
        self, db: AsyncSession, user_id: str, domain: str, charged_micros: int
    ) -> None:
        now = datetime.now(UTC)
        await db.execute(
            update(SiteBilling)
            .where(SiteBilling.user_id == user_id, SiteBilling.domain == domain)
            .values(
                last_charged_at=now,
                charge_count=SiteBilling.charge_count + 1,
                charged_micros=SiteBilling.charged_micros + charged_micros,
                updated_at=now,
            )
        )

    def _due(self, cutoff: datetime):
        return or_(SiteBilling.last_charged_at.is_(None), SiteBilling.last_charged_at <= cutoff)


credit_accounts = CreditAccountRepository()
credit_ledger_entries = CreditLedgerEntryRepository()
site_billings = SiteBillingRepository()
