from datetime import UTC, datetime
from typing import Any

from sqlalchemy import any_, delete, func, literal, select, tuple_, update
from sqlalchemy.dialects.postgresql import ARRAY, TEXT
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.site_pages.models.site_page_link import SitePageLink
from src.site_pages.schemas import SitePageEdge, SitePageLinkRecord
from src.site_pages.schemas.links import NewSitePageLink

LINK_COLUMNS = (
    SitePageLink.id,
    SitePageLink.src_page_id,
    SitePageLink.dst_page_id,
    SitePageLink.dst_url,
    SitePageLink.region,
    SitePageLink.rel,
    SitePageLink.anchor,
    SitePageLink.count,
    SitePageLink.followable,
    SitePageLink.dst_canonical,
)

INSERT_BATCH = 1000


class SitePageLinkRepository:
    ID_PREFIX = "spl"

    async def list_outbound(
        self, db: AsyncSession, site_id: str, page_id: str, cap: int = 500
    ) -> list[SitePageLinkRecord]:
        rows = await db.execute(
            select(*LINK_COLUMNS)
            .where(SitePageLink.site_id == site_id, SitePageLink.src_page_id == page_id)
            .order_by(SitePageLink.dst_url.asc())
            .limit(cap)
        )
        return [SitePageLinkRecord.model_validate(r) for r in rows.mappings()]

    async def outbound_by_src_ids(
        self, db: AsyncSession, site_id: str, src_ids: list[str]
    ) -> dict[str, list[SitePageLinkRecord]]:
        if not src_ids:
            return {}
        rows = await db.execute(
            select(*LINK_COLUMNS)
            .where(SitePageLink.site_id == site_id, SitePageLink.src_page_id.in_(set(src_ids)))
            .order_by(SitePageLink.src_page_id, SitePageLink.dst_url.asc())
        )
        found: dict[str, list[SitePageLinkRecord]] = {}
        for r in rows.mappings():
            record = SitePageLinkRecord.model_validate(r)
            found.setdefault(record.src_page_id, []).append(record)
        return found

    async def list_inbound(
        self, db: AsyncSession, site_id: str, page_id: str
    ) -> list[SitePageLinkRecord]:
        rows = await db.execute(
            select(*LINK_COLUMNS).where(
                SitePageLink.site_id == site_id, SitePageLink.dst_page_id == page_id
            )
        )
        return [SitePageLinkRecord.model_validate(r) for r in rows.mappings()]

    async def list_between(
        self,
        db: AsyncSession,
        site_id: str,
        src_ids: list[str],
        dst_ids: list[str],
        region: str | None = None,
    ) -> list[SitePageLinkRecord]:
        if not src_ids or not dst_ids:
            return []
        conds: list[Any] = [
            SitePageLink.site_id == site_id,
            SitePageLink.src_page_id.in_(set(src_ids)),
            SitePageLink.dst_page_id.in_(set(dst_ids)),
        ]
        if region is not None:
            conds.append(SitePageLink.region == region)
        rows = await db.execute(select(*LINK_COLUMNS).where(*conds))
        return [SitePageLinkRecord.model_validate(r) for r in rows.mappings()]

    async def resolved_edges(self, db: AsyncSession, site_id: str) -> list[tuple[str, str, str]]:
        rows = await db.execute(
            select(SitePageLink.src_page_id, SitePageLink.dst_page_id, SitePageLink.region).where(
                SitePageLink.site_id == site_id
            )
        )
        return [(r.src_page_id, r.dst_page_id, r.region) for r in rows]

    async def followable_edges(self, db: AsyncSession, site_id: str) -> list[SitePageEdge]:
        rows = await db.execute(
            select(SitePageLink.src_page_id, SitePageLink.dst_page_id)
            .where(
                SitePageLink.site_id == site_id,
                SitePageLink.followable.is_(True),
                SitePageLink.dst_canonical.is_(True),
            )
            .distinct()
        )
        return [SitePageEdge(src=r.src_page_id, dst=r.dst_page_id) for r in rows]

    async def adjacency(self, db: AsyncSession, site_id: str) -> dict[str, set[str]]:
        rows = await db.execute(
            select(SitePageLink.src_page_id, SitePageLink.dst_page_id).where(
                SitePageLink.site_id == site_id
            )
        )
        links: dict[str, set[str]] = {}
        for src, dst in rows:
            links.setdefault(src, set()).add(dst)
        return links

    async def existing_pairs(
        self, db: AsyncSession, site_id: str, pairs: list[tuple[str, str]]
    ) -> set[tuple[str, str]]:
        if not pairs:
            return set()
        rows = await db.execute(
            select(SitePageLink.src_page_id, SitePageLink.dst_page_id)
            .where(
                SitePageLink.site_id == site_id,
                tuple_(SitePageLink.src_page_id, SitePageLink.dst_page_id).in_(set(pairs)),
            )
            .distinct()
        )
        return {(r.src_page_id, r.dst_page_id) for r in rows}

    async def pairs_among(
        self, db: AsyncSession, site_id: str, page_ids: list[str]
    ) -> set[tuple[str, str]]:
        if not page_ids:
            return set()
        ids = set(page_ids)
        rows = await db.execute(
            select(SitePageLink.src_page_id, SitePageLink.dst_page_id).where(
                SitePageLink.site_id == site_id,
                SitePageLink.src_page_id.in_(ids),
                SitePageLink.dst_page_id.in_(ids),
            )
        )
        return {(r.src_page_id, r.dst_page_id) for r in rows}

    async def pairs_into(
        self, db: AsyncSession, site_id: str, dst_ids: list[str]
    ) -> set[tuple[str, str]]:
        if not dst_ids:
            return set()
        rows = await db.execute(
            select(SitePageLink.src_page_id, SitePageLink.dst_page_id).where(
                SitePageLink.site_id == site_id,
                SitePageLink.dst_page_id.in_(set(dst_ids)),
            )
        )
        return {(r.src_page_id, r.dst_page_id) for r in rows}

    async def src_ids_linking_to(
        self, db: AsyncSession, site_id: str, dst_page_id: str
    ) -> set[str]:
        rows = await db.execute(
            select(SitePageLink.src_page_id).where(
                SitePageLink.site_id == site_id, SitePageLink.dst_page_id == dst_page_id
            )
        )
        return set(rows.scalars().all())

    async def inlink_counts(
        self, db: AsyncSession, site_id: str, page_ids: list[str]
    ) -> dict[str, int]:
        if not page_ids:
            return {}
        rows = await db.execute(
            select(SitePageLink.dst_page_id, func.count())
            .where(SitePageLink.site_id == site_id, SitePageLink.dst_page_id.in_(set(page_ids)))
            .group_by(SitePageLink.dst_page_id)
        )
        return {r[0]: int(r[1]) for r in rows}

    async def outlink_counts(
        self, db: AsyncSession, site_id: str, region: str | None = None
    ) -> dict[str, int]:
        conds: list[Any] = [SitePageLink.site_id == site_id]
        if region is not None:
            conds.append(SitePageLink.region == region)
        rows = await db.execute(
            select(SitePageLink.src_page_id, func.count())
            .where(*conds)
            .group_by(SitePageLink.src_page_id)
        )
        return {r[0]: int(r[1]) for r in rows}

    async def out_link_counts_by_src_ids(
        self, db: AsyncSession, site_id: str, page_ids: list[str], region: str | None = None
    ) -> dict[str, int]:
        if not page_ids:
            return {}
        conds: list[Any] = [
            SitePageLink.site_id == site_id,
            SitePageLink.src_page_id.in_(set(page_ids)),
        ]
        if region is not None:
            conds.append(SitePageLink.region == region)
        rows = await db.execute(
            select(SitePageLink.src_page_id, func.count())
            .where(*conds)
            .group_by(SitePageLink.src_page_id)
        )
        return {r[0]: int(r[1]) for r in rows}

    async def inbound_anchors_by_page_ids(
        self, db: AsyncSession, page_ids: list[str]
    ) -> dict[str, list[str]]:
        if not page_ids:
            return {}
        rows = await db.execute(
            select(SitePageLink.dst_page_id, SitePageLink.anchor)
            .where(
                SitePageLink.dst_page_id.in_(set(page_ids)),
                SitePageLink.anchor.is_not(None),
                SitePageLink.anchor != "",
            )
            .distinct()
            .order_by(SitePageLink.dst_page_id, SitePageLink.anchor)
        )
        found: dict[str, list[str]] = {}
        for dst, anchor in rows:
            found.setdefault(dst, []).append(anchor)
        return found

    async def replace_for_pages(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        links_by_page: dict[str, list[NewSitePageLink]],
    ) -> int:
        if not links_by_page:
            return 0
        now = datetime.now(UTC)
        await db.execute(
            delete(SitePageLink).where(
                SitePageLink.site_id == site_id, SitePageLink.src_page_id.in_(list(links_by_page))
            )
        )
        rows = [
            {
                **link.model_dump(),
                "id": uid(self.ID_PREFIX),
                "user_id": user_id,
                "site_id": site_id,
                "src_page_id": page_id,
                "created_at": now,
                "updated_at": now,
            }
            for page_id, links in links_by_page.items()
            for link in links
        ]
        for start in range(0, len(rows), INSERT_BATCH):
            await db.execute(pg_insert(SitePageLink).values(rows[start : start + INSERT_BATCH]))
        return len(rows)

    async def set_dst_canonical(
        self, db: AsyncSession, site_id: str, canonical_ids: set[str]
    ) -> None:
        await db.execute(
            update(SitePageLink)
            .where(SitePageLink.site_id == site_id)
            .values(
                dst_canonical=SitePageLink.dst_page_id
                == any_(literal(sorted(canonical_ids), ARRAY(TEXT))),
                updated_at=datetime.now(UTC),
            )
        )
        await db.flush()


site_page_links = SitePageLinkRepository()
