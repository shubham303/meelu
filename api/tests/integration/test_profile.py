from tests.conftest import signup


async def test_profile_lifecycle(client, email):
    await signup(client, email, name="Grace Hopper")

    profile_id = (await client.get("/api/v1/profile")).json()["data"]["id"]
    r = await client.delete("/api/v1/profile")
    assert r.status_code == 200
    assert r.json() == {"data": {"id": profile_id, "deleted": True}}

    r = await client.get("/api/v1/profile")
    assert r.status_code == 200
    assert r.json() == {"data": None}

    r = await client.patch("/api/v1/profile", json={"company": "Navy"})
    assert r.status_code == 404
    assert r.json() == {
        "error": {"message": "No profile yet — PUT /api/v1/profile with fullName first."}
    }

    r = await client.put("/api/v1/profile", json={"company": "Navy"})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "fullName is required."}}

    r = await client.put(
        "/api/v1/profile",
        json={"fullName": "Grace Hopper", "timezone": "America/New_York", "company": "Navy"},
    )
    assert r.status_code == 200
    profile = r.json()["data"]
    assert profile["fullName"] == "Grace Hopper"
    assert profile["timezone"] == "America/New_York"
    assert profile["company"] == "Navy"
    assert "role" not in profile
    assert "userId" not in profile

    r = await client.patch("/api/v1/profile", json={"bio": "COBOL pioneer"})
    assert r.status_code == 200
    assert r.json()["data"]["bio"] == "COBOL pioneer"
    assert r.json()["data"]["company"] == "Navy"

    r = await client.delete("/api/v1/profile")
    assert r.status_code == 200
    r = await client.delete("/api/v1/profile")
    assert r.status_code == 404


async def test_profile_timezone_validation(client, email):
    await signup(client, email)

    r = await client.patch("/api/v1/profile", json={"timezone": "IST"})
    assert r.status_code == 400
    assert "is not an IANA timezone" in r.json()["error"]["message"]

    r = await client.patch("/api/v1/profile", json={"timezone": "EST"})
    assert r.status_code == 400

    r = await client.patch("/api/v1/profile", json={"timezone": "UTC"})
    assert r.status_code == 200
    assert r.json()["data"]["timezone"] == "UTC"
