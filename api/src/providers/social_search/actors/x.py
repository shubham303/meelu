from src.providers.social_search.actors import ActorSpec, SearchQuery
from src.providers.social_search.shape import post, since_day


def kaito_input(q: SearchQuery) -> dict:
    day = since_day(q.since)
    return {
        "searchTerms": [f"{k} since:{day}" if day else k for k in q.keywords],
        "queryType": "Latest",
        "lang": "en",
        "maxItems": q.per_keyword,
    }


def kaito_post(i: dict) -> dict | None:
    if i.get("type") not in (None, "tweet"):
        return None
    author = i.get("author") or {}
    hashtags = ((i.get("entities") or {}).get("hashtags")) or []
    return post(
        "x",
        {
            "id": i.get("id"),
            "url": i.get("url") or i.get("twitterUrl"),
            "handle": author.get("userName"),
            "displayName": author.get("name"),
            "text": i.get("text") or "",
            "createdAt": i.get("createdAt"),
            "score": i.get("likeCount"),
            "comments": i.get("replyCount"),
            "views": i.get("viewCount"),
            "tags": [h.get("text") for h in hashtags if isinstance(h, dict)],
        },
    )


def codeperfection_input(q: SearchQuery) -> dict:
    day = since_day(q.since)
    return {
        "searchTerms": q.keywords,
        "sort": "Latest",
        "language": "en",
        "maxTweets": q.per_keyword,
        "maxTotalTweets": q.run_cap(),
        **({"startDate": day} if day else {}),
    }


def codeperfection_post(i: dict) -> dict | None:
    author = i.get("author") or {}
    return post(
        "x",
        {
            "id": i.get("id"),
            "url": i.get("url") or i.get("twitter_url"),
            "handle": author.get("username"),
            "displayName": author.get("name"),
            "text": i.get("text") or "",
            "createdAt": i.get("created_at"),
            "score": i.get("like_count"),
            "comments": i.get("reply_count"),
            "views": i.get("view_count"),
            "tags": i.get("hashtags"),
        },
    )


ACTORS = [
    ActorSpec(
        "x",
        "kaitoeasyapi~twitter-x-data-tweet-scraper-pay-per-result-cheapest",
        kaito_input,
        kaito_post,
    ),
    ActorSpec("x", "codeperfection~x-twitter-scraper", codeperfection_input, codeperfection_post),
]
