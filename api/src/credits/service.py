from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.credits import pricing
from src.credits import repository as repo
from src.credits.schemas import BalanceResponse, GrantRequest, LedgerEntryResponse
from src.settings import settings


class InsufficientCreditsError(Exception):
    code = "insufficient_credits"

    def __init__(self, balance_micros: int):
        super().__init__(
            "This workspace has no credits left "
            f"(balance ${balance_micros / 1_000_000:.4f}). Add credits to keep calling vendors."
        )
        self.balance_micros = balance_micros


def to_micros(usd: float) -> int:
    return round(usd * 1_000_000)


async def balance(db: AsyncSession, user_id: str) -> BalanceResponse:
    micros = await repo.balance(db, user_id)
    return BalanceResponse(balance_micros=micros, balance_usd=micros / 1_000_000)


async def require_balance(db: AsyncSession, user_id: str) -> int:
    micros = await repo.balance(db, user_id)
    if micros <= 0:
        raise InsufficientCreditsError(micros)
    return micros


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
    if price > 0:
        await repo.apply_delta(
            db, user_id, -price, "usage", f"{domain}/{capability}", provider_call_id
        )
    return price


async def charge_action(db: AsyncSession, user_id: str, action: str) -> int:
    price = pricing.action_price(action)
    if price > 0:
        await require_balance(db, user_id)
        await repo.apply_delta(db, user_id, -price, "usage", action)
    return price


async def ledger(
    db: AsyncSession, user_id: str, paging: PaginationParams
) -> PaginatedApiResponse[LedgerEntryResponse]:
    return await repo.list_ledger(db, user_id, paging)
