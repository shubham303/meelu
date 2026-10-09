from datetime import timedelta

import pytest

from src.core.database import unit_of_work
from src.credits import pricing
from src.credits.service import InsufficientCreditsError
from src.providers.errors import ProviderRequestError
from src.providers.registry import Caller, ProviderAdapter, ProviderFacade, VendorResponse
from tests.conftest import signup
from tests.integration.credits.test_site_billing import balance_usd, set_balance, user_id_of


class PaidAdapter(ProviderAdapter):
    id = "paid"
    name = "Paid"
    capabilities = frozenset({"thing.get"})

    def __init__(self, cost=250_000):
        self.calls = 0
        self.cost = cost

    async def get(self, key):
        self.calls += 1
        return VendorResponse({"key": key, "n": self.calls}, self.cost)


class FreeAdapter(ProviderAdapter):
    id = "free"
    name = "Free"
    capabilities = frozenset({"thing.get"})
    charges = False

    def __init__(self, cost=0):
        self.calls = 0
        self.cost = cost

    async def get(self, key):
        self.calls += 1
        return VendorResponse({"key": key, "free": True}, self.cost)


class BrokenAdapter(ProviderAdapter):
    id = "broken"
    name = "Broken"
    capabilities = frozenset({"thing.get"})

    async def get(self, key):
        raise ProviderRequestError(self.id, 503, "vendor down")


class ThingFacade(ProviderFacade):
    domain = "things-credit"
    label = "things"

    async def get(self, db, caller, key):
        return await self.fetch(
            db,
            caller,
            "thing.get",
            lambda _: {"key": key},
            lambda a: a.get(key),
            timedelta(hours=1),
        )


async def fetch(facade, user_id, key):
    async with unit_of_work() as db:
        return await facade.get(db, Caller(user_id=user_id), key)


async def test_a_free_adapter_is_never_charged_even_with_a_price_set(client, email, monkeypatch):
    await signup(client, email)
    user_id = await user_id_of(client)
    before = await balance_usd(client)

    monkeypatch.setitem(pricing.FIXED_PRICES_MICROS, ("things-credit", "thing.get"), 500_000)
    facade = ThingFacade([FreeAdapter()])
    await fetch(facade, user_id, "k1")

    assert await balance_usd(client) == pytest.approx(before)


async def test_a_cache_hit_costs_nothing(client, email):
    await signup(client, email)
    user_id = await user_id_of(client)
    before = await balance_usd(client)

    adapter = PaidAdapter(cost=250_000)
    facade = ThingFacade([adapter])
    await fetch(facade, user_id, "cached")
    after_first = await balance_usd(client)
    assert after_first == pytest.approx(before - 0.25)

    await fetch(facade, user_id, "cached")
    assert adapter.calls == 1
    assert await balance_usd(client) == pytest.approx(after_first)


async def test_a_failed_vendor_call_costs_nothing_and_a_fallback_charges_once(client, email):
    await signup(client, email)
    user_id = await user_id_of(client)
    before = await balance_usd(client)

    paid = PaidAdapter(cost=100_000)
    facade = ThingFacade([BrokenAdapter(), paid])
    await fetch(facade, user_id, "fallback")

    assert paid.calls == 1
    assert await balance_usd(client) == pytest.approx(before - 0.1)


async def test_every_vendor_charge_is_traceable_to_a_call(client, email):
    await signup(client, email)
    user_id = await user_id_of(client)

    await fetch(ThingFacade([PaidAdapter(cost=120_000)]), user_id, "traced")

    r = await client.get("/api/v1/credits/ledger?page_size=20")
    usage = [e for e in r.json()["data"] if e["kind"] == "usage"]
    assert usage, "a vendor charge must appear in the ledger"
    assert usage[0]["providerCallId"] is not None
    assert usage[0]["note"] == "things-credit/thing.get"


async def test_a_workspace_below_the_floor_cannot_call_a_paid_vendor(client, email):
    await signup(client, email)
    user_id = await user_id_of(client)
    await set_balance(user_id, 0.19)

    adapter = PaidAdapter(cost=100_000)
    with pytest.raises(InsufficientCreditsError):
        await fetch(ThingFacade([adapter]), user_id, "blocked")

    assert adapter.calls == 0
    assert await balance_usd(client) == pytest.approx(0.19)


async def test_overdrawing_disables_the_websites_instead_of_billing_on_silently(client, email):
    from tests.integration.credits.test_site_billing import add_site

    await signup(client, email)
    user_id = await user_id_of(client)
    await add_site(client, "example.com", "Example")
    await set_balance(user_id, 0.30)

    await fetch(ThingFacade([PaidAdapter(cost=2_000_000)]), user_id, "expensive")

    assert await balance_usd(client) == pytest.approx(-1.7)
    r = await client.get("/api/v1/sites")
    assert [s["status"] for s in r.json()["data"]] == ["disabled"]
