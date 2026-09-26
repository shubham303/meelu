from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import JSONB, array
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.leads.models.campaign import LeadCampaign
from src.leads.models.lead import Lead
from src.leads.models.run import LeadRun
from src.leads.schemas import LeadFilters, LeadResponse, RunResponse


class LeadCampaignRepository:
    ID_PREFIX = "lc"

    async def get(self, db: AsyncSession, site_id: str, campaign_id: str) -> LeadCampaign | None:
        result = await db.execute(
            select(LeadCampaign)
            .where(LeadCampaign.site_id == site_id, LeadCampaign.id == campaign_id)
            .limit(1)
        )
        return result.scalars().first()

    async def find_by_name(self, db: AsyncSession, site_id: str, name: str) -> LeadCampaign | None:
        result = await db.execute(
            select(LeadCampaign)
            .where(LeadCampaign.site_id == site_id, LeadCampaign.name == name)
            .limit(1)
        )
        return result.scalars().first()

    async def create(
        self, db: AsyncSession, user_id: str, site_id: str, values: dict[str, Any]
    ) -> LeadCampaign:
        now = datetime.now(UTC)
        row = LeadCampaign(
            id=uid(self.ID_PREFIX),
            user_id=user_id,
            site_id=site_id,
            created_at=now,
            updated_at=now,
            **values,
        )
        db.add(row)
        await db.flush()
        return row

    async def update(
        self, db: AsyncSession, row: LeadCampaign, values: dict[str, Any]
    ) -> LeadCampaign:
        for key, value in values.items():
            setattr(row, key, value)
        row.updated_at = datetime.now(UTC)
        await db.flush()
        return row

    async def delete(self, db: AsyncSession, row: LeadCampaign) -> None:
        await db.delete(row)
        await db.flush()

    async def list(self, db: AsyncSession, site_id: str) -> list[LeadCampaign]:
        result = await db.execute(
            select(LeadCampaign)
            .where(LeadCampaign.site_id == site_id)
            .order_by(LeadCampaign.seq.asc())
        )
        return list(result.scalars().all())


class LeadRunRepository:
    ID_PREFIX = "lrn"

    async def create(
        self, db: AsyncSession, user_id: str, site_id: str, campaign_id: str
    ) -> LeadRun:
        now = datetime.now(UTC)
        row = LeadRun(
            id=uid(self.ID_PREFIX),
            user_id=user_id,
            site_id=site_id,
            campaign_id=campaign_id,
            status="running",
            started_at=now,
            found=0,
            qualified=0,
            skipped_known=0,
            source_stats={},
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.flush()
        return row

    async def get(self, db: AsyncSession, site_id: str, run_id: str) -> LeadRun | None:
        result = await db.execute(
            select(LeadRun).where(LeadRun.site_id == site_id, LeadRun.id == run_id).limit(1)
        )
        return result.scalars().first()

    async def latest(self, db: AsyncSession, site_id: str) -> RunResponse | None:
        result = await db.execute(
            select(LeadRun).where(LeadRun.site_id == site_id).order_by(LeadRun.seq.desc()).limit(1)
        )
        row = result.scalars().first()
        return None if row is None else RunResponse.model_validate(row)

    async def update(self, db: AsyncSession, row: LeadRun, values: dict[str, Any]) -> LeadRun:
        for key, value in values.items():
            setattr(row, key, value)
        row.updated_at = datetime.now(UTC)
        await db.flush()
        return row

    async def list(
        self, db: AsyncSession, site_id: str, campaign_id: str | None, paging: PaginationParams
    ) -> PaginatedApiResponse[RunResponse]:
        query = select(LeadRun).where(LeadRun.site_id == site_id)
        if campaign_id:
            query = query.where(LeadRun.campaign_id == campaign_id)
        query = query.order_by(LeadRun.seq.desc())
        return await PaginationService.paginate_query(
            db, query, paging.page, paging.page_size, RunResponse
        )


class LeadRepository:
    ID_PREFIX = "ld"

    async def find_with_any_keys(
        self, db: AsyncSession, site_id: str, keys: list[str]
    ) -> list[Lead]:
        if not keys:
            return []
        result = await db.execute(
            select(Lead).where(
                Lead.site_id == site_id,
                Lead.dedupe_keys.cast(JSONB).op("?|")(array(keys)),
            )
        )
        return list(result.scalars().all())

    async def create(
        self, db: AsyncSession, user_id: str, site_id: str, values: dict[str, Any]
    ) -> Lead:
        row = self._row(user_id, site_id, values)
        db.add(row)
        await db.flush()
        return row

    async def create_many(
        self, db: AsyncSession, user_id: str, site_id: str, rows: list[dict[str, Any]]
    ) -> int:
        if not rows:
            return 0
        db.add_all([self._row(user_id, site_id, values) for values in rows])
        await db.flush()
        return len(rows)

    async def get(self, db: AsyncSession, site_id: str, lead_id: str) -> Lead | None:
        result = await db.execute(
            select(Lead).where(Lead.site_id == site_id, Lead.id == lead_id).limit(1)
        )
        return result.scalars().first()

    async def list_all(self, db: AsyncSession, site_id: str, filters: LeadFilters) -> list[Lead]:
        result = await db.execute(
            select(Lead)
            .where(*self._conditions(site_id, filters))
            .order_by(*self._order(filters.sort))
        )
        return list(result.scalars().all())

    async def stage_counts(self, db: AsyncSession, site_id: str) -> dict[str, int]:
        result = await db.execute(
            select(Lead.stage, func.count()).where(Lead.site_id == site_id).group_by(Lead.stage)
        )
        return dict(result.all())

    async def campaign_stage_counts(
        self, db: AsyncSession, site_id: str
    ) -> dict[str, dict[str, int]]:
        result = await db.execute(
            select(Lead.campaign_id, Lead.stage, func.count())
            .where(Lead.site_id == site_id, Lead.campaign_id.is_not(None))
            .group_by(Lead.campaign_id, Lead.stage)
        )
        counts: dict[str, dict[str, int]] = {}
        for campaign_id, stage, count in result.all():
            counts.setdefault(campaign_id, {})[stage] = count
        return counts

    async def update(self, db: AsyncSession, row: Lead, values: dict[str, Any]) -> Lead:
        for key, value in values.items():
            setattr(row, key, value)
        row.updated_at = datetime.now(UTC)
        await db.flush()
        return row

    async def delete(self, db: AsyncSession, row: Lead) -> None:
        await db.delete(row)
        await db.flush()

    async def list(
        self, db: AsyncSession, site_id: str, filters: LeadFilters, paging: PaginationParams
    ) -> PaginatedApiResponse[LeadResponse]:
        query = (
            select(Lead)
            .where(*self._conditions(site_id, filters))
            .order_by(*self._order(filters.sort))
        )
        return await PaginationService.paginate_query(
            db, query, paging.page, paging.page_size, LeadResponse
        )

    def _row(self, user_id: str, site_id: str, values: dict[str, Any]) -> Lead:
        now = datetime.now(UTC)
        return Lead(
            id=uid(self.ID_PREFIX),
            user_id=user_id,
            site_id=site_id,
            created_at=now,
            updated_at=now,
            **values,
        )

    def _conditions(self, site_id: str, f: LeadFilters) -> Any:
        conds = [Lead.site_id == site_id]
        if f.stage:
            conds.append(Lead.stage == f.stage)
        if f.campaign_id:
            conds.append(Lead.campaign_id == f.campaign_id)
        if f.source:
            conds.append(Lead.source == f.source)
        if f.has_email is True:
            conds.append(Lead.email.is_not(None))
        if f.has_email is False:
            conds.append(Lead.email.is_(None))
        if f.min_fit is not None:
            conds.append(Lead.fit_score >= f.min_fit)
        if f.q:
            like = f"%{f.q}%"
            conds.append(
                or_(
                    Lead.name.ilike(like),
                    func.coalesce(Lead.company, "").ilike(like),
                )
            )
        return conds

    def _order(self, sort: str | None) -> Any:
        if sort == "fit":
            return (Lead.fit_score.desc().nulls_last(), Lead.seq.desc())
        return (Lead.seq.desc(),)


lead_campaigns = LeadCampaignRepository()
lead_runs = LeadRunRepository()
leads = LeadRepository()
