from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from src.core.database import unit_of_work
from src.providers.models.provider_cache import ProviderCache
from src.providers.registry import Caller, VendorResponse
from src.providers.seo_data.dataforseo import DataForSeoAdapter
from src.providers.seo_data.service import SeoDataProvider
from tests.conftest import signup

COMPETITORS_PATH = "/v3/dataforseo_labs/google/competitors_domain/live"

ENVELOPE = {
    "status_code": 20000,
    "cost": 0.01,
    "tasks": [
        {
            "status_code": 20000,
            "cost": 0.01,
            "result": [
                {"items": [{"domain": "rival.example", "intersections": 40, "avg_position": 7.5}]}
            ],
        }
    ],
}


class RecordingDataForSeo(DataForSeoAdapter):
    def __init__(self):
        self.sent: list[dict] = []

    def configured(self) -> bool:
        return True

    async def send(self, query: dict) -> VendorResponse:
        self.sent.append(query)
        return VendorResponse(ENVELOPE, 10_000)


async def user_id_of(client, email):
    await signup(client, email)
    return (await client.get("/api/auth/me")).json()["data"]["id"]


async def test_a_response_is_stored_raw_under_its_query_fingerprint(client, email):
    caller = Caller(user_id=await user_id_of(client, email))
    adapter = RecordingDataForSeo()
    facade = SeoDataProvider([adapter])

    async with unit_of_work() as db:
        first = await facade.rival_domains(db, caller, "https://Cache-Test.example/")
    async with unit_of_work() as db:
        second = await facade.rival_domains(db, caller, "cache-test.example")

    assert len(adapter.sent) == 1
    assert adapter.sent[0]["endpoint"] == COMPETITORS_PATH
    assert adapter.sent[0]["task"]["target"] == "cache-test.example"
    assert (
        first
        == second
        == {"rivals": [{"domain": "rival.example", "intersections": 40, "avgPosition": 7.5}]}
    )

    async with unit_of_work() as db:
        [row] = (
            await db.scalars(
                select(ProviderCache).where(
                    ProviderCache.capability == "domains.competitors",
                    ProviderCache.request == adapter.sent[0],
                )
            )
        ).all()
    assert row.provider == "dataforseo"
    assert row.response == ENVELOPE
    assert row.vendor_cost_micros == 10_000
    assert row.expires_at - row.fetched_at == timedelta(days=7)
    assert row.expires_at > datetime.now(UTC) + timedelta(days=6)


async def test_a_different_query_is_a_different_fingerprint(client, email):
    caller = Caller(user_id=await user_id_of(client, email))
    adapter = RecordingDataForSeo()
    facade = SeoDataProvider([adapter])

    async with unit_of_work() as db:
        await facade.rival_domains(db, caller, "fingerprint.example", limit=10)
        await facade.rival_domains(db, caller, "fingerprint.example", limit=20)
        await facade.rival_domains(db, caller, "fingerprint.example", location_code=2356)
        await facade.rival_domains(db, caller, "fingerprint.example", limit=20)

    assert [(q["task"]["limit"], q["task"]["location_code"]) for q in adapter.sent] == [
        (10, 2840),
        (20, 2840),
        (10, 2356),
    ]
