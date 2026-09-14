from tests.conftest import signup

PROMPT_FIELDS = {"id", "key", "title", "body", "seeded", "createdAt", "updatedAt"}


async def test_prompts_crud(client, email):
    await signup(client, email)

    r = await client.get("/api/v1/prompts")
    assert r.status_code == 200
    assert r.json() == {"data": []}

    r = await client.post("/api/v1/prompts", json={"title": "Blog Intro — Hook"})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Missing required field(s): body"}}

    r = await client.post(
        "/api/v1/prompts", json={"title": "  Blog Intro — Hook  ", "body": "Open with a fact."}
    )
    assert r.status_code == 201, r.text
    created = r.json()["data"]
    assert set(created) == PROMPT_FIELDS
    assert created["key"] == "blog-intro-hook"
    assert created["title"] == "Blog Intro — Hook"
    assert created["body"] == "Open with a fact."
    assert created["seeded"] is False
    assert created["id"].startswith("prm_")

    r = await client.post("/api/v1/prompts", json={"title": "blog intro hook", "body": "Again."})
    assert r.status_code == 409
    assert r.json() == {
        "error": {
            "message": "You already have a prompt at /blog-intro-hook. "
            "Pick a different name, or edit that one instead."
        }
    }

    r = await client.post("/api/v1/prompts", json={"title": "———", "body": "No slug."})
    assert r.status_code == 400
    assert r.json() == {
        "error": {
            "message": "Could not derive a slash command from that title — set `key` directly."
        }
    }

    r = await client.post("/api/v1/prompts", json={"title": "x" * 81, "body": "Too long."})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Title is too long — 80 characters at most."}}

    r = await client.post("/api/v1/prompts", json={"title": "Fine", "body": "y" * 4001})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Body is too long — 4000 characters at most."}}

    r = await client.post(
        "/api/v1/prompts", json={"key": "Meta Description!", "title": "Meta", "body": "160 chars."}
    )
    assert r.status_code == 201
    second = r.json()["data"]
    assert second["key"] == "meta-description"

    r = await client.get("/api/v1/prompts")
    prompts = r.json()["data"]
    assert len(prompts) == 2
    assert prompts[0]["id"] == second["id"]

    r = await client.get(f"/api/v1/prompts/{created['id']}")
    assert r.status_code == 200
    assert r.json()["data"]["id"] == created["id"]

    r = await client.get("/api/v1/prompts/prm_missing")
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "Not found"}}

    r = await client.put(
        f"/api/v1/prompts/{created['id']}",
        json={"title": "Blog Opener", "body": "Lead with a number.", "key": "blog opener"},
    )
    assert r.status_code == 200
    updated = r.json()["data"]
    assert updated["title"] == "Blog Opener"
    assert updated["body"] == "Lead with a number."
    assert updated["key"] == "blog-opener"

    r = await client.put(f"/api/v1/prompts/{created['id']}", json={"title": "   "})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "title cannot be empty."}}

    r = await client.put(f"/api/v1/prompts/{created['id']}", json={"body": "  "})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "body cannot be empty."}}

    r = await client.put(f"/api/v1/prompts/{created['id']}", json={"key": "meta-description"})
    assert r.status_code == 409
    assert r.json() == {"error": {"message": "You already have a prompt at /meta-description."}}

    r = await client.put("/api/v1/prompts/prm_missing", json={"title": "Nope"})
    assert r.status_code == 404

    r = await client.delete(f"/api/v1/prompts/{created['id']}")
    assert r.status_code == 200
    assert r.json() == {"data": {"deleted": True}}

    r = await client.delete(f"/api/v1/prompts/{created['id']}")
    assert r.status_code == 404

    r = await client.get("/api/v1/prompts")
    assert len(r.json()["data"]) == 1


async def test_prompts_are_scoped_to_their_user(client, email):
    await signup(client, email)
    r = await client.post("/api/v1/prompts", json={"title": "Mine", "body": "Private."})
    assert r.status_code == 201
    mine = r.json()["data"]

    await client.post("/api/auth/logout")
    other = email.replace("user-", "other-")
    await signup(client, other)

    assert r.status_code == 201
    r = await client.get("/api/v1/prompts")
    assert r.json() == {"data": []}
    r = await client.get(f"/api/v1/prompts/{mine['id']}")
    assert r.status_code == 404
