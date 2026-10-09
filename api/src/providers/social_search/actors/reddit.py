from src.providers.apify import ChargeEvents
from src.providers.social_search.actors import ActorSpec, SearchQuery, window
from src.providers.social_search.shape import post

WINDOWS = [(1 / 24, "hour"), (1, "day"), (7, "week"), (31, "month"), (366, "year")]


def time_window(q: SearchQuery) -> str:
    return window(q, WINDOWS, "all") if q.since else "month"


def harshmaur_input(q: SearchQuery) -> dict:
    return {
        "searchTerms": q.keywords,
        "searchPosts": True,
        "searchComments": False,
        "searchCommunities": False,
        "crawlCommentsPerPost": False,
        "searchSort": "new",
        "searchTime": time_window(q),
        "maxPostsCount": q.limit,
        "maxCommentsCount": 0,
        "maxCommentsPerPost": 0,
        "includeNSFW": False,
    }


def harshmaur_post(i: dict) -> dict | None:
    if i.get("dataType") not in (None, "post"):
        return None
    return post(
        "reddit",
        {
            "id": i.get("parsedId") or i.get("id"),
            "url": i.get("postUrl") or i.get("contentUrl"),
            "handle": i.get("authorName"),
            "title": i.get("title"),
            "text": i.get("body") or i.get("title") or "",
            "createdAt": i.get("createdAt"),
            "score": i.get("upVotes") if i.get("upVotes") is not None else i.get("score"),
            "comments": i.get("commentsCount"),
            "subreddit": i.get("parsedCommunityName"),
        },
    )


def fatihtahta_input(q: SearchQuery) -> dict:
    return {
        "queries": q.keywords,
        "sort": "new",
        "timeframe": time_window(q),
        "scrapeComments": False,
        "includeNsfw": False,
        "maxPosts": q.limit,
    }


def fatihtahta_post(i: dict) -> dict | None:
    if i.get("kind") not in (None, "post"):
        return None
    return post(
        "reddit",
        {
            "id": i.get("id"),
            "url": i.get("url") or i.get("canonical_url"),
            "handle": i.get("author"),
            "title": i.get("title"),
            "text": i.get("body") or i.get("title") or "",
            "createdAt": i.get("created_utc"),
            "score": i.get("score"),
            "comments": i.get("num_comments"),
            "subreddit": i.get("subreddit"),
        },
    )


ACTORS = [
    ActorSpec(
        "reddit",
        "harshmaur~reddit-scraper-pro",
        harshmaur_input,
        harshmaur_post,
        ChargeEvents(result="result", start="init"),
    ),
    ActorSpec("reddit", "fatihtahta~reddit-scraper-search-fast", fatihtahta_input, fatihtahta_post),
]
