import asyncio
import uuid

import psycopg

from src.core.database import unit_of_work
from src.core.locks import skip_if_locked
from src.social_listening.repositories.social_posts import social_posts
from tests.conftest import TEST_URL

PG_URL = TEST_URL.replace("postgresql+psycopg://", "postgresql://")


async def test_a_held_lock_is_skipped_by_the_next_worker():
    key = f"test-lock:{uuid.uuid4().hex}"
    async with skip_if_locked(key) as first:
        async with skip_if_locked(key) as second:
            assert first is True
            assert second is False
    async with skip_if_locked(key) as again:
        assert again is True


async def test_two_workers_claim_different_posts():
    run = uuid.uuid4().hex[:8]
    with psycopg.connect(PG_URL, autocommit=True) as conn:
        conn.execute("update social_post set embed_attempts = 3 where embedding is null")
        for i in range(4):
            conn.execute(
                "insert into social_post (id, post_key, platform, url, text) "
                "values (%s, %s, 'hackernews', 'https://news.ycombinator.com', 'post')",
                (f"sp_claim_{run}_{i}", f"hackernews:claim-{run}-{i}"),
            )
    first_claimed = asyncio.Event()
    release = asyncio.Event()
    claims = {}

    async def worker(name, hold):
        async with unit_of_work() as db:
            rows = await social_posts.claim_pending_embeddings(db, 3, 2)
            claims[name] = {r.id for r in rows}
            if hold:
                first_claimed.set()
                await release.wait()

    holder = asyncio.create_task(worker("a", True))
    await first_claimed.wait()
    await worker("b", False)
    release.set()
    await holder
    assert len(claims["a"]) == 2
    assert len(claims["b"]) == 2
    assert not claims["a"] & claims["b"]
