import numpy as np

from src.site_structure.pillars.clustering import (
    PagePoint,
    cluster_pages,
    cohesion,
    coverage,
    family,
    is_structural,
    mixed_families,
    overlap,
    topic_for,
)


def point(pid, axis, wobble=0.0, page_type="informational", title=None, broad=None):
    v = np.zeros(16)
    v[axis] = 1.0
    v[(axis + 1) % 16] = wobble
    return PagePoint(pid, f"https://x/{pid}", title, page_type, 1, v, broad)


def test_cluster_pages_splits_by_direction_and_drops_singletons():
    points = (
        [point(f"a{i}", 0, 0.05 * i) for i in range(3)]
        + [point(f"b{i}", 8, 0.05 * i) for i in range(2)]
        + [point("lonely", 4)]
    )
    groups = {frozenset(g) for g in cluster_pages(points, 0.5)}
    assert groups == {frozenset({"a0", "a1", "a2"}), frozenset({"b0", "b1"})}
    assert cluster_pages(points[:1], 0.5) == []


def test_cohesion_and_coverage():
    points = [point("a", 0), point("b", 0, 0.1), point("c", 8)]
    vectors = {p.id: p.vector for p in points}
    assert cohesion(["a", "b"], vectors) > 0.99
    assert cohesion(["a", "c"], vectors) < 0.01
    assert cohesion(["a"], vectors) == 1.0
    hub = np.zeros(16)
    hub[0] = 1.0
    vectors["hub"] = hub
    found = coverage(["a", "b"], vectors, {"hub": {"a", "b"}, "c": {"a"}})
    assert found.page_id == "hub"
    assert found.score > 0.99
    assert coverage(["a", "b"], vectors, {}).page_id is None


def test_overlap_and_topic():
    assert overlap(["a", "b", "c"], ["b", "c", "d"]) == 0.5
    assert overlap([], []) == 0.0
    points = [
        point("a", 0, title="SEO links", page_type="legal"),
        point("b", 0, title="SEO", page_type="utility"),
        point("c", 0, title="SEO links hubs"),
    ]
    assert topic_for(points) == "seo, links, hubs"
    assert sorted(topic_for([point("t", 0, title="The best SEO guide")]).split(", ")) == [
        "best",
        "guide",
        "seo",
    ]


def test_cluster_pages_keeps_offer_and_content_apart():
    points = [
        point("svc0", 0, 0.00, page_type="money", broad="service"),
        point("svc1", 0, 0.05, page_type="money", broad="service"),
        point("blog0", 0, 0.10, broad="article"),
        point("blog1", 0, 0.15, broad="guide"),
        point("hub", 0, 0.02, page_type="hub", broad="content_listing"),
        point("about", 0, 0.03, page_type="company", broad="about"),
    ]
    groups = {frozenset(g) for g in cluster_pages(points, 0.5)}
    assert groups == {frozenset({"svc0", "svc1"}), frozenset({"blog0", "blog1"})}


def test_family_falls_back_to_page_type_then_unknown():
    assert family(point("a", 0, broad="feature")) == "offer"
    assert family(point("b", 0, page_type="money")) == "offer"
    assert family(point("c", 0, page_type="support")) == "content"
    assert family(point("d", 0, page_type="hub")) is None
    assert family(point("e", 0, page_type=None)) == "unknown"
    assert family(point("f", 0, page_type="money", broad="other")) == "offer"


def test_mixed_families_ignores_unknown_and_unclustered_pages():
    blog = point("b", 0, broad="article")
    assert mixed_families([blog, point("s", 0, broad="service")])
    assert not mixed_families([blog, point("u", 0, page_type=None)])
    assert not mixed_families([blog, point("h", 0, broad="about")])


def test_structural_pages_never_cluster():
    home = PagePoint("home", "https://x/", "Home", "money", 9, np.eye(16)[0], None)
    assert is_structural(home)
    assert is_structural(point("c", 0, page_type="money", broad="contact"))
    assert is_structural(point("l", 0, page_type="legal"))
    assert is_structural(point("o", 0, page_type="company", broad="other"))
    assert not is_structural(point("s", 0, page_type="money", broad="service"))
    assert not is_structural(point("a", 0, page_type="company", broad="article"))
    points = [
        home,
        point("s0", 0, 0.01, page_type="money", broad="service"),
        point("s1", 0, 0.02, page_type="money", broad="service"),
        point("careers", 0, 0.03, page_type="company", broad="careers"),
    ]
    assert cluster_pages(points, 0.5) == [["s0", "s1"]]
