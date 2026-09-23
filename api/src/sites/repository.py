from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.sites.models.site import Site
from src.sites.schemas import SiteFilters, SiteRecord


def _order(sort: str | None):
    if sort == "name":
        return (Site.name.asc(), Site.seq.asc())
    if sort == "domain":
        return (Site.domain.asc(), Site.seq.asc())
    if sort == "crawled":
        return (Site.last_crawled_at.desc().nulls_last(), Site.seq.asc())
    return (Site.seq.asc(),)


def _conditions(user_id: str, f: SiteFilters):
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
    if f.country:
        conds.append(Site.country == f.country)
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
            Site.last_crawled_at.is_(None) if f.never_crawled else Site.last_crawled_at.is_not(None)
        )
    if f.crawled_before is not None:
        conds.append(Site.last_crawled_at < f.crawled_before)
    if f.crawled_after is not None:
        conds.append(Site.last_crawled_at > f.crawled_after)
    return conds


async def list_sites(
    db: AsyncSession, user_id: str, filters: SiteFilters, paging: PaginationParams
) -> PaginatedApiResponse[SiteRecord]:
    query = select(Site).where(*_conditions(user_id, filters)).order_by(*_order(filters.sort))
    return await PaginationService.paginate_query(
        db, query, paging.page, paging.page_size, SiteRecord
    )


async def _row(db: AsyncSession, user_id: str, site_id: str) -> Site | None:
    result = await db.execute(
        select(Site).where(Site.user_id == user_id, Site.id == site_id).limit(1)
    )
    return result.scalars().first()


async def get_site(db: AsyncSession, user_id: str, site_id: str) -> SiteRecord | None:
    row = await _row(db, user_id, site_id)
    return None if row is None else SiteRecord.model_validate(row)


async def default_site_id(db: AsyncSession, user_id: str) -> str | None:
    result = await db.execute(
        select(Site.id).where(Site.user_id == user_id).order_by(Site.seq.asc()).limit(2)
    )
    ids = result.scalars().all()
    return ids[0] if len(ids) == 1 else None


async def count_sites(db: AsyncSession, user_id: str) -> int:
    result = await db.execute(select(func.count()).select_from(Site).where(Site.user_id == user_id))
    return result.scalar_one()


async def create_site(db: AsyncSession, user_id: str, values: dict[str, Any]) -> SiteRecord:
    now = datetime.now(UTC)
    site = Site(id=uid("site"), user_id=user_id, created_at=now, updated_at=now, **values)
    db.add(site)
    await db.flush()
    await db.refresh(site)
    return SiteRecord.model_validate(site)


async def merge_site(
    db: AsyncSession, user_id: str, site_id: str, values: dict[str, Any]
) -> SiteRecord | None:
    site = await _row(db, user_id, site_id)
    if site is None:
        return None
    for key, value in values.items():
        setattr(site, key, value)
    site.updated_at = datetime.now(UTC)
    await db.flush()
    return SiteRecord.model_validate(site)


async def delete_site(db: AsyncSession, user_id: str, site_id: str) -> SiteRecord | None:
    site = await _row(db, user_id, site_id)
    if site is None:
        return None
    record = SiteRecord.model_validate(site)
    await db.delete(site)
    await db.flush()
    return record


async def find_site_by_domain(db: AsyncSession, user_id: str, domain: str) -> SiteRecord | None:
    result = await db.execute(
        select(Site).where(Site.user_id == user_id, Site.domain == domain).limit(1)
    )
    row = result.scalars().first()
    return None if row is None else SiteRecord.model_validate(row)
