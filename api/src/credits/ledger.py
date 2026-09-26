from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.credits.repository import credit_accounts, credit_ledger_entries
from src.credits.schemas import LedgerEntryResponse


class CreditLedgerService:
    async def apply(
        self,
        db: AsyncSession,
        user_id: str,
        delta_micros: int,
        kind: str,
        note: str | None = None,
        provider_call_id: str | None = None,
    ) -> LedgerEntryResponse:
        after = await credit_accounts.add(db, user_id, delta_micros)
        return await credit_ledger_entries.create(
            db, user_id, kind, delta_micros, after, note, provider_call_id
        )

    async def list(
        self, db: AsyncSession, user_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[LedgerEntryResponse]:
        return await credit_ledger_entries.list(db, user_id, paging)


credit_ledger_service = CreditLedgerService()
