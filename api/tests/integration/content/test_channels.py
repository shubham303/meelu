from src.content.platform_seeds import PLATFORM_SEEDS, SEEDS_BY_KEY


async def test_channels_are_seeded_per_site(client, workspace):
    r = await client.get("/api/v1/content/channels")
    assert r.status_code == 200
    channels = r.json()["data"]
    assert [c["channelKey"] for c in channels] == [s.key for s in PLATFORM_SEEDS]
    twitter = next(c for c in channels if c["channelKey"] == "twitter")
    assert twitter["enabled"] is True
    assert twitter["rules"] == SEEDS_BY_KEY["twitter"].rules()
    assert twitter["label"] == "X"
    assert twitter["characterLimit"] == 280
    assert twitter["requiresMedia"] is False
    assert twitter["maxHashtags"] == 2
    assert "userId" not in twitter

    r = await client.get("/api/v1/content/channels")
    assert len(r.json()["data"]) == len(PLATFORM_SEEDS)


async def test_channel_get_update_reset(client, workspace):
    r = await client.get("/api/v1/content/channels/myspace")
    assert r.status_code == 400

    r = await client.get("/api/v1/content/channels/linkedin")
    assert r.status_code == 200
    assert r.json()["data"]["channelKey"] == "linkedin"

    r = await client.put("/api/v1/content/channels/linkedin", json={"rules": "no"})
    assert r.status_code == 400

    r = await client.put(
        "/api/v1/content/channels/linkedin",
        json={
            "rules": ["  Lead with the number.  ", "", "No hashtags."],
            "enabled": False,
        },
    )
    assert r.status_code == 200, r.text
    updated = r.json()["data"]
    assert updated["rules"] == ["Lead with the number.", "No hashtags."]
    assert updated["enabled"] is False

    r = await client.post("/api/v1/content/channels/linkedin/reset")
    assert r.status_code == 200
    reset = r.json()["data"]
    assert reset["rules"] == SEEDS_BY_KEY["linkedin"].rules()
    assert reset["enabled"] is False
