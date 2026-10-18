from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.find_leads.models.lead import Lead
from src.find_leads.schemas import LeadFilters, LeadResponse

ORDER_BY_STATUS = {
    "contacted": Lead.contacted_at,
    "discarded": Lead.discarded_at,
}


class LeadRepository:
    ID_PREFIX = "ld"

    async def get(self, db: AsyncSession, site_id: str, lead_id: str) -> Lead | None:
        result = await db.execute(
            select(Lead).where(Lead.site_id == site_id, Lead.id == lead_id).limit(1)
        )
        return result.scalars().first()

    async def get_many(self, db: AsyncSession, site_id: str, ids: list[str]) -> dict[str, Lead]:
        if not ids:
            return {}
        result = await db.execute(select(Lead).where(Lead.site_id == site_id, Lead.id.in_(ids)))
        return {row.id: row for row in result.scalars().all()}

    async def existing_keys(self, db: AsyncSession, site_id: str, keys: list[str]) -> set[str]:
        if not keys:
            return set()
        result = await db.execute(
            select(Lead.identity_key).where(Lead.site_id == site_id, Lead.identity_key.in_(keys))
        )
        return set(result.scalars().all())

    async def count_for_run(self, db: AsyncSession, run_id: str) -> int:
        result = await db.execute(
            select(func.count()).select_from(Lead).where(Lead.run_id == run_id)
        )
        return int(result.scalar_one())

    async def insert_many(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        run_id: str,
        rows: list[dict[str, Any]],
    ) -> int:
        if not rows:
            return 0
        now = datetime.now(UTC)
        stmt = (
            pg_insert(Lead)
            .values(
                [
                    {
                        "id": uid(self.ID_PREFIX),
                        "user_id": user_id,
                        "site_id": site_id,
                        "run_id": run_id,
                        "status": "candidate",
                        "created_at": now,
                        "updated_at": now,
                        **row,
                    }
                    for row in rows
                ]
            )
            .on_conflict_do_nothing(constraint="lead_site_identity_key")
            .returning(Lead.id)
        )
        result = await db.execute(stmt)
        await db.flush()
        return len(result.scalars().all())

    async def list_by_status(
        self, db: AsyncSession, site_id: str, status: str, limit: int
    ) -> list[Lead]:
        result = await db.execute(
            select(Lead)
            .where(Lead.site_id == site_id, Lead.status == status)
            .order_by(Lead.seq.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_unenriched(self, db: AsyncSession, site_id: str, limit: int) -> list[Lead]:
        result = await db.execute(
            select(Lead)
            .where(
                Lead.site_id == site_id,
                Lead.status == "shortlisted",
                Lead.enriched_at.is_(None),
            )
            .order_by(Lead.seq.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def set_activity(self, db: AsyncSession, lead_id: str, activity: list[dict]) -> None:
        now = datetime.now(UTC)
        await db.execute(
            update(Lead)
            .where(Lead.id == lead_id)
            .values(activity=activity, enriched_at=now, updated_at=now)
        )

    async def update(self, db: AsyncSession, row: Lead, values: dict[str, Any]) -> Lead:
        for key, value in values.items():
            setattr(row, key, value)
        row.updated_at = datetime.now(UTC)
        await db.flush()
        return row

    async def delete_many(self, db: AsyncSession, site_id: str, ids: list[str]) -> int:
        if not ids:
            return 0
        result = await db.execute(delete(Lead).where(Lead.site_id == site_id, Lead.id.in_(ids)))
        await db.flush()
        return int(result.rowcount or 0)

    async def status_counts(self, db: AsyncSession, site_id: str) -> dict[str, int]:
        result = await db.execute(
            select(Lead.status, func.count()).where(Lead.site_id == site_id).group_by(Lead.status)
        )
        return {status: int(n) for status, n in result.all()}

    async def counts_by_brief(
        self, db: AsyncSession, site_id: str, statuses: tuple[str, ...] | None = None
    ) -> dict[str, int]:
        query = (
            select(Lead.brief_id, func.count())
            .where(Lead.site_id == site_id, Lead.brief_id.is_not(None))
            .group_by(Lead.brief_id)
        )
        if statuses:
            query = query.where(Lead.status.in_(statuses))
        result = await db.execute(query)
        return {brief_id: int(n) for brief_id, n in result.all()}

    def _filtered(self, site_id: str, filters: LeadFilters) -> Select:
        query = select(Lead).where(Lead.site_id == site_id)
        if filters.statuses:
            query = query.where(Lead.status.in_(filters.statuses))
        if filters.brief_id:
            query = query.where(Lead.brief_id == filters.brief_id)
        if filters.run_id:
            query = query.where(Lead.run_id == filters.run_id)
        if filters.source:
            query = query.where(Lead.source == filters.source)
        if filters.q:
            pattern = f"%{filters.q.strip()}%"
            query = query.where(
                or_(
                    Lead.name.ilike(pattern),
                    Lead.handle.ilike(pattern),
                    Lead.headline.ilike(pattern),
                    Lead.reason.ilike(pattern),
                    Lead.email.ilike(pattern),
                )
            )
        return query

    async def delete_pipeline_before(self, db: AsyncSession, cutoff: datetime) -> int:
        result = await db.execute(
            delete(Lead).where(
                Lead.status.in_(("candidate", "shortlisted")), Lead.created_at < cutoff
            )
        )
        await db.flush()
        return int(result.rowcount or 0)

    async def discarded_before(self, db: AsyncSession, cutoff: datetime) -> list[Lead]:
        result = await db.execute(
            select(Lead).where(Lead.status == "discarded", Lead.discarded_at < cutoff)
        )
        return list(result.scalars().all())

    async def delete_ids(self, db: AsyncSession, ids: list[str]) -> int:
        if not ids:
            return 0
        result = await db.execute(delete(Lead).where(Lead.id.in_(ids)))
        await db.flush()
        return int(result.rowcount or 0)

    async def list(
        self, db: AsyncSession, site_id: str, filters: LeadFilters, paging: PaginationParams
    ) -> PaginatedApiResponse[LeadResponse]:
        query = self._filtered(site_id, filters)
        single = filters.statuses[0] if filters.statuses and len(filters.statuses) == 1 else None
        stamp = ORDER_BY_STATUS.get(single or "")
        if stamp is not None:
            query = query.order_by(stamp.desc().nulls_last(), Lead.seq.desc())
        else:
            query = query.order_by(Lead.seq.desc())
        return await PaginationService.paginate_query(
            db, query, paging.page, paging.page_size, LeadResponse
        )


leads = LeadRepository()
