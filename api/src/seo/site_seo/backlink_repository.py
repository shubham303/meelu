from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, delete, exists, func, select, update
from sqlalchemy.dialects.postgresql import aggregate_order_by, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from src.core.ids import uid
from src.seo.site_seo.constants import BACKLINK_ID_PREFIX
from src.seo.site_seo.models.site_backlink import SiteBacklink
from src.seo.site_seo.models.site_competitor import SiteCompetitor
from src.seo.site_seo.schemas import BacklinkDraft

INSERT_BATCH = 500


class BacklinkRepository:
    async def replace_for_domain(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        site_domain: str,
        drafts: list[BacklinkDraft],
    ) -> None:
        await db.execute(
            delete(SiteBacklink).where(
                SiteBacklink.site_id == site_id, SiteBacklink.site_domain == site_domain
            )
        )
        now = datetime.now(UTC)
        rows = [
            {
                **d.model_dump(),
                "id": uid(BACKLINK_ID_PREFIX),
                "user_id": user_id,
                "site_id": site_id,
                "created_at": now,
                "updated_at": now,
            }
            for d in drafts
        ]
        for start in range(0, len(rows), INSERT_BATCH):
            await db.execute(
                insert(SiteBacklink)
                .values(rows[start : start + INSERT_BATCH])
                .on_conflict_do_nothing(constraint="site_backlinks_key")
            )

    async def delete_for_domains(self, db: AsyncSession, site_id: str, domains: list[str]) -> None:
        if domains:
            await db.execute(
                delete(SiteBacklink).where(
                    SiteBacklink.site_id == site_id, SiteBacklink.site_domain.in_(domains)
                )
            )

    async def delete_backlinking_domain(self, db: AsyncSession, site_id: str, domain: str) -> int:
        result = await db.execute(
            delete(SiteBacklink).where(
                SiteBacklink.site_id == site_id, SiteBacklink.backlinking_domain == domain
            )
        )
        return result.rowcount or 0

    async def dismissed_domains(self, db: AsyncSession, site_id: str) -> set[str]:
        rows = await db.scalars(
            select(SiteBacklink.backlinking_domain)
            .where(SiteBacklink.site_id == site_id, SiteBacklink.dismissed)
            .distinct()
        )
        return set(rows)

    async def counts_by_domain(self, db: AsyncSession, site_id: str) -> dict[str, int]:
        rows = await db.execute(
            select(SiteBacklink.site_domain, func.count())
            .where(SiteBacklink.site_id == site_id)
            .group_by(SiteBacklink.site_domain)
        )
        return {domain: total for domain, total in rows.all()}

    async def dismiss(self, db: AsyncSession, site_id: str, domains: list[str]) -> list[str]:
        if not domains:
            return []
        rows = await db.scalars(
            update(SiteBacklink)
            .where(SiteBacklink.site_id == site_id, SiteBacklink.backlinking_domain.in_(domains))
            .values(dismissed=True, updated_at=datetime.now(UTC))
            .returning(SiteBacklink.backlinking_domain)
        )
        return sorted(set(rows))

    async def opportunities(
        self, db: AsyncSession, site_id: str, own_domain: str, offset: int, limit: int
    ) -> tuple[list[dict[str, Any]], int]:
        theirs = SiteBacklink
        ours = aliased(SiteBacklink)
        rival = aliased(SiteCompetitor)
        best = func.array_agg(
            aggregate_order_by(theirs.backlinking_url, theirs.page_rank.desc().nulls_last())
        )
        best_anchor = func.array_agg(
            aggregate_order_by(theirs.anchor, theirs.page_rank.desc().nulls_last())
        )
        linked = func.count(theirs.site_domain.distinct())
        query = (
            select(
                theirs.backlinking_domain.label("domain"),
                func.array_agg(
                    aggregate_order_by(theirs.site_domain.distinct(), theirs.site_domain)
                ).label("links_to"),
                func.max(theirs.domain_rank).label("domain_rank"),
                func.max(theirs.domain_spam_score).label("domain_spam_score"),
                func.min(theirs.backlink_spam_score).label("backlink_spam_score"),
                func.bool_or(func.coalesce(theirs.dofollow, False)).label("dofollow"),
                best[1].label("example_url"),
                best_anchor[1].label("example_anchor"),
            )
            .join(
                SiteCompetitor,
                and_(
                    SiteCompetitor.site_id == theirs.site_id,
                    SiteCompetitor.domain == theirs.site_domain,
                ),
            )
            .where(
                theirs.site_id == site_id,
                ~theirs.dismissed,
                theirs.backlinking_domain != own_domain,
                ~exists().where(
                    ours.site_id == site_id,
                    ours.site_domain == own_domain,
                    ours.backlinking_domain == theirs.backlinking_domain,
                ),
                ~exists().where(
                    rival.site_id == site_id,
                    rival.domain == theirs.backlinking_domain,
                ),
            )
            .group_by(theirs.backlinking_domain)
        )
        total = await db.scalar(select(func.count()).select_from(query.subquery()))
        rows = await db.execute(
            query.order_by(
                linked.desc(),
                func.max(theirs.domain_rank).desc().nulls_last(),
                theirs.backlinking_domain,
            )
            .offset(offset)
            .limit(limit)
        )
        return [dict(r) for r in rows.mappings()], int(total or 0)


site_backlinks = BacklinkRepository()
