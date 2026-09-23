import numpy as np

from src.site_structure.pillars.clustering import (
    PagePoint,
    cluster_pages,
    cohesion,
    coverage,
    overlap,
    structural_share,
    topic_for,
)


def point(pid, axis, wobble=0.0, page_type="informational", keywords=(), title=None):
    v = np.zeros(16)
    v[axis] = 1.0
    v[(axis + 1) % 16] = wobble
    return PagePoint(pid, f"https://x/{pid}", title, page_type, 1, tuple(keywords), v)


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


def test_overlap_topic_and_structural_share():
    assert overlap(["a", "b", "c"], ["b", "c", "d"]) == 0.5
    assert overlap([], []) == 0.0
    points = [
        point("a", 0, keywords=("seo", "links"), page_type="legal"),
        point("b", 0, keywords=("seo",), page_type="utility"),
        point("c", 0, keywords=("seo", "links", "hubs")),
    ]
    assert topic_for(points) == "seo, links, hubs"
    assert sorted(topic_for([point("t", 0, title="The best SEO guide")]).split(", ")) == [
        "best",
        "guide",
        "seo",
    ]
    assert structural_share(points, ("legal", "utility")) == 2 / 3
