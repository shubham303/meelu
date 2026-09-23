import pytest

from src.site_pages.pagerank import page_rank
from src.site_pages.schemas import SitePageEdge
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
    body = await list_pages(client, view="full", page_size=100)
    return {p["url"]: p for p in body}


async def test_graph_counts_inlinks_and_depth(client, graph):
    assert graph["https://example.com/"]["inlinks"] == 0
    assert graph["https://example.com/a"]["inlinks"] == 1
    assert graph["https://example.com/b"]["inlinks"] == 2
    assert graph["https://example.com/orphan"]["inlinks"] == 0

    assert graph["https://example.com/"]["depth"] == 0
    assert graph["https://example.com/a"]["depth"] == 1
    assert graph["https://example.com/b"]["depth"] == 1
    assert graph["https://example.com/orphan"]["depth"] is None

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

    body = await list_pages(client, view="full", page_size=100)
    pages = {p["url"]: p for p in body}
    assert pages["https://example.com/b"]["inlinks"] == 1
    assert pages["https://example.com/a"]["inlinks"] == 0
    assert pages["https://example.com/a"]["depth"] is None
    assert pages["https://example.com/"]["depth"] == 0


async def test_graph_on_empty_site(client, site):
    r = await client.post("/api/v1/site/pages/graph", json={})
    assert r.status_code == 200
    assert r.json()["data"] == {"rebuilt": True}


def test_page_rank_matches_reference():
    ids = ["home", "a", "b"]
    edges = [
        SitePageEdge(src="home", dst="a"),
        SitePageEdge(src="home", dst="b"),
        SitePageEdge(src="a", dst="b"),
    ]
    scores = page_rank(ids, edges)
    assert scores["b"] == 100.0
    assert scores["b"] > scores["a"] > scores["home"]
    assert all(isinstance(v, float) for v in scores.values())

    assert page_rank([], edges) == {}

    seeded = page_rank(ids, edges, teleport={"home": 100.0, "a": 0.1, "b": 0.1})
    assert seeded["home"] > scores["home"]

    weighted = page_rank(
        ids,
        [
            SitePageEdge(src="home", dst="a", weight=1.0),
            SitePageEdge(src="home", dst="b", weight=0.1),
        ],
    )
    assert weighted["a"] > weighted["b"]
    assert (
        page_rank(ids, [SitePageEdge(src="home", dst="a", weight=0)])["a"]
        == page_rank(ids, [])["a"]
    )


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

    body = await list_pages(client, view="full", page_size=100)
    pages = {p["url"]: p for p in body}
    assert pages["https://example.com/orphan"]["linkScore"] == 100.0


REGIONS = [
    {
        "url": "https://example.com/",
        "status": 200,
        "outLinks": [
            {"url": "https://example.com/hub", "anchor": "Hub", "region": "nav"},
            {"url": "https://example.com/hub", "anchor": "Read the hub", "region": "body"},
            {"url": "https://example.com/legal", "anchor": "Terms", "region": "footer"},
            {
                "url": "https://example.com/page/2",
                "anchor": "Next",
                "rel": "next",
                "region": "pagination",
            },
            {
                "url": "https://example.com/hidden",
                "anchor": "Hidden",
                "rel": "nofollow",
                "region": "body",
            },
        ],
    },
    {
        "url": "https://example.com/hub",
        "status": 200,
        "outLinks": [{"url": "https://example.com/spoke", "anchor": "Spoke", "region": "nav"}],
    },
    {"url": "https://example.com/spoke", "status": 200, "outLinks": []},
    {"url": "https://example.com/legal", "status": 200, "outLinks": []},
    {
        "url": "https://example.com/page/2",
        "status": 200,
        "outLinks": [{"url": "https://example.com/deep", "anchor": "Deep", "region": "body"}],
    },
    {"url": "https://example.com/deep", "status": 200, "outLinks": []},
    {
        "url": "https://example.com/hidden",
        "status": 200,
        "canonical": "https://example.com/hub",
        "outLinks": [],
    },
]


async def test_graph_stores_regions_and_editorial_counts(client, site):
    from sqlalchemy import select

    from src.core.database import unit_of_work
    from src.site_pages.models.site_page_link import SitePageLink

    await save_pages(client, REGIONS)
    r = await client.post("/api/v1/site/pages/graph", json={})
    assert r.status_code == 200
    pages = {p["url"]: p for p in await list_pages(client, view="full", page_size=100)}

    hub = pages["https://example.com/hub"]
    assert hub["inlinks"] == 1
    assert hub["editorialInlinks"] == 1
    assert hub["depth"] == 1

    spoke = pages["https://example.com/spoke"]
    assert spoke["inlinks"] == 1
    assert spoke["editorialInlinks"] == 0

    assert pages["https://example.com/page/2"]["depth"] is None
    assert pages["https://example.com/deep"]["depth"] is None

    assert (
        pages["https://example.com/hub"]["editorialScore"]
        > pages["https://example.com/legal"]["editorialScore"]
    )

    async with unit_of_work() as db:
        rows = (
            (await db.execute(select(SitePageLink).where(SitePageLink.site_id == site["id"])))
            .scalars()
            .all()
        )
    by_id = {p["id"]: p["url"] for p in pages.values()}
    edges = {(by_id[e.src_page_id], by_id[e.dst_page_id], e.region): e for e in rows}
    home = "https://example.com/"
    assert edges[(home, "https://example.com/hub", "nav")].weight == pytest.approx(0.2)
    assert edges[(home, "https://example.com/hub", "body")].weight == pytest.approx(1.0)
    assert edges[(home, "https://example.com/legal", "footer")].weight == pytest.approx(0.1)
    hidden = edges[(home, "https://example.com/hidden", "body")]
    assert hidden.followable is False
    assert hidden.weight == 0
    assert hidden.dst_canonical is False
    assert edges[(home, "https://example.com/page/2", "pagination")].rel == "next"
