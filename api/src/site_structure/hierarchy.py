from urllib.parse import urlsplit

from src.site_structure.schemas import HierarchyPage, NewLinkSuggestion

HOME_TO_HUB = "The home page should point at this section so it is one click from the root."
HOME_TO_UTILITY = "The home page should give this utility page a way in."
BACK_TO_HOME = "This page should link back to the home page."
PARENT_TO_CHILD = "This section should list its child section {child}."
CHILD_TO_PARENT = "This section should link up to its parent section {parent}."
SIBLINGS = "Sibling sections under {parent} should link to each other."


def path_of(url: str) -> str:
    path = urlsplit(url).path.rstrip("/")
    return path or "/"


def parent_of(path: str) -> str:
    if path == "/":
        return ""
    head, _, _ = path.rpartition("/")
    return head or "/"


def hierarchy_edges(
    pages: list[HierarchyPage], job_id: str
) -> tuple[list[NewLinkSuggestion], HierarchyPage | None, int]:
    home = next((p for p in pages if p.is_home), None)
    hubs = [p for p in pages if p.page_type == "hub" and p is not home]
    utilities = [p for p in pages if p.page_type == "utility" and p is not home]
    edges: dict[tuple[str, str], str] = {}

    def add(src: HierarchyPage, dst: HierarchyPage, why: str) -> None:
        if src.id != dst.id:
            edges.setdefault((src.id, dst.id), why)

    if home is not None:
        for hub in hubs:
            add(home, hub, HOME_TO_HUB)
            add(hub, home, BACK_TO_HOME)
        for page in utilities:
            add(home, page, HOME_TO_UTILITY)
            add(page, home, BACK_TO_HOME)

    by_path = {path_of(h.url): h for h in hubs}
    for path, hub in by_path.items():
        parent_path = parent_of(path)
        parent = by_path.get(parent_path)
        if parent is not None:
            add(parent, hub, PARENT_TO_CHILD.format(child=path))
            add(hub, parent, CHILD_TO_PARENT.format(parent=parent_path))
        for other_path, other in by_path.items():
            if other is not hub and parent_of(other_path) == parent_path:
                add(hub, other, SIBLINGS.format(parent=parent_path or "/"))

    rows = [
        NewLinkSuggestion(job_id=job_id, from_page_id=src, to_page_id=dst, suggestion=why)
        for (src, dst), why in edges.items()
    ]
    return rows, home, len(hubs)
