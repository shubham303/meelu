import re

from src.providers.social_search.actors import ActorSpec, SearchQuery
from src.providers.social_search.shape import post


def hashtag_of(keyword: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(keyword).lower())


def hashtag_input(q: SearchQuery) -> dict:
    return {
        "hashtags": [h for h in (hashtag_of(k) for k in q.keywords) if h],
        "resultsType": "posts",
        "resultsLimit": min(q.limit, 30),
    }


def hashtag_post(i: dict) -> dict | None:
    return post(
        "instagram",
        {
            "id": i.get("id"),
            "url": i.get("url"),
            "handle": i.get("ownerUsername"),
            "text": i.get("caption") or "",
            "createdAt": i.get("timestamp"),
            "score": i.get("likesCount"),
            "comments": i.get("commentsCount"),
            "tags": i.get("hashtags"),
        },
    )


ACTORS = [ActorSpec("instagram", "apify~instagram-hashtag-scraper", hashtag_input, hashtag_post)]
