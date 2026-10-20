from tests.conftest import signup

PROMPT_FIELDS = {"id", "siteId", "surface", "label", "prompt", "createdAt", "updatedAt"}


async def make_site(client, email, domain="prompts.example"):
    r = await client.post("/api/v1/sites", json={"domain": domain, "name": "Prompts"})
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_user_prompts_crud(client, email):
    await signup(client, email)
    site = await make_site(client, email)

    r = await client.post(
        "/api/v1/user-prompts",
        json={"surface": "seo", "label": "  Weekly check ", "prompt": " Find five terms. "},
    )
    assert r.status_code == 201, r.text
    weekly = r.json()["data"]
    assert set(weekly) == PROMPT_FIELDS
    assert weekly["label"] == "Weekly check"
    assert weekly["prompt"] == "Find five terms."
    assert weekly["surface"] == "seo"
    assert weekly["siteId"] == site["id"]

    r = await client.post(
        "/api/v1/user-prompts",
        json={"surface": "structure", "label": "Orphans", "prompt": "Link the orphans."},
    )
    assert r.status_code == 201
    orphans = r.json()["data"]

    r = await client.post(
        "/api/v1/user-prompts",
        json={
            "surface": "structure",
            "label": "Weekly check",
            "prompt": "Same name, other surface.",
        },
    )
    assert r.status_code == 201

    r = await client.post(
        "/api/v1/user-prompts",
        json={"surface": "seo", "label": "Weekly check", "prompt": "dup"},
    )
    assert r.status_code == 409

    r = await client.post(
        "/api/v1/user-prompts", json={"surface": "email", "label": "x", "prompt": "y"}
    )
    assert r.status_code == 400
    assert (
        r.json()["error"]["message"] == 'Invalid surface "email". Allowed values: seo, structure.'
    )

    r = await client.post(
        "/api/v1/user-prompts", json={"surface": "seo", "label": "  ", "prompt": "y"}
    )
    assert r.status_code == 400

    r = await client.post(
        "/api/v1/user-prompts", json={"surface": "seo", "label": "x", "prompt": "y" * 8001}
    )
    assert r.status_code == 400

    r = await client.get("/api/v1/user-prompts")
    assert r.status_code == 200
    assert r.json()["pagination"]["total"] == 3

    r = await client.get("/api/v1/user-prompts", params={"surface": "seo"})
    assert [p["id"] for p in r.json()["data"]] == [weekly["id"]]

    r = await client.get(
        "/api/v1/user-prompts", params={"surface": "structure", "contains": "orphan"}
    )
    assert [p["id"] for p in r.json()["data"]] == [orphans["id"]]

    r = await client.get(f"/api/v1/user-prompts/{weekly['id']}")
    assert r.status_code == 200
    assert r.json()["data"]["id"] == weekly["id"]

    r = await client.get("/api/v1/user-prompts/prompt_missing")
    assert r.status_code == 404

    r = await client.patch(
        f"/api/v1/user-prompts/{weekly['id']}", json={"prompt": "Find ten terms."}
    )
    assert r.status_code == 200
    updated = r.json()["data"]
    assert updated["prompt"] == "Find ten terms."
    assert updated["label"] == "Weekly check"

    r = await client.patch(f"/api/v1/user-prompts/{weekly['id']}", json={})
    assert r.status_code == 400

    r = await client.patch(f"/api/v1/user-prompts/{orphans['id']}", json={"label": "Weekly check"})
    assert r.status_code == 409

    r = await client.patch(f"/api/v1/user-prompts/{weekly['id']}", json={"label": "Weekly check"})
    assert r.status_code == 200

    r = await client.delete(f"/api/v1/user-prompts/{weekly['id']}")
    assert r.status_code == 200
    assert r.json()["data"] == {"id": weekly["id"], "deleted": True}

    r = await client.get(f"/api/v1/user-prompts/{weekly['id']}")
    assert r.status_code == 404


async def test_user_prompts_stay_on_their_site(client, email):
    await signup(client, email)
    first = await make_site(client, email, "first.example")
    second = await make_site(client, email, "second.example")

    r = await client.post(
        "/api/v1/user-prompts",
        json={"surface": "seo", "label": "Mine", "prompt": "Only on first."},
        headers={"x-meelu-site": first["id"]},
    )
    assert r.status_code == 201
    prompt = r.json()["data"]

    r = await client.get("/api/v1/user-prompts", headers={"x-meelu-site": second["id"]})
    assert r.json()["pagination"]["total"] == 0

    r = await client.get(
        f"/api/v1/user-prompts/{prompt['id']}", headers={"x-meelu-site": second["id"]}
    )
    assert r.status_code == 404
