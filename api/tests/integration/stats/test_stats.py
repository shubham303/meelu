from sqlalchemy import select

from src.content.models.content_pieces import ContentPiece
from src.core.database import unit_of_work
from src.core.ids import uid
from src.profile.models.user import User
from src.site_pages.models.site_page import SitePage
from tests.conftest import signup

EMPTY = {
    "content": {"drafts": 0, "blocked": 0},
    "seo": {"pages": 0},
}


async def user_id_for(email):
    async with unit_of_work() as db:
        result = await db.execute(select(User.id).where(User.email == email))
        return result.scalar_one()


async def seed_rows(user_id, site_id):
    async with unit_of_work() as db:
        for status in ("draft", "draft", "draft", "blocked", "blocked"):
            db.add(
                ContentPiece(
                    id=uid("cpc"),
                    user_id=user_id,
                    site_id=site_id,
                    channel_key="linkedin",
                    title="Launch",
                    status=status,
                )
            )
        await db.flush()

        for i, blocked in enumerate([False, False, False, True]):
            db.add(
                SitePage(
                    id=uid("pg"),
                    user_id=user_id,
                    site_id=site_id,
                    url=f"https://stats.example/page-{i}",
                    blocked_by_robots=blocked,
                )
            )


async def test_stats_without_a_site(client, email):
    await signup(client, email)

    r = await client.get("/api/v1/stats")
    assert r.status_code == 200
    assert r.json() == {"data": EMPTY}


async def test_stats_rollups(client, email):
    await signup(client, email)
    r = await client.post("/api/v1/sites", json={"domain": "stats.example", "name": "Stats"})
    assert r.status_code == 201, r.text
    site = r.json()["data"]

    r = await client.get("/api/v1/stats")
    assert r.json() == {"data": EMPTY}

    user_id = await user_id_for(email)
    await seed_rows(user_id, site["id"])

    r = await client.get("/api/v1/stats")
    assert r.status_code == 200
    assert r.json()["data"] == {
        "content": {"drafts": 3, "blocked": 2},
        "seo": {"pages": 3},
    }


async def test_stats_are_scoped_to_the_named_site(client, email):
    await signup(client, email)
    r = await client.post("/api/v1/sites", json={"domain": "one.example", "name": "One"})
    first = r.json()["data"]
    r = await client.post("/api/v1/sites", json={"domain": "two.example", "name": "Two"})
    second = r.json()["data"]

    user_id = await user_id_for(email)
    await seed_rows(user_id, first["id"])

    r = await client.get("/api/v1/stats", headers={"x-meelu-site": first["id"]})
    assert r.json()["data"]["seo"]["pages"] == 3

    r = await client.get("/api/v1/stats", headers={"x-meelu-site": second["id"]})
    assert r.json() == {"data": EMPTY}

    r = await client.get("/api/v1/stats")
    assert r.status_code == 400
    assert "has 2 websites" in r.json()["error"]["message"]
