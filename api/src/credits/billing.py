from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import unit_of_work
from src.core.logging import get_logger
from src.credits import pricing
from src.credits import repository as repo
from src.credits.schemas import DueSite, SweepResult
from src.settings import settings

log = get_logger("credits.billing")

ACTIVE = "active"
DISABLED = "disabled"
BATCH = 500
MAX_BATCHES = 20


def period() -> timedelta:
    return timedelta(hours=settings.credits_billing_period_hours)


def cutoff() -> datetime:
    return datetime.now(UTC) - period()


async def start_site(db: AsyncSession, user_id: str, site_id: str, domain: str) -> bool:
    await repo.ensure_site_billing(db, user_id, site_id, domain)
    if not await repo.lock_due_billing(db, user_id, domain, cutoff()):
        return True
    return await charge_site(
        db, DueSite(site_id=site_id, user_id=user_id, status=ACTIVE, domain=domain)
    )


async def charge_site(db: AsyncSession, site: DueSite) -> bool:
    price = pricing.site_day_price_micros()
    balance = await repo.balance(db, site.user_id)
    if balance < price:
        await repo.set_site_status(db, site.site_id, DISABLED)
        return False
    await repo.apply_delta(db, site.user_id, -price, "site_day", f"{site.domain} · one day")
    await repo.mark_charged(db, site.user_id, site.domain, price)
    await repo.set_site_status(db, site.site_id, ACTIVE)
    return True


async def sweep(limit: int = BATCH) -> SweepResult:
    result = SweepResult()
    seen: set[tuple[str, str]] = set()

    for _ in range(MAX_BATCHES):
        at = cutoff()
        async with unit_of_work() as db:
            due = [
                s for s in await repo.due_sites(db, at, limit) if (s.user_id, s.domain) not in seen
            ]
        if not due:
            break
        result.considered += len(due)
        for site in due:
            seen.add((site.user_id, site.domain))
            try:
                async with unit_of_work() as db:
                    if not await repo.lock_due_billing(db, site.user_id, site.domain, at):
                        continue
                    charged = await charge_site(db, site)
            except Exception as exc:
                result.failed += 1
                log.error("site_billing_failed", site_id=site.site_id, error=str(exc))
                continue
            if charged:
                result.charged += 1
                if site.status == DISABLED:
                    result.reactivated += 1
            elif site.status != DISABLED:
                result.disabled += 1
        if len(due) < limit:
            break
    return result
