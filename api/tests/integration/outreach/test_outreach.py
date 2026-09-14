async def create_project(client, **overrides):
    body = {"name": "Roasters", "prospectProfile": "Specialty coffee roasters", **overrides}
    r = await client.post("/api/v1/outreach/projects", json=body)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def create_campaign(client, project_id, requested=5):
    r = await client.post(
        "/api/v1/outreach/campaigns",
        json={"projectId": project_id, "requestedCount": requested},
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_project_lifecycle(client, site):
    r = await client.post("/api/v1/outreach/projects", json={})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Missing required field(s): name, prospectProfile"}}

    project = await create_project(client, goal="Book demos")
    assert project["name"] == "Roasters"
    assert project["prospectProfile"] == "Specialty coffee roasters"
    assert project["goal"] == "Book demos"
    assert project["siteId"] == site["id"]
    assert "userId" not in project
    assert "seq" not in project
    assert "cta" not in project

    r = await client.get("/api/v1/outreach/projects")
    assert r.status_code == 200
    assert [p["id"] for p in r.json()["data"]] == [project["id"]]

    r = await client.get(f"/api/v1/outreach/projects/{project['id']}")
    assert r.json()["data"]["id"] == project["id"]

    r = await client.put(
        f"/api/v1/outreach/projects/{project['id']}", json={"name": "Indie roasters"}
    )
    assert r.status_code == 200
    assert r.json()["data"]["name"] == "Indie roasters"

    r = await client.get("/api/v1/outreach/projects/prj_missing")
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "Not found"}}

    r = await client.delete(f"/api/v1/outreach/projects/{project['id']}")
    assert r.status_code == 200
    assert r.json()["data"] == {"deleted": True}

    r = await client.delete(f"/api/v1/outreach/projects/{project['id']}")
    assert r.status_code == 404


async def test_campaign_lifecycle_and_found_counts(client, site):
    project = await create_project(client)

    r = await client.post("/api/v1/outreach/campaigns", json={"projectId": project["id"]})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Missing required field(s): requestedCount"}}

    r = await client.post(
        "/api/v1/outreach/campaigns", json={"projectId": "prj_nope", "requestedCount": 3}
    )
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "projectId must reference an existing project."}}

    for bad in (0, 101, "abc"):
        r = await client.post(
            "/api/v1/outreach/campaigns",
            json={"projectId": project["id"], "requestedCount": bad},
        )
        assert r.status_code == 400, bad
        assert r.json() == {
            "error": {"message": "requestedCount must be a whole number between 1 and 100."}
        }

    campaign = await create_campaign(client, project["id"], 2)
    assert campaign["status"] == "running"
    assert campaign["requestedCount"] == 2
    assert campaign["finishedAt"] is None
    assert "found" not in campaign

    r = await client.get("/api/v1/outreach/campaigns")
    listed = r.json()["data"]
    assert listed[0]["found"] == 0

    await client.post(
        "/api/v1/outreach/prospects",
        json={"name": "Bean Co", "campaignId": campaign["id"], "email": "a@bean.co"},
    )
    r = await client.get(f"/api/v1/outreach/campaigns/{campaign['id']}")
    assert r.json()["data"]["found"] == 1

    r = await client.get("/api/v1/outreach/campaigns", params={"status": "done"})
    assert r.json()["data"] == []
    r = await client.get("/api/v1/outreach/campaigns", params={"projectId": "prj_other"})
    assert r.json()["data"] == []

    r = await client.put(f"/api/v1/outreach/campaigns/{campaign['id']}", json={"status": "nope"})
    assert r.status_code == 400
    assert r.json() == {
        "error": {"message": "Invalid status. Allowed values: running, done, failed."}
    }

    r = await client.put(
        f"/api/v1/outreach/campaigns/{campaign['id']}",
        json={"status": "done", "projectId": "prj_hijack", "requestedCount": 99},
    )
    assert r.status_code == 200
    done = r.json()["data"]
    assert done["status"] == "done"
    assert done["projectId"] == project["id"]
    assert done["requestedCount"] == 2
    assert done["finishedAt"] is not None

    r = await client.put(f"/api/v1/outreach/campaigns/{campaign['id']}", json={"status": "running"})
    assert r.json()["data"]["finishedAt"] is None

    r = await client.delete(f"/api/v1/outreach/campaigns/{campaign['id']}")
    assert r.json()["data"] == {"deleted": True}
    r = await client.get("/api/v1/outreach/prospects")
    assert r.json()["data"] == []


async def test_prospect_dedupe(client, site):
    project = await create_project(client)
    campaign = await create_campaign(client, project["id"])

    r = await client.post("/api/v1/outreach/prospects", json={"name": "Solo"})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Missing required field(s): campaignId"}}

    r = await client.post(
        "/api/v1/outreach/prospects", json={"name": "Solo", "campaignId": "cmp_nope"}
    )
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "campaignId must reference an existing campaign run."}}

    r = await client.post(
        "/api/v1/outreach/prospects",
        json={"name": "Solo", "campaignId": campaign["id"], "status": "maybe"},
    )
    assert r.status_code == 400
    assert "Invalid status. Allowed values: found, contacted" in r.json()["error"]["message"]

    r = await client.post(
        "/api/v1/outreach/prospects",
        json={
            "name": "Ada Lovelace",
            "company": "Bean Co",
            "email": "Ada@Bean.co",
            "website": "https://www.bean.co/about?x=1",
            "campaignId": campaign["id"],
        },
    )
    assert r.status_code == 201
    first = r.json()["data"]
    assert first["status"] == "found"
    assert first["dedupeKeys"] == ["email:ada@bean.co", "domain:bean.co", "company:bean co"]

    r = await client.post(
        "/api/v1/outreach/prospects",
        json={"name": "Someone Else", "email": "ada@bean.co", "campaignId": campaign["id"]},
    )
    assert r.status_code == 409
    assert r.json()["error"]["message"] == (
        f"Duplicate prospect: Ada Lovelace (Bean Co) was already found for this project "
        f"by an earlier run [{first['id']}] — matched on email:ada@bean.co. "
        f"Skip this lead and find a different one. Call GET "
        f"/api/v1/outreach/projects/:id/known-prospects before searching so you don't "
        f"re-find them."
    )

    other_campaign = await create_campaign(client, project["id"])
    r = await client.post(
        "/api/v1/outreach/prospects",
        json={
            "name": "Third",
            "website": "http://bean.co",
            "campaignId": other_campaign["id"],
        },
    )
    assert r.status_code == 409
    assert "matched on domain:bean.co" in r.json()["error"]["message"]

    r = await client.post(
        "/api/v1/outreach/prospects",
        json={"name": "Nameless Only", "campaignId": campaign["id"]},
    )
    assert r.status_code == 201
    assert r.json()["data"]["dedupeKeys"] == ["name:nameless only"]

    r = await client.post(
        "/api/v1/outreach/prospects",
        json={
            "prospects": [
                {"name": "Fresh Roast", "email": "hi@fresh.example", "campaignId": campaign["id"]},
                {"name": "Ada Again", "email": "ada@bean.co", "campaignId": campaign["id"]},
                {"campaignId": campaign["id"]},
            ]
        },
    )
    assert r.status_code == 201
    batch = r.json()["data"]
    assert [p["name"] for p in batch["created"]] == ["Fresh Roast"]
    assert [s["name"] for s in batch["skipped"]] == ["Ada Again", "(unnamed)"]
    assert "Duplicate prospect" in batch["skipped"][0]["reason"]
    assert batch["skipped"][1]["reason"] == "Missing required field(s): name"


async def test_prospect_update_and_known_prospects(client, site):
    project = await create_project(client)
    campaign = await create_campaign(client, project["id"])

    r = await client.post(
        "/api/v1/outreach/prospects",
        json={
            "name": "Ada",
            "company": "Bean Co",
            "email": "ada@bean.co",
            "campaignId": campaign["id"],
        },
    )
    first = r.json()["data"]

    r = await client.post(
        "/api/v1/outreach/prospects",
        json={"name": "Bob", "email": "bob@grind.example", "campaignId": campaign["id"]},
    )
    second = r.json()["data"]

    r = await client.put(
        f"/api/v1/outreach/prospects/{second['id']}", json={"email": "ada@bean.co"}
    )
    assert r.status_code == 409
    assert "matched on email:ada@bean.co" in r.json()["error"]["message"]

    r = await client.put(
        f"/api/v1/outreach/prospects/{second['id']}",
        json={"status": "won", "campaignId": "cmp_hijack"},
    )
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "won"
    assert r.json()["data"]["campaignId"] == campaign["id"]

    r = await client.put(
        f"/api/v1/outreach/prospects/{second['id']}", json={"website": "https://grind.example"}
    )
    assert r.json()["data"]["dedupeKeys"] == ["email:bob@grind.example", "domain:grind.example"]

    r = await client.get("/api/v1/outreach/prospects", params={"status": "won"})
    assert [p["id"] for p in r.json()["data"]] == [second["id"]]

    r = await client.get("/api/v1/outreach/prospects", params={"projectId": project["id"]})
    assert {p["id"] for p in r.json()["data"]} == {first["id"], second["id"]}

    r = await client.get("/api/v1/outreach/prospects", params={"campaignId": "cmp_none"})
    assert r.json()["data"] == []

    r = await client.get(f"/api/v1/outreach/projects/{project['id']}/known-prospects")
    assert r.status_code == 200
    known = r.json()["data"]
    assert known["projectId"] == project["id"]
    assert known["projectName"] == "Roasters"
    assert known["count"] == 2
    assert sorted(known["excludeEmails"]) == ["ada@bean.co", "bob@grind.example"]
    assert known["excludeDomains"] == ["grind.example"]
    assert known["excludeCompanies"] == ["bean co"]
    assert {p["id"] for p in known["prospects"]} == {first["id"], second["id"]}
    assert all("dedupeKeys" in p for p in known["prospects"])

    r = await client.get("/api/v1/outreach/projects/prj_missing/known-prospects")
    assert r.status_code == 404

    r = await client.delete(f"/api/v1/outreach/prospects/{first['id']}")
    assert r.json()["data"] == {"deleted": True}
    r = await client.delete(f"/api/v1/outreach/prospects/{first['id']}")
    assert r.status_code == 404
