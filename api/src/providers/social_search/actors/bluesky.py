from src.providers.social_search.actors import ActorSpec, SearchQuery
from src.providers.social_search.shape import post, since_day


def lexis_input(q: SearchQuery) -> dict:
    day = since_day(q.since)
    return {
        "queries": q.keywords,
        "limit": min(q.limit, 50),
        "sort": "latest",
        "lang": "en",
        **({"since": day} if day else {}),
    }


def lexis_post(i: dict) -> dict | None:
    author = i.get("author") or {}
    record = i.get("record") or {}
    return post(
        "bluesky",
        {
            "id": i.get("uri") or i.get("url"),
            "url": i.get("url"),
            "handle": author.get("handle"),
            "displayName": author.get("displayName") or author.get("name"),
            "text": i.get("text") or record.get("text") or "",
            "createdAt": i.get("createdAt") or record.get("createdAt"),
            "score": i.get("likeCount") if i.get("likeCount") is not None else i.get("likes"),
            "comments": i.get("replyCount")
            if i.get("replyCount") is not None
            else i.get("replies"),
        },
    )


ACTORS = [ActorSpec("bluesky", "lexis-solutions~bluesky-posts-scraper", lexis_input, lexis_post)]
