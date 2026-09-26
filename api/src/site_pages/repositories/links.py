from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Integer, cast, delete, func, or_, select, tuple_, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.site_pages.models.site_page_link import SitePageLink
from src.site_pages.schemas import (
    PageLinkInput,
    SitePageEdge,
    SitePageLinkRecord,
)
from src.site_pages.url import normalise_url

LINK_REGIONS = ("body", "nav", "header", "footer", "aside", "breadcrumb", "pagination")

LINK_COLUMNS = (
    SitePageLink.id,
    SitePageLink.src_page_id,
    SitePageLink.dst_page_id,
    SitePageLink.dst_url,
    SitePageLink.external,
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
            .order_by(SitePageLink.external.asc(), SitePageLink.dst_url.asc())
            .limit(cap)
        )
        return [SitePageLinkRecord.model_validate(r) for r in rows.mappings()]

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

    async def list_internal(self, db: AsyncSession, site_id: str) -> list[tuple[str, str, str]]:
        rows = await db.execute(
            select(SitePageLink.id, SitePageLink.src_page_id, SitePageLink.dst_url).where(
                SitePageLink.site_id == site_id, SitePageLink.external.is_(False)
            )
        )
        return [(r.id, r.src_page_id, r.dst_url) for r in rows]

    async def distinct_internal_dst_urls(self, db: AsyncSession, site_id: str) -> list[str]:
        rows = await db.execute(
            select(SitePageLink.dst_url)
            .where(SitePageLink.site_id == site_id, SitePageLink.external.is_(False))
            .distinct()
        )
        return [str(u) for u in rows.scalars()]

    async def resolved_edges(self, db: AsyncSession, site_id: str) -> list[tuple[str, str, str]]:
        rows = await db.execute(
            select(SitePageLink.src_page_id, SitePageLink.dst_page_id, SitePageLink.region).where(
                SitePageLink.site_id == site_id, SitePageLink.dst_page_id.is_not(None)
            )
        )
        return [(r.src_page_id, r.dst_page_id, r.region) for r in rows]

    async def followable_edges(self, db: AsyncSession, site_id: str) -> list[SitePageEdge]:
        rows = await db.execute(
            select(SitePageLink.src_page_id, SitePageLink.dst_page_id)
            .where(
                SitePageLink.site_id == site_id,
                SitePageLink.dst_page_id.is_not(None),
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
        self, db: AsyncSession, site_id: str, page_ids: list[str]
    ) -> dict[str, tuple[int, int]]:
        if not page_ids:
            return {}
        rows = await db.execute(
            select(
                SitePageLink.src_page_id,
                cast(func.count().filter(SitePageLink.external.is_(False)), Integer),
                cast(func.count().filter(SitePageLink.external.is_(True)), Integer),
            )
            .where(SitePageLink.site_id == site_id, SitePageLink.src_page_id.in_(set(page_ids)))
            .group_by(SitePageLink.src_page_id)
        )
        return {r[0]: (int(r[1]), int(r[2])) for r in rows}

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
        links_by_page: dict[str, list[PageLinkInput]],
    ) -> int:
        if not links_by_page:
            return 0
        now = datetime.now(UTC)
        await db.execute(
            delete(SitePageLink).where(
                SitePageLink.site_id == site_id, SitePageLink.src_page_id.in_(list(links_by_page))
            )
        )

        rows: list[dict[str, Any]] = []
        for page_id, links in links_by_page.items():
            merged: dict[tuple[str, str], dict[str, Any]] = {}
            for link in links:
                target = normalise_url(link.url)
                if target == "":
                    continue
                region = self._region(link.region)
                key = (target, region)
                existing = merged.get(key)
                count = max(link.count, 1)
                if existing is None:
                    merged[key] = {
                        "id": uid(self.ID_PREFIX),
                        "user_id": user_id,
                        "site_id": site_id,
                        "src_page_id": page_id,
                        "dst_page_id": None,
                        "dst_url": target,
                        "external": link.external,
                        "region": region,
                        "rel": link.rel,
                        "anchor": link.anchor,
                        "count": count,
                        "followable": self._followable(link.rel),
                        "dst_canonical": True,
                        "created_at": now,
                        "updated_at": now,
                    }
                    continue
                existing["count"] += count
                existing["followable"] = existing["followable"] or self._followable(link.rel)
                if existing["anchor"] is None:
                    existing["anchor"] = link.anchor
            rows.extend(merged.values())

        if not rows:
            return 0
        for start in range(0, len(rows), INSERT_BATCH):
            await db.execute(pg_insert(SitePageLink).values(rows[start : start + INSERT_BATCH]))
        return len(rows)

    async def set_targets(
        self, db: AsyncSession, site_id: str, targets: dict[str, tuple[str | None, bool]]
    ) -> None:
        now = datetime.now(UTC)
        await db.execute(
            update(SitePageLink)
            .where(
                SitePageLink.site_id == site_id,
                or_(SitePageLink.dst_page_id.is_not(None), SitePageLink.dst_canonical.is_(False)),
            )
            .values(dst_page_id=None, dst_canonical=True, updated_at=now)
        )
        rows = [
            {"id": link_id, "dst_page_id": dst, "dst_canonical": canonical, "updated_at": now}
            for link_id, (dst, canonical) in targets.items()
        ]
        for start in range(0, len(rows), INSERT_BATCH):
            await db.execute(update(SitePageLink), rows[start : start + INSERT_BATCH])
        await db.flush()

    def _region(self, region: str | None) -> str:
        wanted = (region or "").strip().lower()
        return wanted if wanted in LINK_REGIONS else "body"

    def _followable(self, rel: str | None) -> bool:
        return "nofollow" not in (rel or "").lower()


site_page_links = SitePageLinkRepository()
