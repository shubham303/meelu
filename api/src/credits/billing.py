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


def period() -> timedelta:
    return timedelta(hours=settings.credits_billing_period_hours)


async def start_site(db: AsyncSession, user_id: str, site_id: str) -> bool:
    await repo.ensure_site_billing(db, user_id, site_id)
    return await charge_site(
        db, DueSite(site_id=site_id, user_id=user_id, status=ACTIVE, domain="")
    )


async def charge_site(db: AsyncSession, site: DueSite) -> bool:
    price = pricing.site_day_price_micros()
    balance = await repo.balance(db, site.user_id)
    if balance < price:
        await repo.set_site_status(db, site.site_id, DISABLED)
        return False
    await repo.apply_delta(db, site.user_id, -price, "site_day", site.site_id)
    await repo.mark_charged(db, site.site_id, price)
    await repo.set_site_status(db, site.site_id, ACTIVE)
    return True


async def sweep(limit: int = 500) -> SweepResult:
    cutoff = datetime.now(UTC) - period()
    async with unit_of_work() as db:
        due = await repo.due_sites(db, cutoff, limit)

    result = SweepResult(considered=len(due))
    for site in due:
        try:
            async with unit_of_work() as db:
                if not await repo.lock_due_site(db, site.site_id, cutoff):
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
    return result
