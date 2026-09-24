from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.technical_seo.rules.render import (
    BOTH_RENDERED,
    JS_ONLY_CONTENT,
    MOBILE_DIFFERS,
    RENDERED,
)


@dataclass(frozen=True)
class RenderCounts:
    rendered: int
    js_dependent: int
    both_rendered: int
    mobile_differs: int


PAGES = (
    "site_pages"
    " left join site_page_renders r on r.page_id = site_pages.id and r.device = 'desktop'"
    " left join site_page_renders m on m.page_id = site_pages.id and m.device = 'mobile'"
    " left join site_page_llm_extraction x on x.page_id = site_pages.id"
)


async def count_matching(db: AsyncSession, site_id: str, where: str) -> int:
    result = await db.execute(
        text(
            f"select count(*)::int as matched from {PAGES}"
            f" where site_pages.site_id = :site_id and ({where})"
        ),
        {"site_id": site_id},
    )
    return result.scalar_one()


async def worst_matching(db: AsyncSession, site_id: str, where: str, limit: int) -> list[str]:
    result = await db.execute(
        text(
            f"select site_pages.id from {PAGES}"
            f" where site_pages.site_id = :site_id and ({where})"
            f" order by site_pages.depth asc nulls last, site_pages.inlinks desc,"
            f" site_pages.url asc limit :limit"
        ),
        {"site_id": site_id, "limit": limit},
    )
    return [row.id for row in result]


async def page_id_by_url(db: AsyncSession, site_id: str, url: str) -> str | None:
    result = await db.execute(
        text("select id from site_pages where site_id = :site_id and url = :url limit 1"),
        {"site_id": site_id, "url": url},
    )
    row = result.first()
    return row.id if row else None


async def page_exists(db: AsyncSession, site_id: str, page_id: str) -> bool:
    result = await db.execute(
        text("select id from site_pages where site_id = :site_id and id = :id limit 1"),
        {"site_id": site_id, "id": page_id},
    )
    return result.first() is not None


async def render_counts(db: AsyncSession, site_id: str) -> RenderCounts:
    result = await db.execute(
        text(
            f"select count(*) filter (where {RENDERED})::int as rendered,"
            f" count(*) filter (where {JS_ONLY_CONTENT})::int as js_dependent,"
            f" count(*) filter (where {BOTH_RENDERED})::int as both_rendered,"
            f" count(*) filter (where {MOBILE_DIFFERS})::int as mobile_differs"
            f" from {PAGES} where site_pages.site_id = :site_id"
        ),
        {"site_id": site_id},
    )
    row = result.one()
    return RenderCounts(
        rendered=row.rendered,
        js_dependent=row.js_dependent,
        both_rendered=row.both_rendered,
        mobile_differs=row.mobile_differs,
    )
