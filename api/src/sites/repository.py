from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.sites.models.site import Site
from src.sites.schemas import SiteFilters, SiteRecord, SiteRef


class SiteRepository:
    ID_PREFIX = "site"

    async def list_refs(
        self,
        db: AsyncSession,
        ids: list[str] | None = None,
        status: str | None = None,
        user_id: str | None = None,
    ) -> list[SiteRef]:
        if ids is not None and not ids:
            return []
        query = select(Site.id, Site.user_id, Site.domain, Site.status).order_by(Site.seq.asc())
        if ids is not None:
            query = query.where(Site.id.in_(ids))
        if user_id is not None:
            query = query.where(Site.user_id == user_id)
        if status is not None:
            query = query.where(Site.status == status)
        rows = await db.execute(query)
        return [SiteRef(id=r.id, user_id=r.user_id, domain=r.domain, status=r.status) for r in rows]

    async def get(self, db: AsyncSession, user_id: str, site_id: str) -> SiteRecord | None:
        row = await self._row(db, user_id, site_id)
        return None if row is None else SiteRecord.model_validate(row)

    async def get_default(self, db: AsyncSession, user_id: str) -> SiteRecord | None:
        result = await db.execute(
            select(Site).where(Site.user_id == user_id).order_by(Site.seq.asc()).limit(2)
        )
        rows = result.scalars().all()
        return SiteRecord.model_validate(rows[0]) if len(rows) == 1 else None

    async def find_by_domain(
        self, db: AsyncSession, user_id: str, domain: str
    ) -> SiteRecord | None:
        result = await db.execute(
            select(Site).where(Site.user_id == user_id, Site.domain == domain).limit(1)
        )
        row = result.scalars().first()
        return None if row is None else SiteRecord.model_validate(row)

    async def count(self, db: AsyncSession, user_id: str) -> int:
        result = await db.execute(
            select(func.count()).select_from(Site).where(Site.user_id == user_id)
        )
        return result.scalar_one()

    async def create(self, db: AsyncSession, user_id: str, values: dict[str, Any]) -> SiteRecord:
        now = datetime.now(UTC)
        site = Site(
            id=uid(self.ID_PREFIX), user_id=user_id, created_at=now, updated_at=now, **values
        )
        db.add(site)
        await db.flush()
        await db.refresh(site)
        return SiteRecord.model_validate(site)

    async def merge(
        self, db: AsyncSession, user_id: str, site_id: str, values: dict[str, Any]
    ) -> SiteRecord | None:
        site = await self._row(db, user_id, site_id)
        if site is None:
            return None
        for key, value in values.items():
            setattr(site, key, value)
        site.updated_at = datetime.now(UTC)
        await db.flush()
        return SiteRecord.model_validate(site)

    async def set_status(
        self, db: AsyncSession, site_id: str, status: str, paused_at: datetime | None
    ) -> None:
        await db.execute(
            update(Site)
            .where(Site.id == site_id, Site.status != status)
            .values(status=status, paused_at=paused_at, updated_at=datetime.now(UTC))
        )

    async def set_status_for_user(
        self, db: AsyncSession, user_id: str, status: str, paused_at: datetime | None
    ) -> int:
        result = await db.execute(
            update(Site)
            .where(Site.user_id == user_id, Site.status != status)
            .values(status=status, paused_at=paused_at, updated_at=datetime.now(UTC))
        )
        return result.rowcount or 0

    async def delete_paused_before(
        self, db: AsyncSession, status: str, before: datetime
    ) -> list[SiteRef]:
        result = await db.execute(
            delete(Site)
            .where(Site.status == status, Site.paused_at < before)
            .returning(Site.id, Site.user_id, Site.domain, Site.status)
        )
        return [
            SiteRef(id=r.id, user_id=r.user_id, domain=r.domain, status=r.status) for r in result
        ]

    async def delete(self, db: AsyncSession, user_id: str, site_id: str) -> SiteRecord | None:
        site = await self._row(db, user_id, site_id)
        if site is None:
            return None
        record = SiteRecord.model_validate(site)
        await db.delete(site)
        await db.flush()
        return record

    async def list(
        self, db: AsyncSession, user_id: str, filters: SiteFilters, paging: PaginationParams
    ) -> PaginatedApiResponse[SiteRecord]:
        query = (
            select(Site)
            .where(*self._conditions(user_id, filters))
            .order_by(*self._order(filters.sort))
        )
        return await PaginationService.paginate_query(
            db, query, paging.page, paging.page_size, SiteRecord
        )

    async def _row(self, db: AsyncSession, user_id: str, site_id: str) -> Site | None:
        result = await db.execute(
            select(Site).where(Site.user_id == user_id, Site.id == site_id).limit(1)
        )
        return result.scalars().first()

    def _order(self, sort: str | None):
        if sort == "name":
            return (Site.name.asc(), Site.seq.asc())
        if sort == "domain":
            return (Site.domain.asc(), Site.seq.asc())
        if sort == "crawled":
            return (Site.last_crawled_at.desc().nulls_last(), Site.seq.asc())
        return (Site.seq.asc(),)

    def _conditions(self, user_id: str, f: SiteFilters):
        conds = [Site.user_id == user_id]
        if f.q:
            like = f"%{f.q}%"
            conds.append(
                or_(
                    Site.name.ilike(like),
                    Site.domain.ilike(like),
                    func.coalesce(Site.summary, "").ilike(like),
                )
            )
        if f.domain:
            conds.append(Site.domain == f.domain)
        if f.status:
            conds.append(Site.status == f.status)
        if f.has_repo is not None:
            conds.append(
                and_(Site.repo_url.is_not(None), Site.repo_url != "")
                if f.has_repo
                else or_(Site.repo_url.is_(None), Site.repo_url == "")
            )
        if f.never_crawled is not None:
            conds.append(
                Site.last_crawled_at.is_(None)
                if f.never_crawled
                else Site.last_crawled_at.is_not(None)
            )
        if f.crawled_before is not None:
            conds.append(Site.last_crawled_at < f.crawled_before)
        if f.crawled_after is not None:
            conds.append(Site.last_crawled_at > f.crawled_after)
        return conds


sites = SiteRepository()
