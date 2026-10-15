from src.providers.social_search.actors import ActorSpec, SearchQuery
from src.providers.social_search.shape import post, since_day


def scraper_one_input(q: SearchQuery) -> dict:
    day = since_day(q.since)
    return {
        "query": q.keywords[0],
        "resultsCount": q.per_keyword,
        "searchType": "latest",
        **({"startDate": day} if day else {}),
    }


def scraper_one_post(i: dict) -> dict | None:
    author = i.get("author") or {}
    return post(
        "facebook",
        {
            "id": i.get("postId"),
            "url": i.get("url"),
            "handle": author.get("name"),
            "displayName": author.get("name"),
            "text": i.get("postText") or "",
            "createdAt": i.get("timestamp"),
            "score": i.get("reactionsCount"),
            "comments": i.get("commentsCount"),
        },
    )


ACTORS = [
    ActorSpec(
        "facebook",
        "scraper_one~facebook-posts-search",
        scraper_one_input,
        scraper_one_post,
        one_query_per_run=True,
    )
]
