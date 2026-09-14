from sqlalchemy import select
from src.prompts.defaults import DEFAULT_PROMPTS, seed_default_prompts

from src.core.database import unit_of_work
from src.profile.models.user import User
from tests.conftest import signup


async def user_id_for(email):
    async with unit_of_work() as db:
        result = await db.execute(select(User.id).where(User.email == email))
        return result.scalar_one()


async def test_seed_default_prompts(client, email):
    await signup(client, email)
    user_id = await user_id_for(email)

    async with unit_of_work() as db:
        await seed_default_prompts(db, user_id, None)

    r = await client.get("/api/v1/prompts")
    assert r.status_code == 200
    prompts = r.json()["data"]
    assert len(prompts) == len(DEFAULT_PROMPTS) == 6
    assert all(p["seeded"] is True for p in prompts)

    by_key = {p["key"]: p for p in prompts}
    assert set(by_key) == {d["key"] for d in DEFAULT_PROMPTS}
    for default in DEFAULT_PROMPTS:
        assert by_key[default["key"]]["title"] == default["title"]
        assert by_key[default["key"]]["body"] == default["body"]

    async with unit_of_work() as db:
        await seed_default_prompts(db, user_id, None)

    r = await client.get("/api/v1/prompts")
    assert len(r.json()["data"]) == 6


async def test_seed_skips_a_user_who_already_has_prompts(client, email):
    await signup(client, email)
    user_id = await user_id_for(email)

    r = await client.post("/api/v1/prompts", json={"title": "Mine", "body": "Only one."})
    assert r.status_code == 201

    async with unit_of_work() as db:
        await seed_default_prompts(db, user_id, None)

    r = await client.get("/api/v1/prompts")
    prompts = r.json()["data"]
    assert len(prompts) == 1
    assert prompts[0]["seeded"] is False
