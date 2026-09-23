from datetime import UTC, datetime

from tests.conftest import signup
from tests.integration.technical_seo.conftest import seed_pages, set_site_facts, user_id_of

ORIGIN = "https://audit.example.com"

CLEAN_ROBOTS = "User-agent: *\nDisallow: /admin\nSitemap: https://audit.example.com/sitemap.xml\n"


def page(url, **facts):
    return {"url": f"{ORIGIN}{url}", **facts}


def defect_pages():
    return [
        page(
            "/",
            kind="home",
            in_sitemap=True,
            inlinks=3,
            depth=0,
            title="Audit Example Home Page",
            meta_description="The home page of the audit example site, written to sit inside the snippet limits.",
            h1=["Audit Example"],
            canonical=f"{ORIGIN}/",
            schema_types=["Organization"],
            out_links=[
                {"url": f"{ORIGIN}/dead", "anchor": "Dead"},
                {"url": f"{ORIGIN}/redirected", "anchor": "Moved"},
                {"url": f"{ORIGIN}/contact", "anchor": "Contact"},
            ],
            external_links=[
                {"url": "https://www.linkedin.com/company/audit", "anchor": "LinkedIn"}
            ],
        ),
        page("/boom", status=500, shallow=True, inlinks=1),
        page("/dead", status=404, in_sitemap=True, shallow=True),
        page("/redirected", status=301, in_sitemap=True, redirect_hops=2, shallow=True),
        page(
            "/noindex-linked",
            in_sitemap=True,
            inlinks=2,
            robots_directives="noindex, follow",
            title="A Page Deliberately Marked Noindex",
            meta_description="This page is marked noindex on purpose so the audit has something to complain about.",
            h1=["Noindex"],
            canonical=f"{ORIGIN}/noindex-linked",
        ),
        page("/blocked", blocked_by_robots=True, in_sitemap=True, inlinks=1, shallow=True),
        page(
            "/first-twin",
            in_sitemap=True,
            inlinks=1,
            title="Two Pages Share This Very Title",
            meta_description="The first of two pages that were given exactly the same title tag by mistake.",
            h1=["Twin One"],
            canonical=f"{ORIGIN}/first-twin",
        ),
        page(
            "/second-twin",
            in_sitemap=True,
            inlinks=1,
            title="Two Pages Share This Very Title",
            meta_description="The second of two pages that were given exactly the same title tag by mistake.",
            h1=["Twin Two"],
            canonical=f"{ORIGIN}/second-twin",
        ),
        page(
            "/orphan",
            in_sitemap=True,
            inlinks=0,
            title="Nothing On The Site Links Here",
            meta_description="An orphan page that the sitemap lists although no other page links to it at all.",
            h1=["Orphan"],
            canonical=f"{ORIGIN}/orphan",
        ),
    ]


async def prepare(client, email, robots=CLEAN_ROBOTS):
    await signup(client, email)
    user_id = await user_id_of(email)
    r = await client.post(
        "/api/v1/sites", json={"domain": "audit.example.com", "name": "Audit Example"}
    )
    assert r.status_code == 201, r.text
    site = r.json()["data"]

    now = datetime.now(UTC)
    await set_site_facts(
        site["id"],
        robots_txt=robots,
        robots_status=200,
        robots_fetched_at=now,
        last_crawled_at=now,
        sitemap_urls=[f"{ORIGIN}/sitemap.xml"],
        sitemap_url_count=1,
        sitemap_at_root=True,
    )
    pages = await seed_pages(site["id"], user_id, defect_pages())
    return site, pages


def by_kind(groups):
    return {g["kind"]: g for g in groups}


async def test_run_audit_finds_the_seeded_defects(client, email):
    site, pages = await prepare(client, email)

    r = await client.post("/api/v1/site/technical-seo/run-audit", json={})
    assert r.status_code == 201, r.text
    body = r.json()["data"]

    assert body["checks"] == 213
    assert body["run"]["rulesRun"] == 213
    assert body["run"]["trigger"] == "user"
    assert body["run"]["finishedAt"] is not None
    assert body["run"]["siteIssuesFound"] == 0
    assert body["site"] == {"open": 0, "rejected": 0}
    assert body["openSiteIssues"] == []

    groups = by_kind(body["openPageIssues"])

    expected = {
        "robots-blocked-but-linked": ("p0", 1),
        "server-error": ("p0", 1),
        "noindex-but-linked": ("p1", 1),
        "sitemap-dead-page": ("p2", 1),
        "sitemap-redirect": ("p2", 1),
        "redirect-chain": ("p2", 1),
        "duplicate-title": ("p2", 2),
        "orphan-page": ("p2", 1),
        "broken-internal-link": ("p2", 1),
        "internal-link-to-redirect": ("p2", 1),
        "home-missing-terms-link": ("p3", 1),
    }
    assert "home-missing-contact-link" not in groups
    assert "home-missing-social-links" not in groups
    for kind, (severity, pages_hit) in expected.items():
        assert kind in groups, f"{kind} missing from {sorted(groups)}"
        assert groups[kind]["severity"] == severity, kind
        assert groups[kind]["pages"] == pages_hit, kind
        assert groups[kind]["matched"] == pages_hit, kind
        assert groups[kind]["scope"] == "pages"
        assert groups[kind]["state"] == "open"

    assert groups["duplicate-title"]["examples"] == [
        f"{ORIGIN}/first-twin",
        f"{ORIGIN}/second-twin",
    ]
    assert groups["server-error"]["examples"] == [f"{ORIGIN}/boom"]

    severities = [g["severity"] for g in body["openPageIssues"]]
    assert severities == sorted(severities)

    assert body["pages"]["open"] == body["run"]["pageIssuesFound"]
    assert body["pages"]["rejected"] == 0


async def test_site_rules_land_as_site_issues(client, email):
    robots = (
        "User-agent: Googlebot\nDisallow: /\n\n"
        "User-agent: OAI-SearchBot\nDisallow: /\n\n"
        "User-agent: Claude-User\nDisallow: /\n"
    )
    site, _ = await prepare(client, email, robots=robots)

    r = await client.post("/api/v1/site/technical-seo/run-audit", json={"trigger": "agent"})
    assert r.status_code == 201, r.text
    body = r.json()["data"]

    assert body["run"]["trigger"] == "agent"
    kinds = {i["kind"]: i["severity"] for i in body["openSiteIssues"]}
    assert kinds["googlebot-blocked"] == "p0"
    assert kinds["ai-search-crawler-blocked"] == "p1"
    assert kinds["ai-user-fetch-blocked"] == "p1"
    assert kinds["ai-permissions-inconsistent"] == "p1"
    assert "robots-no-sitemap" in kinds
    assert body["site"]["open"] == len(kinds)
    assert body["run"]["siteIssuesFound"] == len(kinds)

    r = await client.get("/api/v1/site/technical-seo/issues", params={"severity": "p0"})
    assert r.status_code == 200
    listed = r.json()["data"]
    assert listed["total"] == 1
    assert listed["issues"][0]["kind"] == "googlebot-blocked"
    assert listed["issues"][0]["state"] == "open"
    assert "rejectionReason" not in listed["issues"][0]


async def test_page_issue_listing_and_filters(client, email):
    site, pages = await prepare(client, email)
    await client.post("/api/v1/site/technical-seo/run-audit", json={})

    r = await client.get(
        "/api/v1/site/technical-seo/page-issues", params={"kind": "duplicate-title"}
    )
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["total"] == 2
    assert body["shown"] == 2
    assert body["offset"] == 0
    assert [i["url"] for i in body["issues"]] == [
        f"{ORIGIN}/first-twin",
        f"{ORIGIN}/second-twin",
    ]
    assert body["issues"][0]["matchedPages"] == 2
    assert body["issues"][0]["pageId"] == pages[f"{ORIGIN}/first-twin"]

    r = await client.get(
        "/api/v1/site/technical-seo/page-issues",
        params={"url": f"{ORIGIN}/boom", "kind": "server-error"},
    )
    assert r.json()["data"]["total"] == 1

    r = await client.get(
        "/api/v1/site/technical-seo/page-issues",
        params={"pageId": pages[f"{ORIGIN}/dead"], "kind": "sitemap-dead-page"},
    )
    assert r.json()["data"]["total"] == 1

    r = await client.get(
        "/api/v1/site/technical-seo/page-issues", params={"kind": "duplicate-title", "limit": 1}
    )
    body = r.json()["data"]
    assert body["total"] == 2
    assert body["shown"] == 1

    r = await client.get("/api/v1/site/technical-seo/page-issues", params={"severity": "p0"})
    assert {i["kind"] for i in r.json()["data"]["issues"]} == {
        "robots-blocked-but-linked",
        "server-error",
    }

    r = await client.get("/api/v1/site/technical-seo/page-issues", params={"state": "sideways"})
    assert r.status_code == 400
    assert r.json() == {
        "error": {"message": 'Invalid state "sideways". Allowed values: open, rejected.'}
    }


async def test_csv_export_columns_and_filename(client, email):
    await prepare(client, email)
    await client.post("/api/v1/site/technical-seo/run-audit", json={})

    r = await client.get(
        "/api/v1/site/technical-seo/download", params={"kind": "server-error,duplicate-title"}
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "text/csv; charset=utf-8"
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    assert (
        r.headers["content-disposition"]
        == f'attachment; filename="audit-example-com-open-issues-{stamp}.csv"'
    )
    assert r.headers["cache-control"] == "no-store"

    lines = r.text.strip().split("\n")
    assert lines[0] == "kind,severity,scope,state,url,issue"
    assert len(lines) == 4
    assert lines[1].startswith(f'server-error,p0,pages,open,{ORIGIN}/boom,"')
    assert lines[2].startswith(f"duplicate-title,p2,pages,open,{ORIGIN}/first-twin,")
    assert lines[3].startswith(f"duplicate-title,p2,pages,open,{ORIGIN}/second-twin,")

    r = await client.get("/api/v1/site/technical-seo/download", params={"state": "rejected"})
    assert r.text == "kind,severity,scope,state,url,issue\n\n"


async def test_decisions_carry_forward_into_the_next_run(client, email):
    await prepare(client, email)

    r = await client.post("/api/v1/site/technical-seo/run-audit", json={})
    first_run = r.json()["data"]["run"]["id"]

    r = await client.get("/api/v1/site/technical-seo/page-issues", params={"kind": "orphan-page"})
    issue = r.json()["data"]["issues"][0]

    r = await client.patch(
        f"/api/v1/site/technical-seo/page-issues/{issue['id']}",
        json={"state": "rejected", "rejectionReason": "That page is meant to be unlinked."},
    )
    assert r.status_code == 200
    rejected = r.json()["data"]
    assert rejected["state"] == "rejected"
    assert rejected["rejectionReason"] == "That page is meant to be unlinked."
    assert rejected["reviewedAt"] is not None

    r = await client.post("/api/v1/site/technical-seo/run-audit", json={})
    body = r.json()["data"]
    assert body["run"]["id"] != first_run
    assert "orphan-page" not in by_kind(body["openPageIssues"])
    assert body["pages"]["rejected"] == 1

    r = await client.get(
        "/api/v1/site/technical-seo/page-issues",
        params={"kind": "orphan-page", "state": "rejected"},
    )
    carried = r.json()["data"]["issues"][0]
    assert carried["runId"] == body["run"]["id"]
    assert carried["rejectionReason"] == "That page is meant to be unlinked."

    r = await client.patch(
        f"/api/v1/site/technical-seo/page-issues/{carried['id']}", json={"state": "open"}
    )
    assert r.json()["data"]["state"] == "open"
    assert "rejectionReason" not in r.json()["data"]

    r = await client.post("/api/v1/site/technical-seo/run-audit", json={})
    assert "orphan-page" in by_kind(r.json()["data"]["openPageIssues"])


async def test_summary_and_groups_read_the_latest_run(client, email):
    await prepare(client, email)
    await client.post("/api/v1/site/technical-seo/run-audit", json={})

    r = await client.get("/api/v1/site/technical-seo/summary")
    assert r.status_code == 200
    summary = r.json()["data"]
    assert set(summary) == {"run", "site", "pages", "openSiteIssues", "openPageIssues"}

    r = await client.get("/api/v1/site/technical-seo/groups")
    groups = r.json()["data"]
    assert groups == summary["openPageIssues"]

    r = await client.get(
        "/api/v1/site/technical-seo/groups", params={"runId": summary["run"]["id"]}
    )
    assert r.json()["data"] == groups

    r = await client.get("/api/v1/site/technical-seo/groups", params={"state": "rejected"})
    assert r.json()["data"] == []

    r = await client.get("/api/v1/site/technical-seo/summary", params={"runId": "sar_missing0"})
    assert r.status_code == 404
    assert r.json() == {"error": {"message": "No such technical SEO run for this website."}}


async def test_summary_before_any_audit(client, email):
    await signup(client, email)
    r = await client.post("/api/v1/sites", json={"domain": "fresh.example.com", "name": "Fresh"})
    assert r.status_code == 201

    r = await client.get("/api/v1/site/technical-seo/summary")
    assert r.status_code == 404
    assert r.json() == {
        "error": {
            "message": "This website has not been audited yet — run the technical SEO check first."
        }
    }
