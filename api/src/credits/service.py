from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.credits import billing, pricing
from src.credits import repository as repo
from src.credits.schemas import (
    BalanceResponse,
    GrantRequest,
    LedgerEntryResponse,
    SiteBillingResponse,
)
from src.settings import settings

log = get_logger("credits")


class InsufficientCreditsError(Exception):
    code = "insufficient_credits"

    def __init__(self, balance_micros: int, floor_micros: int):
        super().__init__(
            f"This workspace is below the ${floor_micros / 1_000_000:.2f} minimum needed to call "
            f"a paid vendor (balance ${balance_micros / 1_000_000:.4f}). Add credits to continue."
        )
        self.balance_micros = balance_micros
        self.floor_micros = floor_micros


class SiteDisabledError(Exception):
    code = "site_disabled"

    def __init__(self, site_id: str):
        super().__init__(
            "This website is disabled because the workspace ran out of credits. "
            "Add credits and it turns back on within 15 minutes."
        )
        self.site_id = site_id


def to_micros(usd: float) -> int:
    return round(usd * 1_000_000)


async def balance(db: AsyncSession, user_id: str) -> BalanceResponse:
    micros = await repo.balance(db, user_id)
    return BalanceResponse(balance_micros=micros, balance_usd=micros / 1_000_000)


async def require_balance(db: AsyncSession, user_id: str) -> int:
    micros = await repo.balance(db, user_id)
    floor = pricing.minimum_balance_micros()
    if micros < floor:
        raise InsufficientCreditsError(micros, floor)
    return micros


def require_active_site(site_id: str, status: str) -> None:
    if status != billing.ACTIVE:
        raise SiteDisabledError(site_id)


async def site_billing_state(
    db: AsyncSession, user_id: str, site_id: str, domain: str, status: str
) -> SiteBillingResponse:
    row = await repo.site_billing(db, user_id, domain)
    last = row.last_charged_at if row else None
    return SiteBillingResponse(
        site_id=site_id,
        status=status,
        last_charged_at=last,
        next_charge_at=None if last is None else last + billing.period(),
        charge_count=row.charge_count if row else 0,
        charged_micros=row.charged_micros if row else 0,
        daily_price_micros=pricing.site_day_price_micros(),
    )


async def start_site_billing(db: AsyncSession, user_id: str, site_id: str, domain: str) -> bool:
    return await billing.start_site(db, user_id, site_id, domain)


async def grant(db: AsyncSession, user_id: str, body: GrantRequest) -> BalanceResponse:
    entry = await repo.apply_delta(db, user_id, to_micros(body.amount_usd), "grant", body.note)
    return BalanceResponse(
        balance_micros=entry.balance_after_micros,
        balance_usd=entry.balance_after_micros / 1_000_000,
    )


async def signup_grant(db: AsyncSession, user_id: str) -> None:
    micros = to_micros(settings.credits_signup_grant_usd)
    if micros > 0:
        await repo.apply_delta(db, user_id, micros, "grant", "Signup credits")
    else:
        await repo.ensure_account(db, user_id)


async def charge_vendor_call(
    db: AsyncSession,
    user_id: str,
    domain: str,
    capability: str,
    vendor_cost_micros: int,
    provider_call_id: str,
) -> int:
    price = pricing.vendor_call_price(domain, capability, vendor_cost_micros)
    if price <= 0:
        return 0
    entry = await repo.apply_delta(
        db, user_id, -price, "usage", f"{domain}/{capability}", provider_call_id
    )
    if entry.balance_after_micros < 0:
        disabled = await repo.disable_sites_of(db, user_id)
        log.warning(
            "credits_overdrawn",
            user_id=user_id,
            balance_micros=entry.balance_after_micros,
            sites_disabled=disabled,
        )
    return price


async def ledger(
    db: AsyncSession, user_id: str, paging: PaginationParams
) -> PaginatedApiResponse[LedgerEntryResponse]:
    return await repo.list_ledger(db, user_id, paging)
