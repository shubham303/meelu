from datetime import UTC, datetime

from tests.conftest import signup
from tests.integration.technical_seo.conftest import set_site_facts
from tests.integration.technical_seo.test_audit import CLEAN_ROBOTS, by_kind

ORIGIN = "https://links.example.com"


def page(path, **facts):
    return {
        "url": f"{ORIGIN}{path}",
        "status": 200,
        "title": f"Page {path}",
        "metaDescription": f"A description long enough for the page at {path} on the site.",
        "h1": [f"Heading {path}"],
        "wordCount": 500,
        "inSitemap": True,
        "canonical": f"{ORIGIN}{path}",
        **facts,
    }


def link(path, region="body", **extra):
    return {"url": f"{ORIGIN}{path}", "anchor": f"to {path}", "region": region, **extra}


def pages():
    return [
        page(
            "/",
            outLinks=[
                link("/hub", "nav"),
                link("/hub", "body"),
                link("/facet?sort=price", "nav"),
                link("/hidden", "body", rel="nofollow"),
                link("/breadcrumbed", "body"),
            ],
        ),
        page("/hub", outLinks=[link("/spoke", "nav"), link("/mentioned", "body")]),
        page("/spoke", outLinks=[]),
        page("/mentioned", outLinks=[link("/hub", "breadcrumb")]),
        page("/breadcrumbed", outLinks=[]),
        page("/hidden", outLinks=[]),
        page("/facet?sort=price", canonical=f"{ORIGIN}/hub", outLinks=[]),
        *[page(f"/list/{i}", outLinks=[link("/facet?sort=price", "nav")]) for i in range(12)],
    ]


async def test_link_rules_read_the_edge_table(client, email):
    await signup(client, email)
    r = await client.post("/api/v1/sites", json={"domain": "links.example.com", "name": "Links"})
    assert r.status_code == 201, r.text
    site = r.json()["data"]
    now = datetime.now(UTC)
    await set_site_facts(
        site["id"],
        robots_txt=CLEAN_ROBOTS,
        robots_status=200,
        robots_fetched_at=now,
        last_crawled_at=now,
        sitemap_urls=[f"{ORIGIN}/sitemap.xml"],
        sitemap_url_count=1,
        sitemap_at_root=True,
    )
    r = await client.post("/api/v1/site/pages", json={"pages": pages()})
    assert r.status_code == 200, r.text
    r = await client.post("/api/v1/site/pages/graph", json={})
    assert r.status_code == 200, r.text

    r = await client.post("/api/v1/site/technical-seo/run-audit", json={})
    assert r.status_code == 201, r.text
    groups = by_kind(r.json()["data"]["openPageIssues"])

    assert groups["facet-trap"]["examples"] == [f"{ORIGIN}/facet?sort=price"]
    assert groups["internal-nofollow"]["examples"] == [f"{ORIGIN}/"]
    assert groups["nav-gap"]["examples"] == [f"{ORIGIN}/spoke"]
    breadcrumbs = set(groups["missing-breadcrumbs"]["examples"])
    assert f"{ORIGIN}/spoke" in breadcrumbs
    assert f"{ORIGIN}/mentioned" not in breadcrumbs
    assert f"{ORIGIN}/hub" not in breadcrumbs
