from datetime import UTC, datetime

from sqlalchemy import select

from src.content.models.content_pieces import ContentPiece
from src.core.database import unit_of_work
from src.core.ids import uid
from src.outreach.models.campaigns import Campaign
from src.outreach.models.conversations import Conversation
from src.outreach.models.projects import Project
from src.outreach.models.prospects import Prospect
from src.profile.models.user import User
from src.site_pages.models.site_page import SitePage
from tests.conftest import signup

EMPTY = {
    "outreach": {
        "projects": 0,
        "runs": 0,
        "activeRuns": 0,
        "prospects": 0,
        "drafts": 0,
        "sent": 0,
        "replies": 0,
    },
    "content": {"drafts": 0, "scheduled": 0, "posted": 0, "attention": 0},
    "seo": {"pages": 0},
}


async def user_id_for(email):
    async with unit_of_work() as db:
        result = await db.execute(select(User.id).where(User.email == email))
        return result.scalar_one()


async def seed_rows(user_id, site_id):
    now = datetime.now(UTC)
    async with unit_of_work() as db:
        project = Project(
            id=uid("prj"),
            user_id=user_id,
            site_id=site_id,
            name="Founder outreach",
            prospect_profile="Indie founders",
        )
        db.add(project)
        await db.flush()

        campaigns = []
        for status in ("running", "running", "done"):
            campaign = Campaign(
                id=uid("cmp"),
                user_id=user_id,
                site_id=site_id,
                project_id=project.id,
                requested_count=10,
                status=status,
            )
            db.add(campaign)
            campaigns.append(campaign)
        await db.flush()

        prospects = []
        for status in ("found", "replied", "replied", "bounced"):
            prospect = Prospect(
                id=uid("pro"),
                user_id=user_id,
                site_id=site_id,
                campaign_id=campaigns[0].id,
                name="Someone",
                status=status,
            )
            db.add(prospect)
            prospects.append(prospect)
        await db.flush()

        for status in ("draft", "draft", "draft", "sent", "skipped"):
            db.add(
                Conversation(
                    id=uid("cnv"),
                    user_id=user_id,
                    site_id=site_id,
                    prospect_id=prospects[0].id,
                    status=status,
                    subject="Hello",
                    body="Body",
                )
            )

        for status in (
            "draft",
            "draft",
            "draft",
            "scheduled",
            "scheduled",
            "posted",
            "failed",
            "blocked",
        ):
            db.add(
                ContentPiece(
                    id=uid("cpc"),
                    user_id=user_id,
                    site_id=site_id,
                    channel_key="linkedin",
                    title="Launch",
                    status=status,
                    scheduled_at=now,
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
        "outreach": {
            "projects": 1,
            "runs": 3,
            "activeRuns": 2,
            "prospects": 4,
            "drafts": 3,
            "sent": 1,
            "replies": 2,
        },
        "content": {"drafts": 3, "scheduled": 2, "posted": 1, "attention": 2},
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
    assert r.json()["data"]["outreach"]["projects"] == 1
    assert r.json()["data"]["seo"]["pages"] == 3

    r = await client.get("/api/v1/stats", headers={"x-meelu-site": second["id"]})
    assert r.json() == {"data": EMPTY}

    r = await client.get("/api/v1/stats")
    assert r.status_code == 400
    assert "has 2 websites" in r.json()["error"]["message"]
