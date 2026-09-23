from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.seo.precompute import embed, rollup
from src.seo.schemas import RollupResult

REQUEST_SQL = """
update seo_site_state set precompute_requested_at = now(), updated_at = now()
where site_id = :site_id
"""

BRAND_TERMS_SQL = "select brand_terms from seo_site_state where site_id = :site_id"


async def run_rollup(db: AsyncSession, user_id: str, site_id: str) -> RollupResult:
    pages = await rollup.refresh_page_facts(db, site_id)
    keywords, keyword_pages = await rollup.rollup_keywords(db, user_id, site_id)
    terms = (await db.execute(text(BRAND_TERMS_SQL), {"site_id": site_id})).scalar() or []
    await rollup.mark_branded(db, site_id, list(terms))
    curve = await rollup.refresh_ctr(db, site_id)
    stamped = await rollup.stamp(db, site_id, curve)
    embedded = await embed.embed_pending(db, user_id, site_id)
    return RollupResult(
        pages=pages,
        keywords=keywords,
        keyword_pages=keyword_pages,
        embedded=embedded,
        rollup_at=stamped,
    )


async def request_rebuild(db: AsyncSession, site_id: str) -> None:
    await db.execute(text(REQUEST_SQL), {"site_id": site_id})
