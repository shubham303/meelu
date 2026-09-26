import re
from datetime import UTC, datetime
from statistics import median
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.seo.constants import CTR_MIN_SAMPLE, IMPRESSIONS_FLOOR, YEAR_DAYS
from src.seo.precompute.embed import seo_embed_service
from src.seo.repositories import (
    seo_keyword_gsc_pages,
    seo_keywords,
    seo_page_facts,
    seo_site_states,
)
from src.seo.schemas import RollupResult
from src.site_pages.llm_extraction.repository import site_page_llm_extractions
from src.site_pages.repositories.pages import site_pages
from src.site_pages.schemas import SitePageRecord
from src.site_search.repositories.site_search_daily import site_search_dailies
from src.site_search.schemas import PageWindowTotals, QueryPageWindowTotals, QueryWindowTotals

URL_ORIGIN = re.compile(r"^[a-z]+://[^/]+")


def ctr_curve(rows: list[tuple[str, float, float, int]]) -> dict[str, float]:
    by_position: dict[int, list[float]] = {}
    for _, position, ctr, _ in rows:
        by_position.setdefault(max(1, round(position)), []).append(ctr)
    return {
        str(pos): float(median(values))
        for pos, values in sorted(by_position.items())
        if len(values) >= CTR_MIN_SAMPLE
    }


def expected_ctr(curve: dict[str, float], position: float) -> float | None:
    if not curve:
        return None
    known = sorted((int(k), v) for k, v in curve.items())
    target = max(1, round(position))
    nearest = min(known, key=lambda kv: (abs(kv[0] - target), kv[0]))
    return nearest[1]


def heading_texts(headings: list[Any]) -> list[str]:
    return [
        str(h["text"]) for h in headings if isinstance(h, dict) and h.get("text") is not None
    ]


def page_fact_values(
    page: SitePageRecord, page_type: str | None, search: PageWindowTotals | None
) -> dict[str, Any]:
    live = (
        page.status is not None and 200 <= page.status <= 299 and not page.blocked_by_robots
    )
    noindex = "noindex" in (page.robots_directives or "").lower() or "noindex" in (
        page.x_robots_tag or ""
    ).lower()
    return {
        "page_id": page.id,
        "url": page.url,
        "status": page.status,
        "redirect_to": page.redirect_to,
        "page_type": page_type,
        "lang": page.lang,
        "title": page.title,
        "h1": page.h1[0] if page.h1 else None,
        "headings": heading_texts(page.headings),
        "meta_description": page.meta_description,
        "title_pixels": page.title_pixels,
        "word_count": page.word_count,
        "inlinks": page.inlinks,
        "link_score": page.link_score,
        "published_at": page.published_at,
        "first_seen_at": page.created_at,
        "content_hash": page.content_hash,
        "indexable": live and not noindex,
        "live": live,
        "is_home": URL_ORIGIN.sub("", page.url, count=1) in ("", "/"),
        "impressions_28d": (search.impressions_28d if search else None) or 0,
        "clicks_28d": (search.clicks_28d if search else None) or 0,
        "impressions_ly_28d": search.impressions_ly_28d if search else None,
        "clicks_ly_28d": search.clicks_ly_28d if search else None,
    }


def search_counts(totals: QueryWindowTotals, has_ly: bool) -> dict[str, Any]:
    return {
        "keyword": totals.query,
        "impressions_28d": totals.impressions_28d,
        "clicks_28d": totals.clicks_28d,
        "impressions_prev_28d": totals.impressions_prev_28d,
        "clicks_prev_28d": totals.clicks_prev_28d,
        "impressions_ly_28d": totals.impressions_ly_28d if has_ly else None,
        "clicks_ly_28d": totals.clicks_ly_28d if has_ly else None,
    }


def keyword_page_values(
    totals: QueryPageWindowTotals, keyword_id: str, page_id: str, has_ly: bool
) -> dict[str, Any]:
    return {
        "keyword_id": keyword_id,
        "page_id": page_id,
        "position": totals.position_28d if totals.impressions_28d > 0 else None,
        "impressions_28d": totals.impressions_28d,
        "clicks_28d": totals.clicks_28d,
        "impressions_prev_28d": totals.impressions_prev_28d,
        "clicks_prev_28d": totals.clicks_prev_28d,
        "impressions_ly_28d": totals.impressions_ly_28d if has_ly else None,
        "clicks_ly_28d": totals.clicks_ly_28d if has_ly else None,
        "ctr": totals.clicks_28d / totals.impressions_28d if totals.impressions_28d > 0 else None,
        "leader_days_90d": totals.leader_days_90d,
    }


class SeoRollupService:
    async def run(self, db: AsyncSession, user_id: str, site_id: str) -> RollupResult:
        pages = await self.refresh_page_facts(db, user_id, site_id)
        keywords, keyword_pages = await self.rollup_keywords(db, user_id, site_id)
        state = await seo_site_states.get(db, site_id)
        await seo_keywords.mark_branded(db, site_id, list(state.brand_terms) if state else [])
        curve = await self.refresh_ctr(db, site_id)
        stamped = await self.stamp(db, site_id, curve)
        embedded = await seo_embed_service.embed_pending(db, user_id, site_id)
        return RollupResult(
            pages=pages,
            keywords=keywords,
            keyword_pages=keyword_pages,
            embedded=embedded,
            rollup_at=stamped,
        )

    async def refresh_page_facts(self, db: AsyncSession, user_id: str, site_id: str) -> int:
        pages = await site_pages.list_for_site(db, site_id)
        page_ids = [p.id for p in pages]
        page_types = await site_page_llm_extractions.page_types_by_page_ids(db, site_id, page_ids)
        search = {t.page: t for t in await site_search_dailies.page_window_totals(db, site_id)}
        rows = [page_fact_values(p, page_types.get(p.id), search.get(p.url)) for p in pages]
        count = await seo_page_facts.upsert_many(db, user_id, site_id, rows)
        await seo_page_facts.retire_except(db, site_id, page_ids)
        return count

    async def rollup_keywords(
        self, db: AsyncSession, user_id: str, site_id: str
    ) -> tuple[int, int]:
        started = datetime.now(UTC)
        has_ly = await site_search_dailies.has_data_older_than(db, site_id, YEAR_DAYS)
        queries = await site_search_dailies.query_window_totals(db, site_id)
        terms = [q.query for q in queries if q.query and q.impressions_28d >= IMPRESSIONS_FLOOR]
        inserted = await seo_keywords.insert_many(db, user_id, site_id, terms, "gsc")
        known = await seo_keywords.ids_for(db, site_id, [q.query for q in queries])
        await seo_keywords.apply_search_counts(
            db, site_id, [search_counts(q, has_ly) for q in queries if q.query in known]
        )
        pairs = await self.refresh_keyword_pages(db, user_id, site_id, has_ly, started)
        await seo_keyword_gsc_pages.prune_before(db, site_id, started)
        return len(inserted), pairs

    async def refresh_keyword_pages(
        self, db: AsyncSession, user_id: str, site_id: str, has_ly: bool, started: datetime
    ) -> int:
        totals = await site_search_dailies.query_page_window_totals(db, site_id)
        keyword_ids = await seo_keywords.ids_for(db, site_id, list({t.query for t in totals}))
        page_ids = await site_pages.ids_by_urls(db, site_id, list({t.page for t in totals}))
        rows = [
            keyword_page_values(t, keyword_ids[t.query], page_ids[t.page], has_ly)
            for t in totals
            if t.query in keyword_ids and t.page in page_ids
        ]
        return await seo_keyword_gsc_pages.upsert_many(db, user_id, site_id, rows, started)

    async def refresh_ctr(self, db: AsyncSession, site_id: str) -> dict[str, float]:
        branded = await seo_keywords.branded_ids(db, site_id)
        rows = [
            (row_id, position, ctr, impressions)
            for row_id, keyword_id, position, ctr, impressions in await seo_keyword_gsc_pages.ctr_rows(
                db, site_id, IMPRESSIONS_FLOOR
            )
            if keyword_id not in branded
        ]
        curve = ctr_curve(rows)
        gaps = []
        for row_id, position, ctr, _ in rows:
            expected = expected_ctr(curve, position)
            gaps.append({"id": row_id, "gap": None if expected is None else expected - ctr})
        await seo_keyword_gsc_pages.set_ctr_gaps(db, gaps)
        return curve

    async def stamp(self, db: AsyncSession, site_id: str, curve: dict[str, float]) -> datetime:
        at = datetime.now(UTC)
        await seo_site_states.mark_rollup(db, site_id, at, curve)
        return at


seo_rollup_service = SeoRollupService()
