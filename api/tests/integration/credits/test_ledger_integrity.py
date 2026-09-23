import asyncio

import pytest
from sqlalchemy import text

from src.core.database import unit_of_work
from src.credits import repository as repo
from tests.conftest import signup
from tests.integration.credits.test_site_billing import (
    add_site,
    balance_usd,
    make_operator,
    user_id_of,
)


async def ledger_sum_usd(user_id):
    async with unit_of_work() as db:
        row = await db.execute(
            text("SELECT COALESCE(SUM(delta_micros), 0) FROM credit_ledger WHERE user_id = :u"),
            {"u": user_id},
        )
        return int(row.scalar_one()) / 1_000_000


async def stored_balance_usd(user_id):
    async with unit_of_work() as db:
        return await repo.balance(db, user_id) / 1_000_000


async def test_the_balance_always_equals_the_sum_of_the_ledger(client, email):
    await signup(client, email)
    user_id = await user_id_of(client)
    await make_operator(user_id)

    await add_site(client, "one.com", "One")
    await add_site(client, "two.com", "Two")
    for amount in (1.25, 0.5, 3):
        r = await client.post("/api/v1/credits/grant", json={"amountUsd": amount})
        assert r.status_code == 200, r.text

    assert await stored_balance_usd(user_id) == pytest.approx(await ledger_sum_usd(user_id))
    assert await balance_usd(client) == pytest.approx(await ledger_sum_usd(user_id))


async def test_concurrent_charges_keep_the_ledger_consistent(client, email):
    await signup(client, email)
    user_id = await user_id_of(client)

    async def charge(n):
        async with unit_of_work() as db:
            await repo.apply_delta(db, user_id, -10_000, "usage", f"concurrent {n}")

    await asyncio.gather(*(charge(n) for n in range(20)))

    assert await stored_balance_usd(user_id) == pytest.approx(5.0 - 0.2)
    assert await stored_balance_usd(user_id) == pytest.approx(await ledger_sum_usd(user_id))

    async with unit_of_work() as db:
        rows = await db.execute(
            text(
                "SELECT COUNT(*), COUNT(DISTINCT balance_after_micros) FROM credit_ledger "
                "WHERE user_id = :u AND note LIKE 'concurrent%'"
            ),
            {"u": user_id},
        )
        total, distinct = rows.one()
    assert total == 20
    assert distinct == 20, "every ledger row must show a distinct running balance"


async def test_every_ledger_entry_explains_itself(client, email):
    await signup(client, email)
    await add_site(client, "example.com", "Example")

    r = await client.get("/api/v1/credits/ledger?page_size=50")
    entries = r.json()["data"]
    assert entries, "the ledger should not be empty"
    for entry in entries:
        assert entry["kind"]
        assert entry["note"], f"{entry['kind']} entry has no explanation"
        assert entry["deltaUsd"] != 0


async def test_amounts_are_exact_in_micros(client, email):
    await signup(client, email)
    user_id = await user_id_of(client)

    for _ in range(10):
        await add_site(client, f"site{_}.com", f"Site {_}")

    async with unit_of_work() as db:
        row = await db.execute(
            text(
                "SELECT COALESCE(SUM(delta_micros), 0) FROM credit_ledger "
                "WHERE user_id = :u AND kind = 'site_day'"
            ),
            {"u": user_id},
        )
        assert int(row.scalar_one()) == -4_000_000
