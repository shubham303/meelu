from src.providers.social_search.actors import ActorSpec, SearchQuery
from src.providers.social_search.shape import post


def streamers_input(q: SearchQuery) -> dict:
    return {
        "searchQueries": q.keywords,
        "maxResults": min(q.limit, 30),
        "maxResultsShorts": 0,
        "maxResultStreams": 0,
    }


def streamers_post(i: dict) -> dict | None:
    return post(
        "youtube",
        {
            "id": i.get("id"),
            "url": i.get("url"),
            "handle": i.get("channelName"),
            "title": i.get("title"),
            "text": i.get("text") or i.get("description") or i.get("title") or "",
            "createdAt": i.get("date"),
            "score": i.get("likes"),
            "comments": i.get("commentsCount"),
            "views": i.get("viewCount"),
        },
    )


ACTORS = [ActorSpec("youtube", "streamers~youtube-scraper", streamers_input, streamers_post)]
