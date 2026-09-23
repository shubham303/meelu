from src.site_structure.hierarchy import hierarchy_edges, parent_of, path_of
from src.site_structure.schemas import HierarchyPage

O = "https://x.example.com"


def hp(pid, path, kind="other", page_type="hub"):
    return HierarchyPage(id=pid, url=f"{O}{path}", kind=kind, page_type=page_type)


def edges_of(pages):
    rows, home, hubs = hierarchy_edges(pages, "job")
    return {(r.from_page_id, r.to_page_id) for r in rows}, home, hubs


def test_paths():
    assert path_of(f"{O}/") == "/"
    assert path_of(f"{O}/blog/") == "/blog"
    assert parent_of("/") == ""
    assert parent_of("/blog") == "/"
    assert parent_of("/blog/guides") == "/blog"


def test_home_links_to_and_from_hubs_and_utilities():
    edges, home, hubs = edges_of(
        [
            hp("home", "/", kind="home", page_type="money"),
            hp("blog", "/blog"),
            hp("login", "/login", page_type="utility"),
        ]
    )
    assert home is not None and hubs == 1
    assert edges == {
        ("home", "blog"),
        ("blog", "home"),
        ("home", "login"),
        ("login", "home"),
    }


def test_hub_hierarchy_parent_child_and_siblings():
    edges, home, hubs = edges_of(
        [
            hp("blog", "/blog"),
            hp("guides", "/blog/guides"),
            hp("reviews", "/blog/reviews"),
            hp("shop", "/shop"),
        ]
    )
    assert home is None and hubs == 4
    assert ("blog", "guides") in edges and ("guides", "blog") in edges
    assert ("blog", "reviews") in edges and ("reviews", "blog") in edges
    assert ("guides", "reviews") in edges and ("reviews", "guides") in edges
    assert ("blog", "shop") in edges and ("shop", "blog") in edges
    assert ("guides", "shop") not in edges
    assert not any(a == b for a, b in edges)
