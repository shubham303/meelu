from tests.conftest import signup


async def create_site(client, domain, name):
    r = await client.post("/api/v1/sites", json={"domain": domain, "name": name})
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_sites_create_and_list(client, email):
    await signup(client, email)

    r = await client.post("/api/v1/sites", json={})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Missing required field(s): domain, name"}}

    r = await client.post("/api/v1/sites", json={"domain": "not a host", "name": "Bad"})
    assert r.status_code == 400
    assert "doesn't look like a website" in r.json()["error"]["message"]

    site = await create_site(client, "https://Example.com/shop", "Example")
    assert site["domain"] == "example.com"
    assert site["name"] == "Example"
    assert site["socialLinks"] == []
    assert site["sitemapUrls"] == []
    assert "userId" not in site
    assert "seq" not in site
    assert site.get("country") is None

    r = await client.post("/api/v1/sites", json={"domain": "example.com", "name": "Dup"})
    assert r.status_code == 409
    assert "already in this workspace" in r.json()["error"]["message"]

    r = await client.get("/api/v1/sites")
    assert r.status_code == 200
    body = r.json()
    assert body["pagination"]["total"] == 1
    assert len(body["data"]) == 1
    assert body["pagination"]["page"] == 1
    assert body["data"][0]["id"] == site["id"]

    r = await client.get("/api/v1/sites", params={"q": "exam"})
    assert r.json()["pagination"]["total"] == 1
    r = await client.get("/api/v1/sites", params={"q": "zzz"})
    assert r.json()["pagination"]["total"] == 0

    r = await client.get("/api/v1/sites", params={"sort": "bogus"})
    assert r.status_code == 400
    assert r.json() == {
        "error": {"message": "sort: Input should be 'created', 'name', 'domain' or 'crawled'"}
    }

    r = await client.get("/api/v1/sites", params={"page_size": "x"})
    assert r.status_code == 400
    assert r.json() == {
        "error": {
            "message": "page_size: Input should be a valid integer, unable to parse string as an integer"
        }
    }

    r = await client.get("/api/v1/sites", params={"hasRepo": "maybe"})
    assert r.status_code == 400
    assert r.json() == {
        "error": {"message": "hasRepo: Input should be a valid boolean, unable to interpret input"}
    }


async def test_sites_by_id(client, email):
    await signup(client, email)
    site = await create_site(client, "one.example.com", "One")

    r = await client.get(f"/api/v1/sites/{site['id']}")
    assert r.status_code == 200
    assert r.json()["data"]["id"] == site["id"]

    r = await client.get("/api/v1/sites/site_missing00")
    assert r.status_code == 404

    r = await client.put(f"/api/v1/sites/{site['id']}", json={"name": "One Renamed"})
    assert r.status_code == 200
    assert r.json()["data"]["name"] == "One Renamed"

    r = await client.patch(f"/api/v1/sites/{site['id']}", json={"country": "IN"})
    assert r.status_code == 200
    assert r.json()["data"]["country"] == "IN"

    r = await client.delete(f"/api/v1/sites/{site['id']}")
    assert r.status_code == 200
    assert r.json()["data"]["deleted"] is True


async def test_current_site_resolution(client, email):
    await signup(client, email)

    r = await client.get("/api/v1/site")
    assert r.status_code == 200
    assert r.json() == {"data": None}

    r = await client.put("/api/v1/site", json={"name": "X"})
    assert r.status_code == 400
    assert "No website in this workspace yet" in r.json()["error"]["message"]

    first = await create_site(client, "first.example.com", "First")

    r = await client.get("/api/v1/site")
    assert r.status_code == 200
    assert r.json()["data"]["id"] == first["id"]

    second = await create_site(client, "second.example.com", "Second")

    r = await client.get("/api/v1/site")
    assert r.status_code == 400
    assert "This workspace has 2 websites" in r.json()["error"]["message"]

    r = await client.get("/api/v1/site", headers={"x-meelu-site": second["id"]})
    assert r.status_code == 200
    assert r.json()["data"]["id"] == second["id"]

    r = await client.get("/api/v1/site", params={"siteId": first["id"]})
    assert r.status_code == 200
    assert r.json()["data"]["id"] == first["id"]

    r = await client.get("/api/v1/site", headers={"x-meelu-site": "site_nope"})
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "No website site_nope in this workspace."}}


async def test_current_site_agent_patch(client, email):
    await signup(client, email)
    await create_site(client, "solo.example.com", "Solo")

    r = await client.patch("/api/v1/site", json={})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Nothing to save."}}

    r = await client.patch("/api/v1/site", json={"gscProperty": "sc-domain:solo"})
    assert r.status_code == 400
    assert r.json() == {
        "error": {
            "message": "gscProperty is not part of the website record. This endpoint accepts "
            "summary, socialLinks, country, name, domain, repoUrl, sitemapUrls."
        }
    }

    r = await client.patch(
        "/api/v1/site",
        json={
            "summary": "A solo site",
            "socialLinks": [{"platform": "x", "url": "https://x.com/solo"}],
        },
    )
    assert r.status_code == 200
    site = r.json()["data"]
    assert site["summary"] == "A solo site"
    assert site["socialLinks"] == [{"platform": "x", "url": "https://x.com/solo"}]

    r = await client.patch("/api/v1/site", json={"socialLinks": [{"platform": "x"}]})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Every socialLinks entry needs a url."}}

    r = await client.delete("/api/v1/site")
    assert r.status_code == 200
    assert r.json()["data"]["deleted"] is True
