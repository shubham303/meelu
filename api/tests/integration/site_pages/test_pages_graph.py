import pytest

from src.site_pages.pagerank import page_rank
from tests.integration.site_pages.conftest import list_pages, save_pages

GRAPH = [
    {
        "url": "https://example.com/",
        "status": 200,
        "outLinks": [
            {"url": "https://example.com/a", "anchor": "About us"},
            {"url": "https://example.com/b/", "anchor": "Blog"},
        ],
    },
    {
        "url": "https://example.com/a",
        "status": 200,
        "outLinks": [{"url": "https://example.com/b#top", "anchor": "Blog again"}],
    },
    {"url": "https://example.com/b", "status": 200, "outLinks": []},
    {"url": "https://example.com/orphan", "status": 200, "outLinks": []},
]


@pytest.fixture
async def graph(client, site):
    await save_pages(client, GRAPH)
    r = await client.post("/api/v1/site/pages/graph", json={})
    assert r.status_code == 200
    assert r.json()["data"] == {"rebuilt": True}
    body = await list_pages(client, view="full")
    return {p["url"]: p for p in body["pages"]}


async def test_graph_counts_inlinks_and_depth(client, graph):
    assert graph["https://example.com/"]["inlinks"] == 0
    assert graph["https://example.com/a"]["inlinks"] == 1
    assert graph["https://example.com/b"]["inlinks"] == 2
    assert graph["https://example.com/orphan"]["inlinks"] == 0

    assert graph["https://example.com/"]["depth"] == 0
    assert graph["https://example.com/a"]["depth"] == 1
    assert graph["https://example.com/b"]["depth"] == 1
    assert "depth" not in graph["https://example.com/orphan"]

    anchors = graph["https://example.com/b"]["inboundAnchors"]
    assert sorted(a["anchor"] for a in anchors) == ["Blog", "Blog again"]
    assert sorted(a["from"] for a in anchors) == [
        "https://example.com",
        "https://example.com/a",
    ]
    assert graph["https://example.com/orphan"]["inboundAnchors"] == []


async def test_graph_writes_link_scores(client, graph):
    scores = {url: page.get("linkScore") for url, page in graph.items()}
    assert all(s is not None for s in scores.values())
    assert max(scores.values()) == 100.0
    assert scores["https://example.com/b"] == 100.0
    assert scores["https://example.com/b"] > scores["https://example.com/a"]
    assert scores["https://example.com/a"] > scores["https://example.com/orphan"]


async def test_graph_rebuild_clears_stale_scores(client, site):
    await save_pages(client, GRAPH)
    r = await client.post("/api/v1/site/pages/graph", json={})
    assert r.status_code == 200

    await save_pages(
        client,
        [{"url": "https://example.com/", "status": 200, "outLinks": []}],
    )
    r = await client.post("/api/v1/site/pages/graph", json={})
    assert r.status_code == 200

    body = await list_pages(client, view="full")
    pages = {p["url"]: p for p in body["pages"]}
    assert pages["https://example.com/b"]["inlinks"] == 1
    assert pages["https://example.com/a"]["inlinks"] == 0
    assert "depth" not in pages["https://example.com/a"]
    assert pages["https://example.com/"]["depth"] == 0


async def test_graph_on_empty_site(client, site):
    r = await client.post("/api/v1/site/pages/graph", json={})
    assert r.status_code == 200
    assert r.json()["data"] == {"rebuilt": True}


def test_page_rank_matches_reference():
    ids = ["home", "a", "b"]
    edges = [
        {"src": "home", "dst": "a"},
        {"src": "home", "dst": "b"},
        {"src": "a", "dst": "b"},
    ]
    scores = page_rank(ids, edges)
    assert scores["b"] == 100.0
    assert scores["b"] > scores["a"] > scores["home"]
    assert all(isinstance(v, float) for v in scores.values())

    assert page_rank([], edges) == {}

    seeded = page_rank(ids, edges, teleport={"home": 100.0, "a": 0.1, "b": 0.1})
    assert seeded["home"] > scores["home"]


async def test_link_scores_use_traffic_teleport(client, site):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from src.core.database import unit_of_work
    from src.core.ids import uid
    from src.site_traffic.models.site_traffic_landing_daily import SiteTrafficLandingDaily
    from src.sites.models.site import Site

    await save_pages(client, GRAPH)

    async with unit_of_work() as db:
        row = (await db.execute(select(Site).where(Site.id == site["id"]))).scalar_one()
        db.add(
            SiteTrafficLandingDaily(
                id=uid("stl"),
                user_id=row.user_id,
                site_id=site["id"],
                day=datetime.now(UTC).date() - timedelta(days=1),
                landing_page="/orphan",
                channel="Organic Search",
                sessions=5000,
            )
        )

    r = await client.post("/api/v1/site/pages/graph", json={})
    assert r.status_code == 200

    body = await list_pages(client, view="full")
    pages = {p["url"]: p for p in body["pages"]}
    assert pages["https://example.com/orphan"]["linkScore"] == 100.0
