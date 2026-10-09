from src.site_structure.links.schemas import HierarchyPage
from src.site_structure.links.service import link_suggestion_service, parent_of, path_of

O = "https://x.example.com"


def hp(pid, path, is_home=False, page_type="hub"):
    return HierarchyPage(id=pid, url=f"{O}{path}", is_home=is_home, page_type=page_type)


def edges_of(pages):
    home = next((p for p in pages if p.is_home), None)
    hubs = [p for p in pages if p.page_type == "hub" and p is not home]
    utilities = [p for p in pages if p.page_type == "utility" and p is not home]
    return {
        (src, dst)
        for src, dst, _ in link_suggestion_service._hierarchy_edges(home, hubs, utilities)
    }


def test_paths():
    assert path_of(f"{O}/") == "/"
    assert path_of(f"{O}/blog/") == "/blog"
    assert parent_of("/") == ""
    assert parent_of("/blog") == "/"
    assert parent_of("/blog/guides") == "/blog"


def test_home_links_to_and_from_utilities_but_not_hubs():
    edges = edges_of(
        [
            hp("home", "/", is_home=True, page_type="money"),
            hp("blog", "/blog"),
            hp("login", "/login", page_type="utility"),
        ]
    )
    assert edges == {
        ("home", "login"),
        ("login", "home"),
    }


def test_hub_hierarchy_parent_child_only():
    edges = edges_of(
        [
            hp("blog", "/blog"),
            hp("guides", "/blog/guides"),
            hp("reviews", "/blog/reviews"),
            hp("shop", "/shop"),
        ]
    )
    assert ("blog", "guides") in edges and ("guides", "blog") in edges
    assert ("blog", "reviews") in edges and ("reviews", "blog") in edges
    assert ("guides", "reviews") not in edges and ("reviews", "guides") not in edges
    assert ("blog", "shop") not in edges and ("shop", "blog") not in edges
    assert ("guides", "shop") not in edges
    assert not any(a == b for a, b in edges)
