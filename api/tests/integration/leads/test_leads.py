import pytest

from tests.conftest import signup


@pytest.fixture(autouse=True)
def mount_routers():
    from src.app import app
    from src.leads.endpoints import router

    prefix = "/api/v1/lead-management"
    mounted = any(str(getattr(r, "path", "")).startswith(prefix) for r in app.routes)
    if not mounted:
        app.include_router(router, prefix="/api/v1")


async def prepare(client, email):
    await signup(client, email)
    r = await client.post(
        "/api/v1/sites", json={"domain": "reach.example.com", "name": "Reach Example"}
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def make_campaign(client, name="Founders Q1", **extra):
    payload = {
        "name": name,
        "audience": "Bootstrapped SaaS founders",
        "sources": ["web-search", "hackernews"],
        "schedule": "weekly",
    }
    payload.update(extra)
    r = await client.post("/api/v1/lead-management/campaigns", json=payload)
    assert r.status_code == 201, r.text
    return r.json()["data"]


def lead_item(name, **extra):
    base = {
        "name": name,
        "company": "Acme",
        "role": "Founder",
        "source": "hackernews",
        "sourceUrl": "https://news.ycombinator.com/item?id=1",
        "fitScore": 0.8,
        "fitReason": "Asked for an SEO tool",
        "evidence": [{"quote": "we need audits", "url": "https://example.com/p"}],
    }
    base.update(extra)
    return base


async def test_campaign_crud(client, email):
    await prepare(client, email)
    campaign = await make_campaign(client)
    assert campaign["status"] == "active"
    assert campaign["audience"] == "Bootstrapped SaaS founders"
    assert campaign["sources"] == ["web-search", "hackernews"]
    assert campaign["schedule"] == "weekly"

    r = await client.post(
        "/api/v1/lead-management/campaigns", json={"name": "Founders Q1", "audience": "dupes"}
    )
    assert r.status_code == 409

    r = await client.post("/api/v1/lead-management/campaigns", json={"name": "No audience"})
    assert r.status_code == 400

    r = await client.get("/api/v1/lead-management/campaigns")
    assert r.status_code == 200
    campaigns = r.json()["data"]
    assert [c["name"] for c in campaigns] == ["Founders Q1"]

    r = await client.patch(
        f"/api/v1/lead-management/campaigns/{campaign['id']}",
        json={"status": "paused", "schedule": None},
    )
    assert r.status_code == 200, r.text
    patched = r.json()["data"]
    assert patched["status"] == "paused"
    assert patched["schedule"] is None

    r = await client.patch(
        f"/api/v1/lead-management/campaigns/{campaign['id']}", json={"status": "bogus"}
    )
    assert r.status_code == 400

    r = await client.delete(f"/api/v1/lead-management/campaigns/{campaign['id']}")
    assert r.status_code == 200
    r = await client.get(f"/api/v1/lead-management/campaigns/{campaign['id']}")
    assert r.status_code == 404


async def test_run_lifecycle(client, email):
    await prepare(client, email)
    campaign = await make_campaign(client)

    r = await client.post("/api/v1/lead-management/runs", json={"campaignId": "lc_missing"})
    assert r.status_code == 404

    r = await client.post("/api/v1/lead-management/runs", json={"campaignId": campaign["id"]})
    assert r.status_code == 201, r.text
    run = r.json()["data"]
    assert run["status"] == "running"
    assert run["campaignId"] == campaign["id"]
    assert run["sourceStats"] == {}
    assert run["finishedAt"] is None

    r = await client.patch(
        f"/api/v1/lead-management/runs/{run['id']}",
        json={
            "status": "done",
            "found": 12,
            "qualified": 5,
            "skippedKnown": 3,
            "sourceStats": {"hackernews": {"found": 12, "qualified": 5}},
        },
    )
    assert r.status_code == 200, r.text
    done = r.json()["data"]
    assert done["status"] == "done"
    assert done["found"] == 12
    assert done["finishedAt"] is not None

    r = await client.patch(f"/api/v1/lead-management/runs/{run['id']}", json={"status": "bogus"})
    assert r.status_code == 400

    other = await make_campaign(client, name="Other")
    r = await client.post("/api/v1/lead-management/runs", json={"campaignId": other["id"]})
    run2 = r.json()["data"]

    r = await client.get("/api/v1/lead-management/runs")
    page = r.json()
    assert [x["id"] for x in page["data"]] == [run2["id"], run["id"]]
    assert page["pagination"]["total"] == 2

    r = await client.get(f"/api/v1/lead-management/runs?campaignId={campaign['id']}")
    assert [x["id"] for x in r.json()["data"]] == [run["id"]]

    r = await client.get(f"/api/v1/lead-management/runs/{run['id']}")
    assert r.json()["data"]["id"] == run["id"]


async def test_bulk_leads_dedupe(client, email):
    await prepare(client, email)
    campaign = await make_campaign(client)
    r = await client.post("/api/v1/lead-management/runs", json={"campaignId": campaign["id"]})
    run = r.json()["data"]

    r = await client.post(
        "/api/v1/lead-management/leads/bulk",
        json={
            "runId": run["id"],
            "campaignId": campaign["id"],
            "leads": [
                lead_item("Alice Ash", email="Alice@Acme.com", website="https://acme.com/about"),
                lead_item(
                    "Bob Byte",
                    company="Byteworks",
                    website="www.byteworks.io",
                    channelHandles={"x": "@bobbyte"},
                ),
                lead_item("Cara Code", channelHandles={"linkedin": "caracode"}, stage="found"),
            ],
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"inserted": 3, "skipped": 0}

    r = await client.post(
        "/api/v1/lead-management/leads/bulk",
        json={
            "campaignId": campaign["id"],
            "leads": [
                lead_item("Alice Again", email="alice@acme.com"),
                lead_item("Acme Site", website="http://www.acme.com"),
                lead_item("Bob Twin", channelHandles={"x": "bobbyte"}),
                lead_item("Dana Dev", email="dana@devs.dev"),
            ],
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"inserted": 1, "skipped": 3}

    r = await client.get("/api/v1/lead-management/leads")
    leads = r.json()["data"]
    assert len(leads) == 4
    by_name = {x["name"]: x for x in leads}
    assert by_name["Alice Ash"]["stage"] == "qualified"
    assert by_name["Cara Code"]["stage"] == "found"
    assert by_name["Alice Ash"]["runId"] == run["id"]
    assert by_name["Dana Dev"]["runId"] is None

    r = await client.post(
        "/api/v1/lead-management/leads/bulk", json={"runId": "lrn_missing", "leads": []}
    )
    assert r.status_code == 404


async def test_manual_create_and_conflict(client, email):
    await prepare(client, email)

    r = await client.post(
        "/api/v1/lead-management/leads",
        json={"name": "Eve East", "email": "eve@east.com", "note": "met at a conf"},
    )
    assert r.status_code == 201, r.text
    lead = r.json()["data"]
    assert lead["stage"] == "qualified"
    assert lead["note"] == "met at a conf"
    assert lead["emailVerified"] is False

    r = await client.post(
        "/api/v1/lead-management/leads", json={"name": "Eve Dupe", "email": "EVE@east.com"}
    )
    assert r.status_code == 409, r.text
    assert r.json()["error"]["leadId"] == lead["id"]

    r = await client.post("/api/v1/lead-management/leads", json={"email": "noname@east.com"})
    assert r.status_code == 400


async def test_lead_filters_sort_patch_delete(client, email):
    await prepare(client, email)
    campaign = await make_campaign(client)

    r = await client.post(
        "/api/v1/lead-management/leads/bulk",
        json={
            "campaignId": campaign["id"],
            "leads": [
                lead_item("Low Fit", email="low@a.com", fitScore=0.61, source="web-search"),
                lead_item("High Fit", email="high@b.com", fitScore=0.95),
                lead_item("No Email", company="Ghostly", fitScore=None, website="ghostly.gg"),
            ],
        },
    )
    assert r.json()["data"]["inserted"] == 3

    r = await client.post("/api/v1/lead-management/leads", json={"name": "Solo Sam"})
    solo = r.json()["data"]

    r = await client.get("/api/v1/lead-management/leads?sort=fit")
    names = [x["name"] for x in r.json()["data"]]
    assert names[:2] == ["High Fit", "Low Fit"]
    assert set(names[2:]) == {"No Email", "Solo Sam"}

    r = await client.get(f"/api/v1/lead-management/leads?campaignId={campaign['id']}")
    assert len(r.json()["data"]) == 3

    r = await client.get("/api/v1/lead-management/leads?hasEmail=true")
    assert {x["name"] for x in r.json()["data"]} == {"Low Fit", "High Fit"}

    r = await client.get("/api/v1/lead-management/leads?minFit=0.9")
    assert [x["name"] for x in r.json()["data"]] == ["High Fit"]

    r = await client.get("/api/v1/lead-management/leads?source=web-search")
    assert [x["name"] for x in r.json()["data"]] == ["Low Fit"]

    r = await client.get("/api/v1/lead-management/leads?q=ghost")
    assert [x["name"] for x in r.json()["data"]] == ["No Email"]

    r = await client.get("/api/v1/lead-management/leads?stage=bogus")
    assert r.status_code == 400

    r = await client.patch(
        f"/api/v1/lead-management/leads/{solo['id']}",
        json={"stage": "shortlisted", "company": "Samco", "emailVerified": True},
    )
    assert r.status_code == 200, r.text
    patched = r.json()["data"]
    assert patched["stage"] == "shortlisted"
    assert patched["stageChangedAt"] is not None
    assert patched["company"] == "Samco"

    r = await client.get("/api/v1/lead-management/leads?stage=shortlisted")
    assert [x["id"] for x in r.json()["data"]] == [solo["id"]]

    r = await client.patch(
        f"/api/v1/lead-management/leads/{solo['id']}", json={"stage": "contacted"}
    )
    assert r.status_code == 400

    r = await client.delete(f"/api/v1/lead-management/leads/{solo['id']}")
    assert r.status_code == 200
    r = await client.get(f"/api/v1/lead-management/leads/{solo['id']}")
    assert r.status_code == 404


async def test_summary(client, email):
    await prepare(client, email)
    campaign = await make_campaign(client)

    r = await client.post("/api/v1/lead-management/runs", json={"campaignId": campaign["id"]})
    run = r.json()["data"]
    await client.patch(f"/api/v1/lead-management/runs/{run['id']}", json={"status": "done"})

    r = await client.post(
        "/api/v1/lead-management/leads/bulk",
        json={
            "runId": run["id"],
            "campaignId": campaign["id"],
            "leads": [
                lead_item("Keep Kay", email="kay@x.com"),
                lead_item("Short List", email="short@y.com"),
                lead_item("Fresh Find", email="fresh@w.com", stage="found"),
            ],
        },
    )
    assert r.json()["data"]["inserted"] == 3

    r = await client.get("/api/v1/lead-management/leads?q=Short")
    short = r.json()["data"][0]
    await client.patch(
        f"/api/v1/lead-management/leads/{short['id']}", json={"stage": "shortlisted"}
    )

    r = await client.get("/api/v1/lead-management/summary")
    assert r.status_code == 200, r.text
    summary = r.json()["data"]
    assert summary["stages"] == {"found": 1, "qualified": 1, "shortlisted": 1}
    assert summary["lastRun"]["id"] == run["id"]
    assert summary["campaigns"] == [
        {
            "id": campaign["id"],
            "name": campaign["name"],
            "status": "active",
            "qualified": 1,
            "shortlisted": 1,
        }
    ]
