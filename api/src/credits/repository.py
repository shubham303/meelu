from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.credits.models.credit_account import CreditAccount
from src.credits.models.credit_ledger import CreditLedgerEntry
from src.credits.schemas import LedgerEntryResponse


async def ensure_account(db: AsyncSession, user_id: str) -> None:
    await db.execute(
        insert(CreditAccount)
        .values(user_id=user_id)
        .on_conflict_do_nothing(index_elements=["user_id"])
    )


async def balance(db: AsyncSession, user_id: str) -> int:
    await ensure_account(db, user_id)
    row = await db.execute(
        select(CreditAccount.balance_micros).where(CreditAccount.user_id == user_id)
    )
    return row.scalar_one()


async def apply_delta(
    db: AsyncSession,
    user_id: str,
    delta_micros: int,
    kind: str,
    note: str | None = None,
    provider_call_id: str | None = None,
) -> CreditLedgerEntry:
    await ensure_account(db, user_id)
    now = datetime.now(UTC)
    result = await db.execute(
        update(CreditAccount)
        .where(CreditAccount.user_id == user_id)
        .values(balance_micros=CreditAccount.balance_micros + delta_micros, updated_at=now)
        .returning(CreditAccount.balance_micros)
    )
    after = result.scalar_one()
    entry = CreditLedgerEntry(
        id=uid("cred"),
        user_id=user_id,
        kind=kind,
        delta_micros=delta_micros,
        balance_after_micros=after,
        provider_call_id=provider_call_id,
        note=note,
        created_at=now,
        updated_at=now,
    )
    db.add(entry)
    await db.flush()
    return entry


async def list_ledger(
    db: AsyncSession, user_id: str, paging: PaginationParams
) -> PaginatedApiResponse[LedgerEntryResponse]:
    query = (
        select(CreditLedgerEntry)
        .where(CreditLedgerEntry.user_id == user_id)
        .order_by(CreditLedgerEntry.seq.desc())
    )
    return await PaginationService.paginate_query(
        db, query, paging.page, paging.page_size, LedgerEntryResponse
    )
