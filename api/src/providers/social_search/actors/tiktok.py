from src.providers.social_search.actors import ActorSpec, SearchQuery
from src.providers.social_search.shape import post


def clockworks_input(q: SearchQuery) -> dict:
    return {"searchQueries": q.keywords, "resultsPerPage": min(q.limit, 30)}


def clockworks_post(i: dict) -> dict | None:
    author = i.get("authorMeta") or {}
    return post(
        "tiktok",
        {
            "id": i.get("id"),
            "url": i.get("webVideoUrl"),
            "handle": author.get("name"),
            "displayName": author.get("nickName"),
            "text": i.get("text") or "",
            "createdAt": i.get("createTimeISO") or i.get("createTime"),
            "score": i.get("diggCount"),
            "comments": i.get("commentCount"),
            "views": i.get("playCount"),
        },
    )


ACTORS = [ActorSpec("tiktok", "clockworks~tiktok-scraper", clockworks_input, clockworks_post)]
