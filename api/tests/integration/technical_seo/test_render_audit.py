from datetime import UTC, datetime
from typing import Any

from tests.conftest import signup
from tests.integration.technical_seo.conftest import seed_pages, set_site_facts, user_id_of

ORIGIN = "https://spa.example.com"

RENDER_DEFAULTS: dict[str, Any] = {
    "device": "desktop",
    "render_error": None,
    "user_agent_profile": "googlebot",
    "h1": [],
    "word_count": 0,
    "internal_links": 0,
    "schema_types": [],
    "console_errors": 0,
    "console_samples": [],
    "failed_requests": 0,
    "failed_samples": [],
    "blocked_assets": 0,
    "blocked_samples": [],
    "js_bytes": 0,
    "total_bytes": 0,
    "request_count": 0,
    "third_party_hosts": [],
}


async def seed_renders(site_id: str, user_id: str, renders: list[dict[str, Any]]) -> None:
    from src.core.database import SessionLocal
    from src.core.ids import uid
    from src.render_jobs.models.site_page_render import SitePageRender

    async with SessionLocal() as db:
        now = datetime.now(UTC)
        for render in renders:
            db.add(
                SitePageRender(
                    id=uid("spr"),
                    user_id=user_id,
                    site_id=site_id,
                    rendered_at=now,
                    created_at=now,
                    updated_at=now,
                    **{**RENDER_DEFAULTS, **render},
                )
            )
        await db.commit()


def page(url, **facts):
    return {
        "url": f"{ORIGIN}{url}",
        "in_sitemap": True,
        "inlinks": 2,
        "depth": 1,
        "title": "A perfectly ordinary title for testing",
        "meta_description": "A description long enough to sit inside the limits the checks apply.",
        "h1": ["Heading"],
        "canonical": f"{ORIGIN}{url}",
        "schema_types": ["WebPage"],
        "word_count": 500,
        "links": [{"url": f"{ORIGIN}/", "anchor": "Home"}],
        **facts,
    }


def raw_pages():
    return [
        page("/", page_type="money", depth=0),
        page("/shell", title=None, h1=[], schema_types=[], word_count=8, canonical=None),
        page("/static"),
        page("/redirects"),
        page("/slow"),
        page("/unrendered", title=None, word_count=3),
        page("/broken-render"),
        page("/noindex-by-js"),
        page("/m-shell", word_count=6),
        page("/m-menu"),
        page("/m-wide"),
        page("/m-head"),
    ]


def renders(pages: dict[str, str]):
    return [
        {
            "page_id": pages[f"{ORIGIN}/"],
            "title": "Home",
            "h1": ["Heading"],
            "word_count": 520,
            "internal_links": 1,
            "schema_types": ["WebPage"],
            "canonical": f"{ORIGIN}/",
        },
        {
            "page_id": pages[f"{ORIGIN}/shell"],
            "title": "Rendered by React",
            "h1": ["Welcome"],
            "canonical": f"{ORIGIN}/shell",
            "word_count": 900,
            "internal_links": 40,
            "schema_types": ["Product"],
            "console_errors": 3,
            "failed_requests": 2,
            "blocked_assets": 1,
            "js_bytes": 2_000_000,
            "request_count": 200,
            "third_party_hosts": [f"h{n}.example.net" for n in range(12)],
        },
        {
            "page_id": pages[f"{ORIGIN}/static"],
            "title": "A perfectly ordinary title for testing",
            "h1": ["Heading"],
            "word_count": 500,
            "internal_links": 1,
            "schema_types": ["WebPage"],
            "canonical": f"{ORIGIN}/static",
        },
        {
            "page_id": pages[f"{ORIGIN}/redirects"],
            "final_url": f"{ORIGIN}/elsewhere",
            "main_frame_navigations": 1,
            "title": "Moved",
            "word_count": 500,
            "canonical": f"{ORIGIN}/elsewhere",
        },
        {
            "page_id": pages[f"{ORIGIN}/slow"],
            "title": "Slow",
            "word_count": 500,
            "canonical": f"{ORIGIN}/slow",
        },
        {
            "page_id": pages[f"{ORIGIN}/broken-render"],
            "render_error": "timed out",
            "word_count": 5000,
            "internal_links": 500,
        },
        {
            "page_id": pages[f"{ORIGIN}/noindex-by-js"],
            "title": "Hidden",
            "word_count": 500,
            "canonical": f"{ORIGIN}/noindex-by-js",
            "robots_directives": "noindex, nofollow",
        },
        {
            "page_id": pages[f"{ORIGIN}/m-shell"],
            "device": "mobile",
            "title": "A perfectly ordinary title for testing",
            "canonical": f"{ORIGIN}/m-shell",
            "word_count": 900,
            "internal_links": 4,
        },
        {
            "page_id": pages[f"{ORIGIN}/m-menu"],
            "device": "mobile",
            "title": "A perfectly ordinary title for testing",
            "canonical": f"{ORIGIN}/m-menu",
            "word_count": 500,
            "internal_links": 40,
            "hidden_word_count": 300,
            "hidden_internal_links": 18,
        },
        {
            "page_id": pages[f"{ORIGIN}/m-wide"],
            "device": "mobile",
            "title": "A perfectly ordinary title for testing",
            "canonical": f"{ORIGIN}/m-wide",
            "word_count": 500,
            "viewport_overflow_px": 140,
            "small_tap_targets": 9,
        },
        {
            "page_id": pages[f"{ORIGIN}/m-head"],
            "device": "desktop",
            "title": "Desktop title",
            "canonical": f"{ORIGIN}/m-head",
            "word_count": 500,
        },
        {
            "page_id": pages[f"{ORIGIN}/m-head"],
            "device": "mobile",
            "title": "Mobile title",
            "canonical": f"{ORIGIN}/m-head?m=1",
            "word_count": 500,
            "robots_directives": "noindex",
        },
    ]


async def prepare(client, email):
    await signup(client, email)
    user_id = await user_id_of(email)
    r = await client.post("/api/v1/sites", json={"domain": "spa.example.com", "name": "SPA"})
    assert r.status_code == 201, r.text
    site = r.json()["data"]
    now = datetime.now(UTC)
    await set_site_facts(
        site["id"],
        robots_txt="User-agent: *\nSitemap: https://spa.example.com/sitemap.xml\n",
        robots_status=200,
        robots_fetched_at=now,
        last_crawled_at=now,
        sitemap_urls=[f"{ORIGIN}/sitemap.xml"],
        sitemap_url_count=1,
        sitemap_at_root=True,
    )
    pages = await seed_pages(site["id"], user_id, raw_pages())
    return site, user_id, pages


def by_kind(groups):
    return {g["kind"]: g for g in groups}


async def test_no_renders_means_no_rendering_issues(client, email):
    await prepare(client, email)
    r = await client.post("/api/v1/site/technical-seo/run-audit", json={})
    assert r.status_code == 201, r.text
    body = r.json()["data"]
    assert [g for g in body["openPageIssues"] if g["issueType"] != "static"] == []
    assert [i for i in body["openSiteIssues"] if i["issueType"] != "static"] == []

    r = await client.get("/api/v1/site/technical-seo/page-issues", params={"type": "desktop"})
    assert r.status_code == 200
    assert r.json()["pagination"]["total"] == 0


async def test_rendering_rules_fire_only_on_rendered_pages(client, email):
    site, user_id, pages = await prepare(client, email)
    await seed_renders(site["id"], user_id, renders(pages))

    r = await client.post("/api/v1/site/technical-seo/run-audit", json={})
    assert r.status_code == 201, r.text
    body = r.json()["data"]
    groups = by_kind(body["openPageIssues"])

    shell = f"{ORIGIN}/shell"
    expected_on_shell = {
        "js-only-content": "p1",
        "js-only-title": "p1",
        "js-only-canonical": "p2",
        "js-only-h1": "p2",
        "js-only-schema": "p2",
        "js-only-links": "p1",
        "render-blocked-assets": "p1",
        "render-console-errors": "p2",
        "render-failed-requests": "p2",
        "heavy-javascript": "p3",
        "too-many-requests": "p3",
        "third-party-bloat": "p3",
    }
    for kind, severity in expected_on_shell.items():
        assert kind in groups, f"{kind} missing from {sorted(groups)}"
        assert groups[kind]["issueType"] == "desktop", kind
        assert groups[kind]["severity"] == severity, kind
        assert shell in groups[kind]["examples"], kind

    assert groups["client-side-redirect"]["examples"] == [f"{ORIGIN}/redirects"]
    assert groups["canonical-changed-by-js"]["examples"] == [f"{ORIGIN}/redirects"]
    assert groups["robots-changed-by-js"]["examples"] == [f"{ORIGIN}/noindex-by-js"]

    for kind, group in groups.items():
        if group["issueType"] == "desktop":
            assert f"{ORIGIN}/unrendered" not in group["examples"], kind
            assert f"{ORIGIN}/broken-render" not in group["examples"], kind
            assert f"{ORIGIN}/static" not in group["examples"], kind

    assert groups["missing-title"]["issueType"] == "static"
    assert set(groups["missing-title"]["examples"]) == {shell, f"{ORIGIN}/unrendered"}

    site_kinds = {i["kind"]: i for i in body["openSiteIssues"]}
    assert "js-dependent-site" not in site_kinds
    assert "mobile-differs-from-desktop" not in site_kinds

    expected_mobile = {
        "mobile-js-only-content": ("p1", f"{ORIGIN}/m-shell"),
        "mobile-hidden-content": ("p1", f"{ORIGIN}/m-menu"),
        "mobile-hidden-links": ("p1", f"{ORIGIN}/m-menu"),
        "mobile-viewport-overflow": ("p2", f"{ORIGIN}/m-wide"),
        "mobile-small-tap-targets": ("p3", f"{ORIGIN}/m-wide"),
        "mobile-title-differs": ("p2", f"{ORIGIN}/m-head"),
        "mobile-canonical-differs": ("p1", f"{ORIGIN}/m-head"),
        "mobile-noindex-differs": ("p0", f"{ORIGIN}/m-head"),
    }
    for kind, (severity, url) in expected_mobile.items():
        assert kind in groups, f"{kind} missing from {sorted(groups)}"
        assert groups[kind]["issueType"] == "mobile", kind
        assert groups[kind]["severity"] == severity, kind
        assert groups[kind]["examples"] == [url], kind
    for kind, group in groups.items():
        if group["issueType"] == "mobile":
            assert shell not in group["examples"], kind
            assert f"{ORIGIN}/static" not in group["examples"], kind

    r = await client.get("/api/v1/site/technical-seo/page-issues", params={"type": "mobile"})
    assert r.json()["pagination"]["total"] == 8
    assert all(i["issueType"] == "mobile" for i in r.json()["data"])

    r = await client.get("/api/v1/site/technical-seo/page-issues", params={"type": "desktop"})
    assert r.status_code == 200
    listed = r.json()
    assert listed["pagination"]["total"] > 0
    assert all(i["issueType"] == "desktop" for i in listed["data"])

    r = await client.get("/api/v1/site/technical-seo/page-issues", params={"type": "static"})
    assert all(i["issueType"] == "static" for i in r.json()["data"])

    r = await client.get("/api/v1/site/technical-seo/download", params={"kind": "js-only-title"})
    assert r.status_code == 200
    lines = r.text.strip().split("\n")
    assert lines[0] == "kind,severity,scope,type,state,url,issue"
    assert lines[1].startswith(f"js-only-title,p1,pages,desktop,open,{shell},")


async def test_site_is_flagged_when_most_rendered_pages_depend_on_js(client, email):
    site, user_id, pages = await prepare(client, email)
    shells = [
        {"page_id": pages[url], "title": "Rendered", "word_count": 3000, "internal_links": 1}
        for url in (
            f"{ORIGIN}/",
            f"{ORIGIN}/shell",
            f"{ORIGIN}/static",
            f"{ORIGIN}/redirects",
            f"{ORIGIN}/slow",
        )
    ]
    await seed_renders(site["id"], user_id, shells)

    r = await client.post("/api/v1/site/technical-seo/run-audit", json={})
    assert r.status_code == 201, r.text
    body = r.json()["data"]
    site_kinds = {i["kind"]: i for i in body["openSiteIssues"]}
    assert "js-dependent-site" in site_kinds
    assert site_kinds["js-dependent-site"]["severity"] == "p0"
    assert site_kinds["js-dependent-site"]["issueType"] == "desktop"
    assert "5 of the 5 pages" in site_kinds["js-dependent-site"]["issue"]

    r = await client.get("/api/v1/site/technical-seo/issues", params={"type": "desktop"})
    assert r.status_code == 200
    assert [i["kind"] for i in r.json()["data"]] == ["js-dependent-site"]


async def test_site_is_flagged_when_mobile_head_differs_from_desktop(client, email):
    site, user_id, pages = await prepare(client, email)
    rows = []
    for n, url in enumerate(list(pages)[:6]):
        rows.append(
            {
                "page_id": pages[url],
                "device": "desktop",
                "title": "Same",
                "canonical": url,
                "word_count": 500,
            }
        )
        rows.append(
            {
                "page_id": pages[url],
                "device": "mobile",
                "title": "Same" if n == 0 else "Different on mobile",
                "canonical": url,
                "word_count": 500,
            }
        )
    await seed_renders(site["id"], user_id, rows)

    r = await client.post("/api/v1/site/technical-seo/run-audit", json={})
    assert r.status_code == 201, r.text
    site_kinds = {i["kind"]: i for i in r.json()["data"]["openSiteIssues"]}
    assert "mobile-differs-from-desktop" in site_kinds
    assert site_kinds["mobile-differs-from-desktop"]["issueType"] == "mobile"
    assert "5 of the 6 pages" in site_kinds["mobile-differs-from-desktop"]["issue"]

    r = await client.get("/api/v1/site/technical-seo/issues", params={"type": "mobile"})
    assert [i["kind"] for i in r.json()["data"]] == ["mobile-differs-from-desktop"]


CLEAN_V2: dict[str, Any] = {
    "settle_reason": "idle",
    "status": 200,
    "title": "A perfectly ordinary title for testing",
    "meta_description": "A description long enough to sit inside the limits the checks apply.",
    "h1": ["Heading"],
    "word_count": 500,
    "visible_word_count": 500,
    "internal_links": 1,
    "internal_link_urls": [f"{ORIGIN}/"],
    "schema_types": ["WebPage"],
    "schema_hashes": ["abc123"],
    "canonical_count": 1,
    "title_count": 1,
    "description_count": 1,
    "viewport_meta": "width=device-width, initial-scale=1",
}


def v2_row(pages, url, device, **over):
    return {
        **CLEAN_V2,
        "page_id": pages[url],
        "device": device,
        "canonical": url,
        "canonical_hrefs": [url],
        "final_url": url,
        **over,
    }


SOFT_OVERRIDES: dict[str, Any] = {
    "soft404_signal": True,
    "visible_word_count": 20,
    "h1": [],
    "exception_count": 1,
    "word_count": 50,
    "internal_links": 0,
    "internal_link_urls": [],
    "uncrawlable_nav_anchors": 1,
    "hashbang_links": 1,
    "dangling_fragment_links": 5,
    "main_frame_navigations": 0,
    "load_more_control": True,
    "pagination_links": False,
    "images_without_src_above_fold": 1,
    "shadow_dom_words": 200,
    "service_worker": True,
}

SOFT_KINDS = {
    "soft-404-after-render": "p0",
    "rendered-body-empty": "p0",
    "render-exception-with-thin-content": "p0",
    "content-lost-after-render": "p1",
    "links-lost-after-render": "p1",
    "uncrawlable-anchors-after-render": "p1",
    "old-ajax-crawling-scheme": "p1",
    "dangling-fragment-links": "p2",
    "url-changed-by-history-api": "p1",
    "interaction-gated-content": "p2",
    "images-without-src-after-render": "p1",
    "shadow-dom-content-unslotted": "p2",
    "service-worker-registered": "p3",
}

HEALTH_OVERRIDES: dict[str, Any] = {
    "failed_data_requests": 1,
    "failed_scripts": 1,
    "cors_errors": 1,
    "settle_reason": "timeout",
    "pending_requests": 3,
    "websocket_used": True,
    "mixed_content_active": 1,
    "mixed_content_passive": 1,
    "document_bytes": 3_000_000,
    "largest_resource_bytes": 3_000_000,
    "html_bytes": 3_000_000,
    "overlay_coverage": 0.6,
}

HEALTH_KINDS = {
    "failed-data-request": "p1",
    "failed-first-party-script": "p1",
    "cors-blocked-request": "p1",
    "network-never-idle": "p2",
    "websocket-transport-used": "p2",
    "mixed-content-active": "p1",
    "mixed-content-passive": "p3",
    "document-over-2mb": "p0",
    "resource-over-2mb": "p1",
    "rendered-html-over-2mb": "p1",
}

META_OVERRIDES: dict[str, Any] = {
    "schema_types": ["Product"],
    "schema_hashes": ["dup", "dup"],
    "schema_invalid_blocks": 1,
    "canonical": "/relative",
    "canonical_count": 2,
    "robots_meta_contents": ["index, follow", "noindex"],
    "robots_directives": "nofollow",
    "title": "Changed by a script",
    "meta_description": "A different description written by a script.",
    "h1": ["Other heading"],
    "title_count": 2,
    "description_count": 2,
    "hreflang_invalid": 1,
    "template_tokens_head": 1,
    "template_tokens_body": 3,
    "images": [{"src": f"{ORIGIN}/injected.png"}],
    "external_link_hosts": [f"w{n}.example.org" for n in range(5)],
    "plugin_content": 1,
}

META_KINDS = {
    "schema-changed-by-js": "p1",
    "schema-duplicated-after-render": "p2",
    "schema-invalid-after-render": "p1",
    "canonical-conflict-after-render": "p0",
    "canonical-invalid-after-render": "p1",
    "robots-directives-conflict-after-render": "p1",
    "nofollow-changed-by-js": "p1",
    "title-modified-by-js": "p1",
    "meta-description-modified-by-js": "p2",
    "h1-modified-by-js": "p2",
    "title-duplicated-after-render": "p2",
    "description-duplicated-after-render": "p2",
    "hreflang-changed-by-js": "p2",
    "hreflang-invalid-after-render": "p2",
    "unrendered-template-tokens": "p1",
    "unrendered-template-tokens-body": "p2",
    "js-injected-images-missing-alt": "p2",
    "external-links-injected-by-js": "p3",
    "plugin-content-after-render": "p3",
}

PARITY_MOBILE_KINDS = {
    "mobile-status-differs-from-desktop": "p0",
    "mobile-final-url-differs-from-desktop": "p1",
    "viewport-meta-missing": "p1",
    "mobile-intrusive-overlay": "p1",
    "mobile-illegible-text": "p2",
    "mobile-word-count-drop": "p1",
    "mobile-description-differs-from-desktop": "p1",
    "mobile-h1-differs-from-desktop": "p2",
    "mobile-schema-differs-from-desktop": "p1",
    "mobile-image-alt-differs": "p3",
}


async def test_v2_measurement_rules(client, email):
    await signup(client, email)
    user_id = await user_id_of(email)
    r = await client.post("/api/v1/sites", json={"domain": "spa.example.com", "name": "SPA"})
    site = r.json()["data"]
    now = datetime.now(UTC)
    await set_site_facts(
        site["id"],
        robots_txt="User-agent: *\nSitemap: https://spa.example.com/sitemap.xml\n",
        robots_status=200,
        robots_fetched_at=now,
        last_crawled_at=now,
        sitemap_urls=[f"{ORIGIN}/sitemap.xml"],
        sitemap_url_count=1,
        sitemap_at_root=True,
    )
    clean, soft, health, meta, meta2, parity = (
        f"{ORIGIN}/clean",
        f"{ORIGIN}/soft",
        f"{ORIGIN}/health",
        f"{ORIGIN}/meta",
        f"{ORIGIN}/meta2",
        f"{ORIGIN}/parity",
    )
    pages = await seed_pages(
        site["id"],
        user_id,
        [
            page("/", depth=0),
            page("/clean"),
            page("/soft"),
            page("/health"),
            page("/meta", hreflang={}),
            page("/meta2", meta_description=None),
            page("/parity"),
        ],
    )
    shared = {"src": f"{ORIGIN}/hero.png"}
    rows = [
        v2_row(pages, clean, "desktop"),
        v2_row(pages, clean, "mobile"),
        v2_row(pages, soft, "desktop", final_url=f"{ORIGIN}/soft-moved", **SOFT_OVERRIDES),
        v2_row(pages, soft, "mobile", final_url=f"{ORIGIN}/soft-moved", **SOFT_OVERRIDES),
        v2_row(pages, health, "desktop", **HEALTH_OVERRIDES),
        v2_row(
            pages,
            meta,
            "desktop",
            canonical_hrefs=[meta, f"{ORIGIN}/other"],
            hreflang={"en": meta},
            **META_OVERRIDES,
        ),
        v2_row(pages, meta, "mobile", viewport_meta="width=device-width, user-scalable=no"),
        v2_row(
            pages,
            meta2,
            "desktop",
            canonical_count=2,
            canonical_hrefs=[meta2, meta2],
            meta_description="Only after scripts run.",
        ),
        v2_row(pages, parity, "desktop", images=[{**shared, "alt": "Hero"}]),
        v2_row(
            pages,
            parity,
            "mobile",
            status=404,
            final_url=f"{ORIGIN}/m/parity",
            viewport_meta=None,
            overlay_coverage=0.6,
            small_text_ratio=0.5,
            text_chars=300,
            visible_word_count=100,
            meta_description="Phone description.",
            h1=["Phone heading"],
            schema_types=["Other"],
            images=[shared],
        ),
    ]
    await seed_renders(site["id"], user_id, rows)

    r = await client.post("/api/v1/site/technical-seo/run-audit", json={})
    assert r.status_code == 201, r.text
    groups = by_kind(r.json()["data"]["openPageIssues"])

    def expect(kind, severity, url, issue_type):
        assert kind in groups, f"{kind} missing from {sorted(groups)}"
        assert groups[kind]["severity"] == severity, kind
        assert groups[kind]["issueType"] == issue_type, kind
        assert url in groups[kind]["examples"], (kind, groups[kind]["examples"])

    for kind, severity in SOFT_KINDS.items():
        expect(kind, severity, soft, "desktop")
        expect(f"mobile-{kind}", severity, soft, "mobile")
    for kind, severity in HEALTH_KINDS.items():
        expect(kind, severity, health, "desktop")
    expect("intrusive-overlay", "p2", health, "desktop")
    for kind, severity in META_KINDS.items():
        expect(kind, severity, meta, "desktop")
    expect("canonical-repeated-after-render", "p2", meta2, "desktop")
    expect("meta-description-only-after-js", "p2", meta2, "desktop")
    expect("viewport-meta-restrictive", "p2", meta, "mobile")
    for kind, severity in PARITY_MOBILE_KINDS.items():
        expect(kind, severity, parity, "mobile")

    assert "client-side-redirect" not in groups
    from src.technical_seo.rules.render import V2_PAGE_RULES

    v2_kinds = {rule.kind for rule in V2_PAGE_RULES}
    for kind, group in groups.items():
        if kind in v2_kinds:
            assert clean not in group["examples"], (kind, group["examples"])


async def test_raw_counterpart_rules_compare_crawl_and_render(client, email):
    from sqlalchemy import update

    from src.core.database import SessionLocal
    from src.site_pages.models.site_page import SitePage

    site, user_id, pages = await prepare(client, email)
    changed = pages[f"{ORIGIN}/static"]
    clean = pages[f"{ORIGIN}/slow"]
    async with SessionLocal() as db:
        await db.execute(
            update(SitePage)
            .where(SitePage.id == changed)
            .values(
                viewport_meta="width=device-width, initial-scale=1",
                nosnippet_count=0,
                social_meta_count=0,
            )
        )
        await db.execute(
            update(SitePage)
            .where(SitePage.id == clean)
            .values(
                viewport_meta="width=device-width, initial-scale=1",
                nosnippet_count=2,
                social_meta_count=4,
            )
        )
        await db.commit()
    measured = {"settle_reason": "idle", "status": 200}
    await seed_renders(
        site["id"],
        user_id,
        [
            {
                "page_id": changed,
                "title": "Static",
                "word_count": 500,
                **measured,
                "viewport_meta": "width=device-width, initial-scale=1, user-scalable=no",
                "nosnippet_count": 3,
                "social_meta_count": 5,
            },
            {
                "page_id": changed,
                "device": "mobile",
                "title": "Static",
                "word_count": 500,
                **measured,
                "viewport_meta": "width=device-width,initial-scale=1",
                "nosnippet_count": 0,
                "social_meta_count": 0,
            },
            {
                "page_id": clean,
                "title": "Slow",
                "word_count": 500,
                **measured,
                "viewport_meta": "width=device-width,initial-scale=1",
                "nosnippet_count": 2,
                "social_meta_count": 4,
            },
        ],
    )

    r = await client.post("/api/v1/site/technical-seo/run-audit", json={})
    assert r.status_code == 201, r.text
    groups = by_kind(r.json()["data"]["openPageIssues"])
    for kind in (
        "viewport-meta-changed-by-js",
        "data-nosnippet-changed-by-js",
        "og-tags-only-after-js",
    ):
        assert kind in groups, kind
        assert groups[kind]["issueType"] == "desktop"
        assert groups[kind]["examples"] == [f"{ORIGIN}/static"], kind
        assert f"mobile-{kind}" not in groups, kind


async def test_thin_content_counts_the_rendered_words_when_a_render_exists(client, email):
    site, user_id, _ = await prepare(client, email)
    extra = await seed_pages(
        site["id"],
        user_id,
        [
            page("/js-article", page_type="informational", word_count=8),
            page("/thin-article", page_type="informational", word_count=40),
        ],
    )
    await seed_renders(
        site["id"],
        user_id,
        [{"page_id": extra[f"{ORIGIN}/js-article"], "title": "Rendered article", "word_count": 900}],
    )

    r = await client.post("/api/v1/site/technical-seo/run-audit", json={})
    assert r.status_code == 201, r.text
    groups = by_kind(r.json()["data"]["openPageIssues"])
    assert groups["thin-content"]["examples"] == [f"{ORIGIN}/thin-article"]
    assert f"{ORIGIN}/js-article" in groups["js-only-content"]["examples"]
