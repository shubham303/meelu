from tests.conftest import signup

HTML = "<h1>Report</h1><p>All local, no network.</p>"


async def setup_site(client, email):
    await signup(client, email)
    r = await client.post("/api/v1/sites", json={"domain": "example.com", "name": "Example"})
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def create_report(client, title, desk="analytics", **extra):
    r = await client.post(
        "/api/v1/reports", json={"desk": desk, "title": title, "html": HTML, **extra}
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_reports_lifecycle(client, email):
    await setup_site(client, email)

    r = await client.post("/api/v1/reports", json={"desk": "analytics", "title": "No html"})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Missing required field(s): html"}}

    r = await client.post("/api/v1/reports", json={"title": "No desk", "html": HTML})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Missing required field(s): desk"}}

    r = await client.post("/api/v1/reports", json={"desk": "pages", "title": "T", "html": HTML})
    assert r.status_code == 400
    assert "Invalid desk" in r.json()["error"]["message"]

    loose = await create_report(client, "Clicks drop in March")
    assert loose["createdBy"] == "agent"
    assert loose["desk"] == "analytics"
    assert loose["htmlBytes"] == len(HTML.encode("utf-8"))
    assert "html" not in loose
    assert "sessionId" not in loose

    mine = await create_report(client, "Weekly traffic", createdBy="user")
    assert mine["createdBy"] == "user"

    audit = await create_report(client, "Audit summary", desk="technical-seo")
    assert audit["desk"] == "technical-seo"

    r = await client.get("/api/v1/reports")
    assert [row["id"] for row in r.json()["data"]] == [audit["id"], mine["id"], loose["id"]]

    r = await client.get("/api/v1/reports", params={"desk": "technical-seo"})
    assert [row["id"] for row in r.json()["data"]] == [audit["id"]]

    r = await client.get("/api/v1/reports", params={"desk": "seo"})
    assert r.json()["data"] == []

    r = await client.get("/api/v1/reports", params={"q": "march"})
    assert [row["id"] for row in r.json()["data"]] == [loose["id"]]

    r = await client.get(f"/api/v1/reports/{loose['id']}")
    assert r.status_code == 200
    full = r.json()["data"]
    assert full["html"] == HTML
    assert full["desk"] == "analytics"
    assert "htmlBytes" not in full

    r = await client.get("/api/v1/reports/rpt_missing0")
    assert r.status_code == 404

    r = await client.put(f"/api/v1/reports/{loose['id']}", json={})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "Nothing to update — send `title` and/or `html`."}}

    new_html = "<p>Rewritten</p>"
    r = await client.put(f"/api/v1/reports/{loose['id']}", json={"title": "T2", "html": new_html})
    assert r.status_code == 200
    assert r.json()["data"]["title"] == "T2"
    assert r.json()["data"]["htmlBytes"] == len(new_html.encode("utf-8"))

    r = await client.put("/api/v1/reports/rpt_missing0", json={"title": "x"})
    assert r.status_code == 404

    r = await client.delete(f"/api/v1/reports/{loose['id']}")
    assert r.status_code == 200
    assert r.json() == {"data": {"id": loose["id"], "deleted": True}}

    r = await client.delete(f"/api/v1/reports/{loose['id']}")
    assert r.status_code == 404


async def test_report_html_must_be_self_contained(client, email):
    await setup_site(client, email)

    async def rejected(html):
        r = await client.post(
            "/api/v1/reports", json={"desk": "analytics", "title": "T", "html": html}
        )
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

    r = await client.post(
        "/api/v1/reports", json={"desk": "analytics", "title": "T", "html": "   "}
    )
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "`html` must be a non-empty string."}}

    r = await client.post("/api/v1/reports", json={"desk": "analytics", "title": "T", "html": 5})
    assert r.status_code == 400
    assert r.json() == {"error": {"message": "`html` must be a non-empty string."}}

    big = "<p>" + ("x" * (8 * 1024 * 1024)) + "</p>"
    r = await client.post("/api/v1/reports", json={"desk": "analytics", "title": "T", "html": big})
    assert r.status_code == 400
    assert "exceeds 8MB" in r.json()["error"]["message"]

    r = await client.put("/api/v1/reports/rpt_missing0", json={"html": "<script></script>"})
    assert r.status_code == 400


async def test_reports_are_scoped_to_user_and_site(client, email):
    await setup_site(client, email)
    report = await create_report(client, "On the first site")

    r = await client.post("/api/v1/sites", json={"domain": "other.com", "name": "Other"})
    other = r.json()["data"]

    r = await client.get(f"/api/v1/reports/{report['id']}", headers={"x-meelu-site": other["id"]})
    assert r.status_code == 404

    r = await client.get("/api/v1/reports", headers={"x-meelu-site": other["id"]})
    assert r.json()["data"] == []

    r = await client.get("/api/v1/reports", headers={"x-meelu-site": "site_nope0000"})
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "No website site_nope0000 in this workspace."}}
