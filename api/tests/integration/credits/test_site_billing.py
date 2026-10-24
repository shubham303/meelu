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
    assert await balance_usd(client) == pytest.approx(before - 0.5)

    r = await client.get(f"/api/v1/credits/sites/{site['id']}")
    assert r.status_code == 200, r.text
    state = r.json()["data"]
    assert state["chargeCount"] == 1
    assert state["chargedMicros"] == 500_000
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
    assert await balance_usd(client) == pytest.approx(after_create - 0.5)


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
    paused = r.json()["data"][0]
    assert paused["status"] == "disabled"
    assert paused["pausedAt"] is not None

    await make_operator(user_id)
    r = await client.post("/api/v1/credits/grant", json={"amountUsd": 5})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["balanceUsd"] == pytest.approx(5.1 - 0.5)

    r = await client.get(f"/api/v1/sites/{site['id']}")
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "active"
    assert r.json()["data"].get("pausedAt") is None

    r = await client.get("/api/v1/site/pages")
    assert r.status_code == 200, r.text

    result = await site_billing_service.sweep()
    assert result.charged == 0


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


async def test_pause_time_survives_later_sweeps(client, email):
    await signup(client, email)
    site = await add_site(client)
    user_id = await user_id_of(client)

    await set_balance(user_id, 0)
    await age_billing(site["id"], 25)
    await site_billing_service.sweep()
    first = (await client.get(f"/api/v1/sites/{site['id']}")).json()["data"]["pausedAt"]

    await site_billing_service.sweep()
    again = (await client.get(f"/api/v1/sites/{site['id']}")).json()["data"]["pausedAt"]
    assert first is not None
    assert again == first


async def test_overdrawn_sites_resume_without_a_second_charge(client, email):
    from src.credits.service import credit_service

    await signup(client, email)
    site = await add_site(client)
    user_id = await user_id_of(client)

    await set_balance(user_id, 0.25)
    async with unit_of_work() as db:
        await credit_service.charge_vendor_call(db, user_id, "seo_data", "test", 500_000, None)
    r = await client.get(f"/api/v1/sites/{site['id']}")
    assert r.json()["data"]["status"] == "disabled"
    assert r.json()["data"]["pausedAt"] is not None

    await make_operator(user_id)
    r = await client.post("/api/v1/credits/grant", json={"amountUsd": 0.1})
    assert r.status_code == 200, r.text
    r = await client.get(f"/api/v1/sites/{site['id']}")
    assert r.json()["data"]["status"] == "disabled"

    r = await client.post("/api/v1/credits/grant", json={"amountUsd": 1})
    assert r.status_code == 200, r.text
    assert r.json()["data"]["balanceUsd"] == pytest.approx(0.85)
    r = await client.get(f"/api/v1/sites/{site['id']}")
    assert r.json()["data"]["status"] == "active"
    assert r.json()["data"].get("pausedAt") is None


async def test_top_up_without_enough_for_a_day_keeps_the_site_paused(client, email):
    await signup(client, email)
    site = await add_site(client)
    user_id = await user_id_of(client)

    await set_balance(user_id, 0)
    await age_billing(site["id"], 25)
    await site_billing_service.sweep()

    await make_operator(user_id)
    r = await client.post("/api/v1/credits/grant", json={"amountUsd": 0.1})
    assert r.status_code == 200, r.text
    r = await client.get(f"/api/v1/sites/{site['id']}")
    assert r.json()["data"]["status"] == "disabled"
    assert await balance_usd(client) == pytest.approx(0.1)


async def test_top_up_resumes_sites_in_order_until_credits_run_out(client, email):
    await signup(client, email)
    first = await add_site(client, "one.example", "One")
    user_id = await user_id_of(client)
    await set_balance(user_id, 1)
    second = await add_site(client, "two.example", "Two")

    await set_balance(user_id, 0)
    await age_billing(first["id"], 25)
    await age_billing(second["id"], 25)
    await site_billing_service.sweep()

    await make_operator(user_id)
    r = await client.post("/api/v1/credits/grant", json={"amountUsd": 0.75})
    assert r.status_code == 200, r.text
    states = {s["id"]: s["status"] for s in (await client.get("/api/v1/sites")).json()["data"]}
    assert states == {first["id"]: "active", second["id"]: "disabled"}


async def test_purge_deletes_sites_paused_for_thirty_days(client, email):
    from src.sites.cron import purge

    await signup(client, email)
    old = await add_site(client, "old.example", "Old")
    user_id = await user_id_of(client)
    await set_balance(user_id, 2)
    recent = await add_site(client, "recent.example", "Recent")
    active = await add_site(client, "active.example", "Active")

    async with unit_of_work() as db:
        await db.execute(
            text("UPDATE site SET status = 'disabled', paused_at = :t WHERE id = :s"),
            {"t": datetime.now(UTC) - timedelta(days=30, minutes=1), "s": old["id"]},
        )
        await db.execute(
            text("UPDATE site SET status = 'disabled', paused_at = :t WHERE id = :s"),
            {"t": datetime.now(UTC) - timedelta(days=29), "s": recent["id"]},
        )

    await purge()

    ids = {s["id"] for s in (await client.get("/api/v1/sites")).json()["data"]}
    assert ids == {recent["id"], active["id"]}
    r = await client.get(f"/api/v1/sites/{old['id']}")
    assert r.status_code == 404


async def test_paid_sites_resume_even_when_an_unpaid_one_cannot_be_charged(client, email):
    from src.credits.service import credit_service

    await signup(client, email)
    user_id = await user_id_of(client)
    await set_balance(user_id, 2)
    first = await add_site(client, "a.example", "A")
    second = await add_site(client, "b.example", "B")

    await set_balance(user_id, 0.05)
    async with unit_of_work() as db:
        await credit_service.charge_vendor_call(db, user_id, "seo_data", "test", 100_000, None)
    await age_billing(first["id"], 25)

    await make_operator(user_id)
    r = await client.post("/api/v1/credits/grant", json={"amountUsd": 0.3})
    assert r.status_code == 200, r.text

    states = {s["id"]: s["status"] for s in (await client.get("/api/v1/sites")).json()["data"]}
    assert states == {first["id"]: "disabled", second["id"]: "active"}


async def test_the_first_site_is_free_for_the_first_day(client, email):
    await signup(client, email, credits=0, trial=True)
    user_id = await user_id_of(client)

    first = await add_site(client, "first.com", "First")
    assert first["status"] == "active"
    assert await balance_usd(client) == 0

    second = await add_site(client, "second.com", "Second")
    assert second["status"] == "disabled"

    await age_billing(first["id"], 25)
    await site_billing_service.sweep()
    r = await client.get(f"/api/v1/credits/sites/{first['id']}")
    assert r.json()["data"]["status"] == "active"
    assert r.json()["data"]["chargeCount"] == 2
    assert await balance_usd(client) == 0

    async with unit_of_work() as db:
        await db.execute(
            text("UPDATE \"user\" SET created_at = now() - interval '2 days' WHERE id = :u"),
            {"u": user_id},
        )
    await age_billing(first["id"], 25)
    await site_billing_service.sweep()
    r = await client.get(f"/api/v1/credits/sites/{first['id']}")
    assert r.json()["data"]["status"] == "disabled"


async def test_paid_calls_need_credits_during_the_trial(client, email):
    from src.credits.service import InsufficientCreditsError, credit_service

    await signup(client, email, credits=0, trial=True)
    user_id = await user_id_of(client)

    async with unit_of_work() as db:
        with pytest.raises(InsufficientCreditsError) as caught:
            await credit_service.require_balance(db, user_id)
    assert "Connections" in str(caught.value)


async def test_sites_after_the_fifth_cost_half(client, email):
    await signup(client, email, credits=10)

    added = [await add_site(client, f"tier{i}.com", f"Tier {i}") for i in range(7)]

    assert await balance_usd(client) == pytest.approx(10 - 5 * 0.5 - 2 * 0.25)
    prices = []
    for site in added:
        r = await client.get(f"/api/v1/credits/sites/{site['id']}")
        prices.append(r.json()["data"]["dailyPriceMicros"])
    assert prices == [500_000] * 5 + [250_000] * 2
