from tests.conftest import signup


async def setup_site(client, email, domain="example.com"):
    await signup(client, email)
    r = await client.post("/api/v1/sites", json={"domain": domain, "name": "Example"})
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def create_chat(client, title, headers=None):
    r = await client.post("/api/v1/analytics/chats", json={"title": title}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_chats_lifecycle(client, email):
    await setup_site(client, email)

    r = await client.post("/api/v1/analytics/chats", json={"title": "   "})
    assert r.status_code == 400

    long = await create_chat(client, "Why did   clicks drop " + "x" * 200)
    assert len(long["title"]) == 80
    assert long["title"].endswith("…")
    assert "sdkSessionId" not in long

    first = await create_chat(client, "Clicks by country")
    second = await create_chat(client, "Top landing pages")

    r = await client.get("/api/v1/analytics/chats", params={"page_size": 2})
    body = r.json()
    assert [c["id"] for c in body["data"]] == [second["id"], first["id"]]
    assert set(body["data"][0]) == {"id", "title", "updatedAt"}
    assert body["pagination"]["total"] == 3
    assert body["pagination"]["has_next"] is True

    r = await client.post(
        f"/api/v1/analytics/chats/{first['id']}/messages",
        json={
            "messages": [
                {"role": "user", "text": "Which country grew?"},
                {"role": "assistant", "text": "India, by 40%."},
            ]
        },
    )
    assert r.status_code == 201, r.text
    assert [m["role"] for m in r.json()["data"]] == ["user", "assistant"]

    r = await client.get("/api/v1/analytics/chats", params={"page_size": 1})
    assert r.json()["data"][0]["id"] == first["id"], "a new message moves the chat to the top"

    r = await client.post(
        f"/api/v1/analytics/chats/{first['id']}/messages",
        json={"messages": [{"role": "system", "text": "x"}]},
    )
    assert r.status_code == 400

    r = await client.get(f"/api/v1/analytics/chats/{first['id']}/messages", params={"page_size": 1})
    page = r.json()
    assert [m["text"] for m in page["data"]] == ["India, by 40%."]
    assert page["pagination"]["has_next"] is True

    r = await client.put(f"/api/v1/analytics/chats/{first['id']}", json={})
    assert r.status_code == 400
    r = await client.put(
        f"/api/v1/analytics/chats/{first['id']}",
        json={"title": "Country growth", "sdkSessionId": "sess-1"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["sdkSessionId"] == "sess-1"
    r = await client.get(f"/api/v1/analytics/chats/{first['id']}")
    assert r.json()["data"]["title"] == "Country growth"

    r = await client.delete(f"/api/v1/analytics/chats/{first['id']}")
    assert r.json()["data"] == {"id": first["id"], "deleted": True}
    r = await client.get(f"/api/v1/analytics/chats/{first['id']}/messages")
    assert r.status_code == 404


async def test_chats_belong_to_one_site(client, email):
    one = await setup_site(client, email)
    chat = await create_chat(client, "Only on site one")
    r = await client.post("/api/v1/sites", json={"domain": "other.com", "name": "Other"})
    other = r.json()["data"]

    headers = {"x-meelu-site": other["id"]}
    r = await client.get("/api/v1/analytics/chats", headers=headers)
    assert r.json()["data"] == []
    r = await client.get(f"/api/v1/analytics/chats/{chat['id']}", headers=headers)
    assert r.status_code == 404

    r = await client.get("/api/v1/analytics/chats", headers={"x-meelu-site": one["id"]})
    assert [c["id"] for c in r.json()["data"]] == [chat["id"]]
