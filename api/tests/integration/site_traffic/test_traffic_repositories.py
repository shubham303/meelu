from src.core.database import unit_of_work
from src.site_traffic.repositories.site_traffic_channels_daily import site_traffic_channels_dailies
from src.site_traffic.repositories.site_traffic_landing_daily import site_traffic_landing_dailies
from tests.conftest import signup
from tests.integration.site_traffic.test_traffic import DAY_A, DAY_B, make_site, seed_all


async def test_landing_sessions_and_channel_days(client, email):
    await signup(client, email)
    site = await make_site(client)
    await seed_all(client)

    async with unit_of_work() as db:
        by_path = await site_traffic_landing_dailies.sessions_by_path(db, site["id"], 90)
        organic = await site_traffic_channels_dailies.daily_sessions_for_channel(
            db, site["id"], "Organic Search", DAY_B, 28
        )
        none = await site_traffic_landing_dailies.sessions_by_path(db, site["id"], 1)

    assert by_path == {"/pricing": 100, "/blog/beans": 25}
    assert set(organic) == {DAY_A, DAY_B}
    assert none == {}
