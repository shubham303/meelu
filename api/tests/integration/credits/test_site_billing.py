from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from src.core.database import unit_of_work
from src.credits.billing import site_billing_service
from tests.conftest import signup


async def add_site(client, domain="example.com", name="Example"):
    r = await client.post("/api/v1/sites", json={"domain": domain, "name": name})
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def balance_usd(client):
    r = await client.get("/api/v1/credits")
    assert r.status_code == 200, r.text
    return r.json()["data"]["balanceUsd"]


async def set_balance(user_id, usd):
    async with unit_of_work() as db:
        await db.execute(
            text("UPDATE credit_account SET balance_micros = :m WHERE user_id = :u"),
            {"m": round(usd * 1_000_000), "u": user_id},
        )


async def age_billing(site_id, hours):
    async with unit_of_work() as db:
        await db.execute(
            text("UPDATE site_billing SET last_charged_at = :t WHERE site_id = :s"),
            {"t": datetime.now(UTC) - timedelta(hours=hours), "s": site_id},
        )


async def make_operator(user_id):
    async with unit_of_work() as db:
        await db.execute(
            text('UPDATE "user" SET is_superuser = true WHERE id = :u'), {"u": user_id}
        )


async def user_id_of(client):
    r = await client.get("/api/auth/me")
    return r.json()["data"]["id"]


async def test_adding_a_site_charges_the_first_day(client, email):
    await signup(client, email)
    before = await balance_usd(client)

    site = await add_site(client)

    assert site["status"] == "active"
    assert await balance_usd(client) == pytest.approx(before - 0.4)

    r = await client.get(f"/api/v1/credits/sites/{site['id']}")
    assert r.status_code == 200, r.text
    state = r.json()["data"]
    assert state["chargeCount"] == 1
    assert state["chargedMicros"] == 400_000
    assert state["lastChargedAt"] is not None
    assert state["nextChargeAt"] is not None


async def test_sweep_charges_once_per_day(client, email):
    await signup(client, email)
    site = await add_site(client)
    after_create = await balance_usd(client)

    result = await site_billing_service.sweep()
    assert result.charged == 0
    assert await balance_usd(client) == pytest.approx(after_create)

    await age_billing(site["id"], 25)
    result = await site_billing_service.sweep()
    assert result.charged == 1
    assert result.disabled == 0
    assert await balance_usd(client) == pytest.approx(after_create - 0.4)


async def test_site_is_disabled_when_credits_run_out_and_revives_on_top_up(client, email):
    await signup(client, email)
    site = await add_site(client)
    user_id = await user_id_of(client)

    await set_balance(user_id, 0.1)
    await age_billing(site["id"], 25)

    result = await site_billing_service.sweep()
    assert result.disabled == 1
    assert result.charged == 0

    r = await client.get("/api/v1/site/pages")
    assert r.status_code == 402
    assert r.json()["error"]["code"] == "site_disabled"

    r = await client.get("/api/v1/sites")
    assert r.status_code == 200
    assert r.json()["data"][0]["status"] == "disabled"

    # the failed charge never advanced the clock, so the next sweep retries it
    await make_operator(user_id)
    r = await client.post("/api/v1/credits/grant", json={"amountUsd": 5})
    assert r.status_code == 200, r.text

    result = await site_billing_service.sweep()
    assert result.charged == 1
    assert result.reactivated == 1

    r = await client.get(f"/api/v1/sites/{site['id']}")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "active"


async def test_disabled_site_blocks_site_scoped_routes(client, email):
    await signup(client, email)
    site = await add_site(client)
    user_id = await user_id_of(client)

    await set_balance(user_id, 0)
    await age_billing(site["id"], 25)
    await site_billing_service.sweep()

    r = await client.get("/api/v1/site/pages")
    assert r.status_code == 402
    assert r.json()["error"]["code"] == "site_disabled"

    # the credits surface itself stays reachable so the user can pay
    assert await balance_usd(client) == pytest.approx(0)
    r = await client.get(f"/api/v1/credits/sites/{site['id']}")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "disabled"


async def test_vendor_calls_need_the_minimum_balance(client, email):
    from src.credits.service import InsufficientCreditsError, credit_service

    await signup(client, email)
    user_id = await user_id_of(client)

    await set_balance(user_id, 0.19)
    async with unit_of_work() as db:
        with pytest.raises(InsufficientCreditsError) as caught:
            await credit_service.require_balance(db, user_id)
    assert caught.value.floor_micros == 200_000
    assert "minimum" in str(caught.value)

    await set_balance(user_id, 0.2)
    async with unit_of_work() as db:
        assert await credit_service.require_balance(db, user_id) == 200_000
