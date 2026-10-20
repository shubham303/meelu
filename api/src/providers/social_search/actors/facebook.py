from src.providers.apify import ChargeEvents
from src.providers.social_search.actors import ActorSpec, SearchQuery
from src.providers.social_search.shape import post, since_day


def topapi_input(q: SearchQuery) -> dict:
    day = since_day(q.since)
    return {
        "searchQueries": q.keywords,
        "sortBy": "recent",
        "mustContainQuery": False,
        "maxPostsPerQuery": q.per_keyword,
        "maxItems": q.run_cap(),
        **({"startDate": day} if day else {}),
    }


def topapi_post(i: dict) -> dict | None:
    author = i.get("author") or {}
    return post(
        "facebook",
        {
            "id": i.get("post_id"),
            "url": i.get("url"),
            "handle": author.get("name"),
            "displayName": author.get("name"),
            "text": i.get("message") or "",
            "createdAt": i.get("published_at") or i.get("timestamp"),
            "score": i.get("reactions_count"),
            "comments": i.get("comments_count"),
        },
    )


ACTORS = [
    ActorSpec(
        "facebook",
        "topapi~facebook-search-posts-scraper",
        topapi_input,
        topapi_post,
        ChargeEvents(result="post-scraped"),
    )
]
