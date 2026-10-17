from src.seo.search_suggestions.schemas import PeopleAlsoAsk


def blocks(result: dict | None, kind: str) -> list[dict]:
    return [
        i
        for i in (result or {}).get("items") or []
        if isinstance(i, dict) and i.get("type") == kind
    ]


def autocomplete(result: dict | None, keyword: str) -> list[str]:
    found = (
        " ".join(str(i.get("suggestion") or "").lower().split())
        for i in blocks(result, "autocomplete")
    )
    return [s for s in dict.fromkeys(found) if s and s != keyword]


def answer_url(element: dict) -> str | None:
    for expanded in element.get("expanded_element") or []:
        if isinstance(expanded, dict) and expanded.get("url"):
            return str(expanded["url"])
    return None


def people_also_ask(result: dict | None) -> list[PeopleAlsoAsk]:
    found: dict[str, PeopleAlsoAsk] = {}
    for block in blocks(result, "people_also_ask"):
        for element in block.get("items") or []:
            question = isinstance(element, dict) and str(element.get("title") or "").strip()
            if question and question not in found:
                found[question] = PeopleAlsoAsk(question=question, url=answer_url(element))
    return list(found.values())


def related_searches(result: dict | None) -> list[str]:
    found = (
        " ".join(str(s).lower().split())
        for block in blocks(result, "related_searches")
        for s in block.get("items") or []
        if isinstance(s, str)
    )
    return [s for s in dict.fromkeys(found) if s]
