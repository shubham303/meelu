from tests.conftest import signup

HTML = "<h1>Report</h1><p>All local, no network.</p>"


async def setup_site(client, email):
    await signup(client, email)
    r = await client.post("/api/v1/sites", json={"domain": "example.com", "name": "Example"})
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def create_session(client, **body):
    r = await client.post("/api/v1/analytics/sessions", json=body)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_sessions_lifecycle(client, email):
    site = await setup_site(client, email)

    first = await create_session(client)
    assert first["title"] == "Session 1"
    assert first["about"] == ""
    assert first["siteId"] == site["id"]
    assert "sessionKey" not in first
    assert "userId" not in first
    assert "seq" not in first

    second = await create_session(client, title="  Named  ", about="why", sessionKey="k-1")
    assert second["title"] == "Named"
    assert second["about"] == "why"
    assert second["sessionKey"] == "k-1"

    r = await client.get("/api/v1/analytics/sessions")
    assert r.status_code == 200
    rows = r.json()["data"]
    assert [row["id"] for row in rows] == [second["id"], first["id"]]

    r = await client.get(f"/api/v1/analytics/sessions/{first['id']}")
    assert r.status_code == 200
    assert r.json()["data"]["id"] == first["id"]

    r = await client.get("/api/v1/analytics/sessions/ssn_missing0")
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "Not found"}}

    r = await client.put(f"/api/v1/analytics/sessions/{first['id']}", json={})
    assert r.status_code == 400
    assert r.json() == {
        "error": {"message": "Nothing to update — send `title`, `about` and/or `sessionKey`."}
    }

    r = await client.put(
        f"/api/v1/analytics/sessions/{first['id']}",
        json={"title": "Renamed", "about": "new", "sessionKey": ""},
    )
    assert r.status_code == 200
    updated = r.json()["data"]
    assert updated["title"] == "Renamed"
    assert updated["about"] == "new"
    assert "sessionKey" not in updated

    r = await client.put("/api/v1/analytics/sessions/ssn_missing0", json={"title": "x"})
    assert r.status_code == 404

    r = await client.delete(f"/api/v1/analytics/sessions/{second['id']}")
    assert r.status_code == 200
    assert r.json() == {"data": {"ok": True}}

    r = await client.delete(f"/api/v1/analytics/sessions/{second['id']}")
    assert r.status_code == 404


async def test_sources_lifecycle(client, email):
    await setup_site(client, email)
    session = await create_session(client)

    r = await client.post(f"/api/v1/analytics/sessions/{session['id']}/sources", json={})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Missing required field(s): name"}}

    r = await client.post(
        "/api/v1/analytics/sessions/ssn_missing0/sources", json={"name": "pages.csv"}
    )
    assert r.status_code == 404

    r = await client.post(
        f"/api/v1/analytics/sessions/{session['id']}/sources", json={"name": "pages.csv"}
    )
    assert r.status_code == 201
    plain = r.json()["data"]
    assert plain["name"] == "pages.csv"
    assert plain["sessionId"] == session["id"]
    assert "filePath" not in plain

    r = await client.post(
        f"/api/v1/analytics/sessions/{session['id']}/sources",
        json={"name": "corpus", "filePath": "exports\\corpus.csv"},
    )
    assert r.status_code == 201
    windows_path = r.json()["data"]
    assert windows_path["filePath"] == "exports/corpus.csv"

    r = await client.post(
        f"/api/v1/analytics/sessions/{session['id']}/sources",
        json={"name": "bad", "filePath": "/etc/passwd"},
    )
    assert r.status_code == 400
    assert "relative to the analytics data directory" in r.json()["error"]["message"]

    r = await client.post(
        f"/api/v1/analytics/sessions/{session['id']}/sources",
        json={"name": "bad", "filePath": "C:/data/corpus.csv"},
    )
    assert r.status_code == 400

    r = await client.post(
        f"/api/v1/analytics/sessions/{session['id']}/sources",
        json={"name": "bad", "filePath": "exports/../../secrets.csv"},
    )
    assert r.status_code == 400
    assert r.json() == {
        "error": {"message": "`filePath` may not step outside the analytics data directory."}
    }

    r = await client.post(
        f"/api/v1/analytics/sessions/{session['id']}/sources",
        json={"name": "bad", "filePath": 12},
    )
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "`filePath` must be a string."}}

    r = await client.get(f"/api/v1/analytics/sessions/{session['id']}/sources")
    assert r.status_code == 200
    rows = r.json()["data"]
    assert [row["id"] for row in rows] == [windows_path["id"], plain["id"]]

    r = await client.get("/api/v1/analytics/sessions/ssn_missing0/sources")
    assert r.status_code == 404

    r = await client.delete(f"/api/v1/analytics/sources/{plain['id']}")
    assert r.status_code == 200
    assert r.json() == {"data": {"ok": True}}

    r = await client.delete(f"/api/v1/analytics/sources/{plain['id']}")
    assert r.status_code == 404


async def test_reports_lifecycle(client, email):
    await setup_site(client, email)
    session = await create_session(client)

    r = await client.post("/api/v1/analytics/reports", json={"title": "No html"})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Missing required field(s): html"}}

    r = await client.post("/api/v1/analytics/reports", json={"title": "T", "html": HTML})
    assert r.status_code == 201
    loose = r.json()["data"]
    assert loose["title"] == "T"
    assert loose["createdBy"] == "agent"
    assert loose["htmlBytes"] == len(HTML.encode("utf-8"))
    assert "html" not in loose
    assert "sessionId" not in loose

    r = await client.post(
        "/api/v1/analytics/reports",
        json={"title": "Bound", "html": HTML, "sessionId": session["id"], "createdBy": "user"},
    )
    assert r.status_code == 201
    bound = r.json()["data"]
    assert bound["sessionId"] == session["id"]
    assert bound["createdBy"] == "user"

    r = await client.post(
        "/api/v1/analytics/reports",
        json={"title": "Bad session", "html": HTML, "sessionId": "ssn_missing0"},
    )
    assert r.status_code == 404

    r = await client.get("/api/v1/analytics/reports")
    assert [row["id"] for row in r.json()["data"]] == [bound["id"], loose["id"]]

    r = await client.get("/api/v1/analytics/reports", params={"sessionId": session["id"]})
    assert [row["id"] for row in r.json()["data"]] == [bound["id"]]

    r = await client.get(f"/api/v1/analytics/reports/{bound['id']}")
    assert r.status_code == 200
    full = r.json()["data"]
    assert full["html"] == HTML
    assert "htmlBytes" not in full

    r = await client.get("/api/v1/analytics/reports/rpt_missing0")
    assert r.status_code == 404

    r = await client.put(f"/api/v1/analytics/reports/{loose['id']}", json={})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Nothing to update — send `title` and/or `html`."}}

    new_html = "<p>Rewritten</p>"
    r = await client.put(
        f"/api/v1/analytics/reports/{loose['id']}", json={"title": "T2", "html": new_html}
    )
    assert r.status_code == 200
    assert r.json()["data"]["title"] == "T2"
    assert r.json()["data"]["htmlBytes"] == len(new_html.encode("utf-8"))

    r = await client.put("/api/v1/analytics/reports/rpt_missing0", json={"title": "x"})
    assert r.status_code == 404

    r = await client.delete(f"/api/v1/analytics/reports/{loose['id']}")
    assert r.status_code == 200
    assert r.json() == {"data": {"ok": True}}

    r = await client.delete(f"/api/v1/analytics/reports/{loose['id']}")
    assert r.status_code == 404


async def test_report_html_must_be_self_contained(client, email):
    await setup_site(client, email)

    async def rejected(html):
        r = await client.post("/api/v1/analytics/reports", json={"title": "T", "html": html})
        assert r.status_code == 400, html
        return r.json()["error"]["message"]

    assert "an element that can load or send" in await rejected("<script>alert(1)</script>")
    assert "an element that can load or send" in await rejected("<iframe></iframe>")
    assert "http-equiv" in await rejected('<meta http-equiv="refresh" content="0">')
    assert "an attribute referencing another origin" in await rejected(
        '<a href="https://example.com">x</a>'
    )
    assert "a CSS url() to another origin" in await rejected(
        "<style>body{background:url(//cdn.example.com/x.png)}</style>"
    )
    assert "a CSS image-set() to another origin" in await rejected(
        "<style>body{background:image-set('//cdn.example.com/x.png')}</style>"
    )
    assert "a CSS @import" in await rejected("<style>@import 'x.css';</style>")

    r = await client.post("/api/v1/analytics/reports", json={"title": "T", "html": "   "})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Missing required field(s): html"}}

    r = await client.post("/api/v1/analytics/reports", json={"title": "T", "html": 5})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "`html` must be a non-empty string."}}

    big = "<p>" + ("x" * (8 * 1024 * 1024)) + "</p>"
    r = await client.post("/api/v1/analytics/reports", json={"title": "T", "html": big})
    assert r.status_code == 400
    assert "exceeds 8MB" in r.json()["error"]["message"]

    r = await client.put(
        "/api/v1/analytics/reports/rpt_missing0", json={"html": "<script></script>"}
    )
    assert r.status_code == 400


async def test_deleting_a_session_deletes_its_reports(client, email):
    await setup_site(client, email)
    session = await create_session(client)

    r = await client.post(
        "/api/v1/analytics/reports",
        json={"title": "Bound", "html": HTML, "sessionId": session["id"]},
    )
    assert r.status_code == 201
    bound = r.json()["data"]

    r = await client.post("/api/v1/analytics/reports", json={"title": "Loose", "html": HTML})
    loose = r.json()["data"]

    r = await client.post(
        f"/api/v1/analytics/sessions/{session['id']}/sources", json={"name": "pages.csv"}
    )
    assert r.status_code == 201

    r = await client.delete(f"/api/v1/analytics/sessions/{session['id']}")
    assert r.status_code == 200

    r = await client.get(f"/api/v1/analytics/reports/{bound['id']}")
    assert r.status_code == 404

    r = await client.get(f"/api/v1/analytics/reports/{loose['id']}")
    assert r.status_code == 200

    r = await client.get("/api/v1/analytics/workspace")
    assert r.json()["data"]["sources"] == []


async def test_workspace(client, email):
    await setup_site(client, email)

    r = await client.get("/api/v1/analytics/workspace")
    assert r.status_code == 200
    assert r.json()["data"] == {"sessions": [], "sources": [], "reports": []}

    session = await create_session(client, title="One")
    await client.post(
        f"/api/v1/analytics/sessions/{session['id']}/sources",
        json={"name": "pages.csv", "filePath": "exports/pages.csv"},
    )
    await client.post(
        "/api/v1/analytics/reports",
        json={"title": "R", "html": HTML, "sessionId": session["id"]},
    )

    r = await client.get("/api/v1/analytics/workspace")
    body = r.json()["data"]
    assert [s["id"] for s in body["sessions"]] == [session["id"]]
    assert body["sources"][0]["filePath"] == "exports/pages.csv"
    assert body["reports"][0]["htmlBytes"] == len(HTML.encode("utf-8"))
    assert "html" not in body["reports"][0]


async def test_analytics_is_scoped_to_user_and_site(client, email):
    await setup_site(client, email)
    session = await create_session(client, title="On the first site")

    r = await client.post("/api/v1/sites", json={"domain": "other.com", "name": "Other"})
    other = r.json()["data"]

    r = await client.get(
        f"/api/v1/analytics/sessions/{session['id']}", headers={"x-meelu-site": other["id"]}
    )
    assert r.status_code == 404

    r = await client.get("/api/v1/analytics/sessions", headers={"x-meelu-site": other["id"]})
    assert r.json()["data"] == []

    r = await client.get("/api/v1/analytics/sessions", headers={"x-meelu-site": "site_nope0000"})
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "No website site_nope0000 in this workspace."}}
