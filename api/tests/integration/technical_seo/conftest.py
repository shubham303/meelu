from datetime import UTC, datetime
from typing import Any

import pytest

PAGE_DEFAULTS: dict[str, Any] = {
    "status": 200,
    "inlinks": 0,
    "title": None,
    "title_pixels": 400,
    "meta_description": None,
    "h1": [],
    "headings": [],
    "body_text": None,
    "canonical": None,
    "robots_directives": None,
    "x_robots_tag": None,
    "blocked_by_robots": False,
    "viewport_meta": "width=device-width, initial-scale=1",
    "schema_types": [],
    "schema_nodes": [],
    "lang": "en",
    "hreflang": {},
    "in_sitemap": False,
    "depth": 1,
    "redirect_hops": None,
    "images": [],
    "word_count": 500,
    "mixed_content": False,
    "shallow": False,
}


@pytest.fixture(autouse=True)
def mount_router():
    from src.app import app
    from src.technical_seo.endpoints import router

    mounted = any(
        str(getattr(r, "path", "")).startswith("/api/v1/site/technical-seo") for r in app.routes
    )
    if not mounted:
        app.include_router(router, prefix="/api/v1")


async def seed_pages(site_id: str, user_id: str, pages: list[dict[str, Any]]) -> dict[str, str]:
    from src.core.database import SessionLocal
    from src.core.ids import uid
    from src.site_pages.models.site_page import SitePage
    from src.site_pages.models.site_page_link import SitePageLink
    from src.site_pages.models.site_page_llm_extraction import SitePageLlmExtraction
    from src.site_pages.url import normalise_url

    made: dict[str, str] = {}
    links_by_page: dict[str, list[dict[str, Any]]] = {}
    async with SessionLocal() as db:
        now = datetime.now(UTC)
        for page in pages:
            values = {**PAGE_DEFAULTS, **page}
            page_type = values.pop("page_type", None)
            page_links = values.pop("links", [])
            row = SitePage(
                id=uid("pg"),
                user_id=user_id,
                site_id=site_id,
                created_at=now,
                updated_at=now,
                **values,
            )
            db.add(row)
            made[values["url"]] = row.id
            links_by_page[row.id] = page_links
            if page_type is not None:
                db.add(
                    SitePageLlmExtraction(
                        id=uid("spx"),
                        user_id=user_id,
                        site_id=site_id,
                        page_id=row.id,
                        page_type=page_type,
                        extracted_from_hash=values.get("content_hash"),
                        extracted_at=now,
                        created_at=now,
                        updated_at=now,
                    )
                )
        for src_id, page_links in links_by_page.items():
            for link in page_links:
                db.add(
                    SitePageLink(
                        id=uid("spl"),
                        user_id=user_id,
                        site_id=site_id,
                        src_page_id=src_id,
                        dst_page_id=None,
                        dst_url=normalise_url(link["url"]),
                        external=bool(link.get("external")),
                        region=link.get("region", "body"),
                        rel=link.get("rel"),
                        anchor=link.get("anchor"),
                        count=link.get("count", 1),
                        followable="nofollow" not in (link.get("rel") or "").lower(),
                        dst_canonical=True,
                        created_at=now,
                        updated_at=now,
                    )
                )
        await db.commit()

    from src.site_pages.service import site_page_service

    async with SessionLocal() as db:
        await site_page_service.resolve_links(db, site_id)
        await db.commit()
    return made


async def user_id_of(email: str) -> str:
    from sqlalchemy import select

    from src.core.database import SessionLocal
    from src.profile.models.user import User

    async with SessionLocal() as db:
        result = await db.execute(select(User.id).where(User.email == email))
        return result.scalar_one()


async def set_site_facts(site_id: str, **facts: Any) -> None:
    from sqlalchemy import update

    from src.core.database import SessionLocal
    from src.sites.models.site import Site

    async with SessionLocal() as db:
        await db.execute(update(Site).where(Site.id == site_id).values(**facts))
        await db.commit()
