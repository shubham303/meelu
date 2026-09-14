from datetime import UTC, datetime
from typing import Any

import pytest

PAGE_DEFAULTS: dict[str, Any] = {
    "status": 200,
    "inlinks": 0,
    "inbound_anchors": [],
    "title": None,
    "title_pixels": 400,
    "meta_description": None,
    "h1": [],
    "headings": [],
    "body_text": None,
    "out_links": [],
    "external_links": [],
    "canonical": None,
    "robots_directives": None,
    "x_robots_tag": None,
    "blocked_by_robots": False,
    "has_viewport": True,
    "schema_types": [],
    "schema_nodes": [],
    "lang": "en",
    "hreflang": {},
    "kind": "other",
    "in_sitemap": False,
    "depth": 1,
    "redirect_hops": None,
    "images": [],
    "word_count": 500,
    "mixed_content": False,
    "keywords": [],
    "questions_answered": [],
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

    made: dict[str, str] = {}
    async with SessionLocal() as db:
        now = datetime.now(UTC)
        for page in pages:
            values = {**PAGE_DEFAULTS, **page}
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
