import pytest

from tests.conftest import signup


@pytest.fixture
async def user_id(client, email):
    await signup(client, email)
    r = await client.get("/api/auth/me")
    assert r.status_code == 200, r.text
    return r.json()["data"]["id"]
