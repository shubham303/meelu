import pytest

from src.agent.context import AgentContext, require_site, reset_context, set_context
from src.credits.billing import site_billing_service
from tests.conftest import signup
from tests.integration.credits.test_site_billing import (
    add_site,
    age_billing,
    set_balance,
    user_id_of,
)


async def disable(client, site_id):
    await set_balance(await user_id_of(client), 0)
    await age_billing(site_id, 25)
    await site_billing_service.sweep()


async def test_a_disabled_site_can_still_be_seen_and_paid_for(client, email):
    await signup(client, email)
    site = await add_site(client)
    await disable(client, site["id"])

    for path in ("/api/v1/credits", "/api/v1/credits/ledger", "/api/v1/sites", "/api/v1/profile"):
        r = await client.get(path)
        assert r.status_code == 200, f"{path} -> {r.status_code} {r.text}"

    r = await client.get(f"/api/v1/sites/{site['id']}")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "disabled"

    r = await client.get(f"/api/v1/credits/sites/{site['id']}")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "disabled"


async def test_a_disabled_site_still_shows_its_own_record_and_stats(client, email):
    await signup(client, email)
    site = await add_site(client)
    await disable(client, site["id"])

    r = await client.get("/api/v1/site")
    assert r.status_code == 200, r.text
    assert r.json()["data"]["id"] == site["id"]

    r = await client.get("/api/v1/stats")
    assert r.status_code == 200, r.text


async def test_a_disabled_site_can_still_be_deleted_both_ways(client, email):
    await signup(client, email)
    site = await add_site(client, "one.com", "One")
    await disable(client, site["id"])

    r = await client.delete("/api/v1/site")
    assert r.status_code == 200, r.text

    second = await add_site(client, "two.com", "Two")
    await disable(client, second["id"])
    r = await client.delete(f"/api/v1/sites/{second['id']}")
    assert r.status_code == 200, r.text


async def test_a_disabled_site_blocks_the_desks_but_not_crawl_cleanup(client, email):
    await signup(client, email)
    site = await add_site(client)
    await disable(client, site["id"])

    for path in ("/api/v1/site/pages", "/api/v1/notes", "/api/v1/content/pieces"):
        r = await client.get(path)
        assert r.status_code == 402, f"{path} -> {r.status_code}"
        assert r.json()["error"]["code"] == "site_disabled"

    r = await client.post("/api/v1/site/crawl-jobs", json={})
    assert r.status_code == 402

    r = await client.get("/api/v1/site/crawl-jobs")
    assert r.status_code == 200, r.text
    r = await client.post("/api/v1/site/crawl-jobs/reap", json={"staleMs": 60_000})
    assert r.status_code == 200, r.text


async def test_each_site_is_gated_on_its_own(client, email):
    await signup(client, email)
    broke = await add_site(client, "broke.com", "Broke")
    payer = await add_site(client, "payer.com", "Payer")

    await set_balance(await user_id_of(client), 0.1)
    await age_billing(broke["id"], 25)
    await site_billing_service.sweep()

    r = await client.get("/api/v1/site/pages", headers={"x-meelu-site": broke["id"]})
    assert r.status_code == 402
    r = await client.get("/api/v1/site/pages", headers={"x-meelu-site": payer["id"]})
    assert r.status_code == 200, r.text


def test_agent_tools_refuse_a_disabled_site():
    ctx = AgentContext(
        user_id="user_x",
        site_id="site_x",
        site_domain="example.com",
        site_status="disabled",
        role="r",
        schema="s",
        api_key="k",
    )
    token = set_context(ctx)
    try:
        with pytest.raises(ValueError, match="credits"):
            require_site()
    finally:
        reset_context(token)


def test_paid_agent_tools_use_the_gate():
    from src.providers.seo_data import tools

    ctx = AgentContext(
        user_id="user_x",
        site_id="site_x",
        site_domain="example.com",
        site_status="disabled",
        role="r",
        schema="s",
        api_key="k",
    )
    token = set_context(ctx)
    try:
        with pytest.raises(ValueError, match="credits"):
            tools.caller()
    finally:
        reset_context(token)
