import asyncio

import pytest
from sqlalchemy import text

from src.core.database import unit_of_work
from src.credits import billing
from tests.conftest import signup
from tests.integration.credits.test_site_billing import (
    add_site,
    age_billing,
    balance_usd,
    make_operator,
    set_balance,
    user_id_of,
)


async def ledger_kinds(client):
    r = await client.get("/api/v1/credits/ledger?page_size=50")
    assert r.status_code == 200, r.text
    return [(e["kind"], e["note"], e["deltaUsd"]) for e in r.json()["data"]]


async def test_a_user_cannot_grant_themselves_credits(client, email):
    await signup(client, email)
    before = await balance_usd(client)

    r = await client.post("/api/v1/credits/grant", json={"amountUsd": 1_000_000})
    assert r.status_code == 403, r.text
    assert await balance_usd(client) == pytest.approx(before)

    r = await client.post("/api/v1/credits/sweep")
    assert r.status_code == 403, r.text

    await make_operator(await user_id_of(client))
    r = await client.post("/api/v1/credits/grant", json={"amountUsd": 2})
    assert r.status_code == 200, r.text
    assert await balance_usd(client) == pytest.approx(before + 2)


async def test_re_adding_the_same_domain_the_same_day_is_not_charged_twice(client, email):
    await signup(client, email)
    start = await balance_usd(client)

    for _ in range(5):
        site = await add_site(client, "example.com", "Example")
        r = await client.delete(f"/api/v1/sites/{site['id']}")
        assert r.status_code == 200, r.text

    assert await balance_usd(client) == pytest.approx(start - 0.4)

    site = await add_site(client, "example.com", "Example")
    await age_billing(site["id"], 25)
    await billing.sweep()
    assert await balance_usd(client) == pytest.approx(start - 0.8)


async def test_a_second_domain_is_charged_separately(client, email):
    await signup(client, email)
    start = await balance_usd(client)

    await add_site(client, "one.com", "One")
    await add_site(client, "two.com", "Two")

    assert await balance_usd(client) == pytest.approx(start - 0.8)


async def test_deleting_a_site_leaves_a_ledger_entry_that_still_names_the_domain(client, email):
    await signup(client, email)
    site = await add_site(client, "example.com", "Example")

    r = await client.delete(f"/api/v1/sites/{site['id']}")
    assert r.status_code == 200, r.text

    entries = await ledger_kinds(client)
    charge = next(e for e in entries if e[0] == "site_day")
    assert "example.com" in charge[1]
    assert charge[2] == pytest.approx(-0.4)


async def test_one_broke_site_cannot_starve_the_sweep(client, email, monkeypatch):
    await signup(client, email)
    user_id = await user_id_of(client)

    monkeypatch.setattr(billing, "BATCH", 1)
    broke = await add_site(client, "broke.com", "Broke")
    payer = await add_site(client, "payer.com", "Payer")

    await set_balance(user_id, 0.4)
    await age_billing(broke["id"], 25)
    await age_billing(payer["id"], 25)

    result = await billing.sweep(limit=1)

    # the sweep must reach both, not spin on the first page forever
    assert result.considered >= 2
    r = await client.get("/api/v1/sites")
    statuses = {s["domain"]: s["status"] for s in r.json()["data"]}
    assert sorted(statuses.values()) == ["active", "disabled"]
    assert await balance_usd(client) == pytest.approx(0)


async def test_concurrent_sweeps_charge_a_site_once(client, email):
    await signup(client, email)
    site = await add_site(client)
    after_create = await balance_usd(client)
    await age_billing(site["id"], 25)

    results = await asyncio.gather(*(billing.sweep() for _ in range(4)))

    assert sum(r.charged for r in results) == 1
    assert await balance_usd(client) == pytest.approx(after_create - 0.4)


async def test_a_site_billing_row_survives_its_site(client, email):
    await signup(client, email)
    user_id = await user_id_of(client)
    site = await add_site(client, "example.com", "Example")
    await client.delete(f"/api/v1/sites/{site['id']}")

    async with unit_of_work() as db:
        row = await db.execute(
            text(
                "SELECT site_id, domain, charge_count FROM site_billing "
                "WHERE domain = 'example.com' AND user_id = :u"
            ),
            {"u": user_id},
        )
        kept = row.first()
    assert kept is not None
    assert kept.site_id is None
    assert kept.charge_count == 1
