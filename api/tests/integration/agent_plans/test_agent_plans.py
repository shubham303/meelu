from src.agent_plans import service
from src.agent_plans.library import BUILTIN_PLANS
from src.core.database import unit_of_work
from tests.conftest import signup


async def sync():
    async with unit_of_work() as db:
        return await service.sync_builtins(db)


async def test_sync_is_idempotent_and_prunes_nothing_user_owned(client, email):
    first = await sync()
    second = await sync()
    assert first.synced == second.synced == len(BUILTIN_PLANS)
    assert second.pruned == 0


async def test_list_search_and_get(client, email):
    await sync()
    await signup(client, email)

    r = await client.get("/api/v1/agent-plans")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pagination"]["total"] >= len(BUILTIN_PLANS)
    assert all(p["builtin"] for p in body["data"])

    r = await client.get("/api/v1/agent-plans", params={"q": "striking distance page one"})
    hits = r.json()["data"]
    assert hits and hits[0]["slug"] == "striking-distance"

    r = await client.get("/api/v1/agent-plans/by-slug/striking-distance")
    assert r.status_code == 200
    plan = r.json()
    assert plan["builtin"] is True
    assert "site_search_daily" in plan["plan"]

    r = await client.get(f"/api/v1/agent-plans/{plan['id']}")
    assert r.json()["slug"] == "striking-distance"


async def test_user_plans_crud_and_builtin_protection(client, email):
    await sync()
    await signup(client, email)

    r = await client.post(
        "/api/v1/agent-plans",
        json={
            "slug": "my-funnel",
            "question": "How does our signup funnel convert?",
            "plan": "SELECT 1;",
        },
    )
    assert r.status_code == 201, r.text
    created = r.json()
    assert created["builtin"] is False

    r = await client.post(
        "/api/v1/agent-plans",
        json={"slug": "my-funnel", "question": "dup", "plan": "SELECT 2;"},
    )
    assert r.status_code == 409

    r = await client.post(
        "/api/v1/agent-plans", json={"slug": "Bad Slug", "question": "x", "plan": "y"}
    )
    assert r.status_code == 400

    r = await client.patch(f"/api/v1/agent-plans/{created['id']}", json={"plan": "SELECT 3;"})
    assert r.status_code == 200
    assert r.json()["plan"] == "SELECT 3;"

    r = await client.get("/api/v1/agent-plans", params={"q": "signup funnel convert"})
    assert [h["slug"] for h in r.json()["data"]][:1] == ["my-funnel"]

    r = await client.get("/api/v1/agent-plans/by-slug/striking-distance")
    builtin_id = r.json()["id"]
    r = await client.patch(f"/api/v1/agent-plans/{builtin_id}", json={"plan": "nope"})
    assert r.status_code == 403
    r = await client.delete(f"/api/v1/agent-plans/{builtin_id}")
    assert r.status_code == 403

    r = await client.delete(f"/api/v1/agent-plans/{created['id']}")
    assert r.status_code == 200
    r = await client.get(f"/api/v1/agent-plans/{created['id']}")
    assert r.status_code == 404

    assert (await sync()).pruned == 0


async def test_user_plans_are_private(client, email):
    await sync()
    await signup(client, email)
    r = await client.post(
        "/api/v1/agent-plans",
        json={"slug": "private-one", "question": "private?", "plan": "SELECT 1;"},
    )
    assert r.status_code == 201

    await client.post("/api/auth/logout")
    await signup(client, f"other-{email}")
    r = await client.get("/api/v1/agent-plans/by-slug/private-one")
    assert r.status_code == 404
    r = await client.post(
        "/api/v1/agent-plans",
        json={"slug": "private-one", "question": "mine", "plan": "SELECT 1;"},
    )
    assert r.status_code == 201
