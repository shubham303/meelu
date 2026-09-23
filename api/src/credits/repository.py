from datetime import UTC, datetime

from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.credits.models.credit_account import CreditAccount
from src.credits.models.credit_ledger import CreditLedgerEntry
from src.credits.models.site_billing import SiteBilling
from src.credits.schemas import DueSite, LedgerEntryResponse
from src.sites.models.site import Site


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


async def ensure_site_billing(db: AsyncSession, user_id: str, site_id: str, domain: str) -> None:
    now = datetime.now(UTC)
    await db.execute(
        insert(SiteBilling)
        .values(user_id=user_id, domain=domain, site_id=site_id)
        .on_conflict_do_update(
            index_elements=["user_id", "domain"],
            set_={"site_id": site_id, "updated_at": now},
        )
    )


async def due_sites(db: AsyncSession, cutoff: datetime, limit: int) -> list[DueSite]:
    result = await db.execute(
        select(SiteBilling.site_id, SiteBilling.user_id, SiteBilling.domain, Site.status)
        .join(Site, Site.id == SiteBilling.site_id)
        .where(
            or_(
                SiteBilling.last_charged_at.is_(None),
                SiteBilling.last_charged_at <= cutoff,
            )
        )
        .order_by(SiteBilling.last_charged_at.asc().nulls_first())
        .limit(limit)
    )
    return [
        DueSite(site_id=r.site_id, user_id=r.user_id, status=r.status, domain=r.domain)
        for r in result
    ]


async def lock_due_billing(db: AsyncSession, user_id: str, domain: str, cutoff: datetime) -> bool:
    result = await db.execute(
        select(SiteBilling.domain)
        .where(
            SiteBilling.user_id == user_id,
            SiteBilling.domain == domain,
            or_(
                SiteBilling.last_charged_at.is_(None),
                SiteBilling.last_charged_at <= cutoff,
            ),
        )
        .with_for_update(skip_locked=True)
    )
    return result.scalars().first() is not None


async def mark_charged(db: AsyncSession, user_id: str, domain: str, charged_micros: int) -> None:
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


async def set_site_status(db: AsyncSession, site_id: str, status: str) -> None:
    await db.execute(
        update(Site)
        .where(Site.id == site_id, Site.status != status)
        .values(status=status, updated_at=datetime.now(UTC))
    )


async def disable_sites_of(db: AsyncSession, user_id: str) -> int:
    result = await db.execute(
        update(Site)
        .where(Site.user_id == user_id, Site.status != "disabled")
        .values(status="disabled", updated_at=datetime.now(UTC))
    )
    return result.rowcount or 0


async def site_billing(db: AsyncSession, user_id: str, domain: str) -> SiteBilling | None:
    result = await db.execute(
        select(SiteBilling)
        .where(SiteBilling.user_id == user_id, SiteBilling.domain == domain)
        .limit(1)
    )
    return result.scalars().first()
