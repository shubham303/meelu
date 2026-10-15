from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import unit_of_work
from src.core.logging import get_logger
from src.credits import pricing
from src.credits.ledger import credit_ledger_service
from src.credits.repository import credit_accounts, site_billings
from src.credits.schemas import DueSite, SweepResult
from src.profile.repository import users
from src.settings import settings
from src.sites.repository import sites

log = get_logger("credits.billing")

ACTIVE = "active"
DISABLED = "disabled"
BATCH = 500
MAX_BATCHES = 20


def period() -> timedelta:
    return timedelta(hours=settings.credits_billing_period_hours)


def cutoff() -> datetime:
    return datetime.now(UTC) - period()


class SiteBillingService:
    async def due_sites(self, db: AsyncSession, at: datetime, limit: int) -> list[DueSite]:
        rows = await site_billings.list_due(db, at, limit)
        ids = [r.site_id for r in rows if r.site_id is not None]
        status = {s.id: s.status for s in await sites.list_refs(db, ids=ids)}
        return [
            DueSite(site_id=r.site_id, user_id=r.user_id, status=status[r.site_id], domain=r.domain)
            for r in rows
            if r.site_id in status
        ]

    async def start_site(self, db: AsyncSession, user_id: str, site_id: str, domain: str) -> bool:
        await site_billings.ensure(db, user_id, site_id, domain)
        if not await site_billings.lock_due(db, user_id, domain, cutoff()):
            return True
        return await self.charge_site(
            db, DueSite(site_id=site_id, user_id=user_id, status=ACTIVE, domain=domain)
        )

    async def charge_site(self, db: AsyncSession, site: DueSite) -> bool:
        earlier = await site_billings.count_earlier(db, site.user_id, site.domain)
        if earlier == 0 and await self._in_trial(db, site.user_id):
            await site_billings.mark_charged(db, site.user_id, site.domain, 0)
            await sites.set_status(db, site.site_id, ACTIVE, None)
            return True
        price = pricing.site_day_price_micros(earlier)
        balance = await credit_accounts.balance(db, site.user_id)
        if balance < price:
            await sites.set_status(db, site.site_id, DISABLED, datetime.now(UTC))
            return False
        await credit_ledger_service.apply(
            db, site.user_id, -price, "site_day", f"{site.domain} · one day"
        )
        await site_billings.mark_charged(db, site.user_id, site.domain, price)
        await sites.set_status(db, site.site_id, ACTIVE, None)
        return True

    async def _in_trial(self, db: AsyncSession, user_id: str) -> bool:
        user = await users.get(db, user_id)
        trial = timedelta(days=settings.credits_trial_days)
        return user is not None and datetime.now(UTC) - user.created_at < trial

    async def resume_user_sites(self, db: AsyncSession, user_id: str) -> int:
        at = cutoff()
        paused = await sites.list_refs(db, status=DISABLED, user_id=user_id)
        paid: list[str] = []
        unpaid = []
        for ref in paused:
            row = await site_billings.get(db, user_id, ref.domain)
            if row is not None and row.last_charged_at is not None and row.last_charged_at > at:
                paid.append(ref.id)
            else:
                unpaid.append(ref)

        resumed = 0
        if paid and await credit_accounts.balance(db, user_id) >= 0:
            for site_id in paid:
                await sites.set_status(db, site_id, ACTIVE, None)
            resumed += len(paid)

        for ref in unpaid:
            await site_billings.ensure(db, user_id, ref.id, ref.domain)
            if not await site_billings.lock_due(db, user_id, ref.domain, at):
                continue
            site = DueSite(site_id=ref.id, user_id=user_id, status=DISABLED, domain=ref.domain)
            if not await self.charge_site(db, site):
                break
            resumed += 1
        return resumed

    async def sweep(self, limit: int = BATCH) -> SweepResult:
        result = SweepResult()
        seen: set[tuple[str, str]] = set()

        for _ in range(MAX_BATCHES):
            at = cutoff()
            async with unit_of_work() as db:
                due = [
                    s
                    for s in await self.due_sites(db, at, limit)
                    if (s.user_id, s.domain) not in seen
                ]
            if not due:
                break
            result.considered += len(due)
            for site in due:
                seen.add((site.user_id, site.domain))
                try:
                    async with unit_of_work() as db:
                        if not await site_billings.lock_due(db, site.user_id, site.domain, at):
                            continue
                        charged = await self.charge_site(db, site)
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


site_billing_service = SiteBillingService()
