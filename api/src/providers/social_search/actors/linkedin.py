from src.providers.apify import ChargeEvents
from src.providers.social_search.actors import ActorSpec, SearchQuery, window
from src.providers.social_search.shape import post

HARVEST_WINDOWS = [
    (1, "24h"),
    (7, "week"),
    (31, "month"),
    (92, "3months"),
    (183, "6months"),
    (366, "year"),
]
MAESTRO_WINDOWS = [(1, "past-24h"), (7, "past-week"), (31, "past-month")]
MAESTRO_PAGE = 50


def harvest_input(q: SearchQuery) -> dict:
    return {
        "searchQueries": q.keywords,
        "maxPosts": q.limit,
        "sortBy": "date",
        "postedLimit": window(q, HARVEST_WINDOWS, "any") if q.since else "month",
        "profileScraperMode": "short",
        "scrapeReactions": False,
        "scrapeComments": False,
    }


def harvest_post(i: dict) -> dict | None:
    if i.get("type") not in (None, "post"):
        return None
    author = i.get("author") or {}
    posted = i.get("postedAt") or {}
    engagement = i.get("engagement") or {}
    return post(
        "linkedin",
        {
            "id": i.get("id") or i.get("entityId"),
            "url": i.get("linkedinUrl") or i.get("shareLinkedinUrl"),
            "handle": author.get("publicIdentifier")
            or author.get("universalName")
            or author.get("name"),
            "displayName": author.get("name"),
            "text": i.get("content") or "",
            "createdAt": posted.get("timestamp") or posted.get("date"),
            "score": engagement.get("likes"),
            "comments": engagement.get("comments"),
        },
    )


def maestro_input(q: SearchQuery) -> dict:
    return {
        "keyword": " OR ".join(f'"{k}"' if " " in k else k for k in q.keywords),
        "sort_type": "date_posted",
        "date_filter": window(q, MAESTRO_WINDOWS, "") if q.since else "past-month",
        "limit": min(q.limit, MAESTRO_PAGE),
        "total_posts": q.limit,
    }


def maestro_post(i: dict) -> dict | None:
    author = i.get("author") or {}
    posted = i.get("posted_at") or {}
    stats = i.get("stats") or {}
    return post(
        "linkedin",
        {
            "id": i.get("activity_id") or i.get("full_urn"),
            "url": i.get("post_url"),
            "handle": author.get("name"),
            "displayName": author.get("name"),
            "text": i.get("text") or "",
            "createdAt": posted.get("timestamp") or posted.get("date"),
            "score": stats.get("total_reactions"),
            "comments": stats.get("comments"),
            "tags": i.get("hashtags"),
        },
    )


ACTORS = [
    ActorSpec(
        "linkedin",
        "harvestapi~linkedin-post-search",
        harvest_input,
        harvest_post,
        ChargeEvents(result="post", start="apify-actor-start"),
    ),
    ActorSpec(
        "linkedin",
        "apimaestro~linkedin-posts-search-scraper-no-cookies",
        maestro_input,
        maestro_post,
    ),
]
