from tests.integration.technical_seo.test_audit import ORIGIN, prepare


async def audited(client, email):
    site, pages = await prepare(client, email)
    r = await client.post("/api/v1/site/technical-seo/run-audit", json={})
    assert r.status_code == 201, r.text
    return site, pages, r.json()["data"]["run"]


async def test_runs_listing_and_lifecycle(client, email):
    site, _, run = await audited(client, email)
    await client.post("/api/v1/site/technical-seo/run-audit", json={"trigger": "schedule"})

    r = await client.get("/api/v1/site/technical-seo/runs")
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["total"] == 2
    assert body["shown"] == 2
    assert body["offset"] == 0
    assert body["runs"][0]["trigger"] == "schedule"
    assert body["runs"][1]["id"] == run["id"]

    r = await client.get("/api/v1/site/technical-seo/runs", params={"trigger": "schedule"})
    assert r.json()["data"]["total"] == 1

    r = await client.get("/api/v1/site/technical-seo/runs", params={"reviewed": "true"})
    assert r.json()["data"]["total"] == 0

    r = await client.get(f"/api/v1/site/technical-seo/runs/{run['id']}")
    assert r.json()["data"]["id"] == run["id"]

    r = await client.patch(f"/api/v1/site/technical-seo/runs/{run['id']}", json={"reviewed": True})
    assert r.status_code == 200
    assert r.json()["data"]["reviewedAt"] is not None

    r = await client.get("/api/v1/site/technical-seo/runs", params={"reviewed": "true"})
    assert r.json()["data"]["total"] == 1

    r = await client.put(f"/api/v1/site/technical-seo/runs/{run['id']}", json={"trigger": "agent"})
    assert r.json()["data"]["trigger"] == "agent"

    r = await client.patch(f"/api/v1/site/technical-seo/runs/{run['id']}", json={})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Nothing to change. Send reviewed or trigger."}}

    r = await client.delete(f"/api/v1/site/technical-seo/runs/{run['id']}")
    assert r.json()["data"] == {"deleted": True}

    r = await client.delete(f"/api/v1/site/technical-seo/runs/{run['id']}")
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "No such technical SEO run for this website."}}

    r = await client.get("/api/v1/site/technical-seo/runs")
    assert r.json()["data"]["total"] == 1


async def test_site_issue_crud(client, email):
    site, _, run = await audited(client, email)

    r = await client.post(
        "/api/v1/site/technical-seo/issues",
        json={"kind": "llms-missing", "issue": "  There is no /llms.txt.  "},
    )
    assert r.status_code == 201, r.text
    issue = r.json()["data"]
    assert issue["kind"] == "llms-missing"
    assert issue["issue"] == "There is no /llms.txt."
    assert issue["severity"] == "p2"
    assert issue["state"] == "open"
    assert issue["runId"] == run["id"]
    assert issue["siteId"] == site["id"]
    assert "userId" not in issue

    r = await client.post(
        "/api/v1/site/technical-seo/issues",
        json={"kind": "llms-missing", "issue": "Again"},
    )
    assert r.status_code == 409
    assert r.json() == {
        "error": {"message": 'This run already carries the site-wide "llms-missing" check.'}
    }

    r = await client.post(
        "/api/v1/site/technical-seo/issues", json={"kind": "not-a-kind", "issue": "x"}
    )
    assert r.status_code == 400
    assert r.json()["error"]["message"].startswith('Unknown issue kind "not-a-kind".')

    r = await client.post("/api/v1/site/technical-seo/issues", json={"kind": "robots-missing"})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "An issue needs a wording."}}

    r = await client.get(f"/api/v1/site/technical-seo/issues/{issue['id']}")
    assert r.json()["data"]["id"] == issue["id"]

    r = await client.put(
        f"/api/v1/site/technical-seo/issues/{issue['id']}",
        json={"state": "rejected", "rejectionReason": "Not worth it yet."},
    )
    assert r.status_code == 200
    assert r.json()["data"]["state"] == "rejected"
    assert r.json()["data"]["rejectionReason"] == "Not worth it yet."

    r = await client.patch(f"/api/v1/site/technical-seo/issues/{issue['id']}", json={})
    assert r.status_code == 400
    assert r.json() == {
        "error": {"message": "Nothing to change. Send issue, severity, state or rejectionReason."}
    }

    r = await client.patch(
        f"/api/v1/site/technical-seo/issues/{issue['id']}", json={"severity": "p9"}
    )
    assert r.status_code == 400
    assert r.json()["error"]["message"].startswith('Invalid severity "p9".')

    r = await client.patch(
        "/api/v1/site/technical-seo/issues",
        json={"kind": "llms-missing", "state": "open"},
    )
    assert r.status_code == 200
    assert r.json()["data"] == {"runId": run["id"], "updated": 1}

    r = await client.patch(
        "/api/v1/site/technical-seo/issues",
        json={"kind": "robots-missing", "state": "open"},
    )
    assert r.status_code == 404
    assert r.json() == {
        "error": {"message": 'No site-wide "robots-missing" issue in this run to change.'}
    }

    r = await client.delete(f"/api/v1/site/technical-seo/issues/{issue['id']}")
    assert r.json()["data"] == {"deleted": True}

    r = await client.get(f"/api/v1/site/technical-seo/issues/{issue['id']}")
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "No such site-wide issue on this website."}}


async def test_page_issue_crud(client, email):
    site, pages, run = await audited(client, email)
    home = pages[f"{ORIGIN}/"]

    r = await client.post(
        "/api/v1/site/technical-seo/page-issues",
        json={
            "kind": "missing-lang",
            "issue": "The html tag declares no language.",
            "severity": "p3",
            "url": f"{ORIGIN}/",
        },
    )
    assert r.status_code == 201, r.text
    issue = r.json()["data"]
    assert issue["pageId"] == home
    assert issue["url"] == f"{ORIGIN}/"
    assert issue["matchedPages"] == 1
    assert issue["severity"] == "p3"

    r = await client.post(
        "/api/v1/site/technical-seo/page-issues",
        json={"kind": "missing-lang", "issue": "again", "pageId": home},
    )
    assert r.status_code == 409
    assert r.json() == {
        "error": {"message": 'This run already carries the "missing-lang" check on that page.'}
    }

    r = await client.post(
        "/api/v1/site/technical-seo/page-issues",
        json={"kind": "missing-lang", "issue": "x", "url": f"{ORIGIN}/nowhere"},
    )
    assert r.status_code == 404
    assert r.json() == {"error": {"message": f"No page on record at {ORIGIN}/nowhere."}}

    r = await client.post(
        "/api/v1/site/technical-seo/page-issues",
        json={"kind": "missing-lang", "issue": "x", "pageId": "pg_missing00"},
    )
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "No page pg_missing00 on this website."}}

    r = await client.post(
        "/api/v1/site/technical-seo/page-issues", json={"kind": "missing-lang", "issue": "x"}
    )
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "A page issue needs a pageId or a url."}}

    r = await client.get(f"/api/v1/site/technical-seo/page-issues/{issue['id']}")
    assert r.json()["data"]["url"] == f"{ORIGIN}/"

    r = await client.put(
        f"/api/v1/site/technical-seo/page-issues/{issue['id']}",
        json={"issue": "Set a lang attribute on the html element."},
    )
    assert r.json()["data"]["issue"] == "Set a lang attribute on the html element."
    assert r.json()["data"]["url"] == f"{ORIGIN}/"

    r = await client.patch(
        "/api/v1/site/technical-seo/page-issues",
        json={"kind": "duplicate-title", "state": "rejected", "rejectionReason": "By design."},
    )
    assert r.status_code == 200
    assert r.json()["data"] == {"runId": run["id"], "updated": 2}

    r = await client.patch("/api/v1/site/technical-seo/page-issues", json={"state": "open"})
    assert r.status_code == 400
    assert r.json() == {
        "error": {"message": "Changing page issues in bulk needs a kind, a pageId or a url."}
    }

    r = await client.patch(
        "/api/v1/site/technical-seo/page-issues",
        json={"url": f"{ORIGIN}/orphan", "kind": "orphan-page", "state": "rejected"},
    )
    assert r.json()["data"]["updated"] == 1

    r = await client.patch(
        "/api/v1/site/technical-seo/page-issues",
        json={"kind": "url-dated", "state": "open"},
    )
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "No page issue in this run matched."}}

    r = await client.delete(f"/api/v1/site/technical-seo/page-issues/{issue['id']}")
    assert r.json()["data"] == {"deleted": True}

    r = await client.get(f"/api/v1/site/technical-seo/page-issues/{issue['id']}")
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "No such page issue on this website."}}


async def test_issue_endpoints_need_a_site(client, email):
    r = await client.get("/api/v1/site/technical-seo/summary")
    assert r.status_code == 401


async def test_llm_check_flags_and_verdicts(client, email):
    site, pages, run = await audited(client, email)

    r = await client.get(
        "/api/v1/site/technical-seo/page-issues", params={"kind": "duplicate-title"}
    )
    assert r.json()["data"][0]["llmCheckRequired"] is False

    r = await client.get(
        "/api/v1/site/technical-seo/page-issues", params={"llmCheckPending": "true"}
    )
    pending = r.json()
    total = pending["pagination"]["total"]
    assert total >= 1
    assert all(i["llmCheckRequired"] and i["llmCheckDoneAt"] is None for i in pending["data"])
    first = pending["data"][0]
    r = await client.get("/api/v1/site/technical-seo/page-issues", params={"kind": "server-error"})
    second = r.json()["data"][0]

    r = await client.post(
        f"/api/v1/site/technical-seo/page-issues/{first['id']}/llm-check",
        json={"verdict": "update", "issue": "A sharper explanation from the check."},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"] == {"id": first["id"], "verdict": "update", "deleted": False}
    r = await client.get(f"/api/v1/site/technical-seo/page-issues/{first['id']}")
    body = r.json()["data"]
    assert body["issue"] == "A sharper explanation from the check."
    assert body["llmCheckDoneAt"] is not None
    assert body["reviewedAt"] is None

    r = await client.post(
        f"/api/v1/site/technical-seo/page-issues/{second['id']}/llm-check",
        json={"verdict": "delete"},
    )
    assert r.json()["data"]["deleted"] is True
    r = await client.get(f"/api/v1/site/technical-seo/page-issues/{second['id']}")
    assert r.status_code == 404

    r = await client.post(
        f"/api/v1/site/technical-seo/page-issues/{first['id']}/llm-check",
        json={"verdict": "update"},
    )
    assert r.status_code == 400

    r = await client.get(
        "/api/v1/site/technical-seo/page-issues", params={"llmCheckPending": "true"}
    )
    assert r.json()["pagination"]["total"] == total - 1

    r = await client.get("/api/v1/site/technical-seo/issues", params={"llmCheckPending": "true"})
    assert all(i["llmCheckRequired"] for i in r.json()["data"])

    r = await client.post(
        "/api/v1/site/technical-seo/issues",
        json={"kind": "robots-missing", "issue": "Hand-made for the keep verdict."},
    )
    site_issue = r.json()["data"]
    r = await client.post(
        f"/api/v1/site/technical-seo/issues/{site_issue['id']}/llm-check",
        json={"verdict": "keep"},
    )
    assert r.json()["data"] == {"id": site_issue["id"], "verdict": "keep", "deleted": False}
    r = await client.get(f"/api/v1/site/technical-seo/issues/{site_issue['id']}")
    assert r.json()["data"]["llmCheckDoneAt"] is not None
    assert r.json()["data"]["issue"] == site_issue["issue"]
