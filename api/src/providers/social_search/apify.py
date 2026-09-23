import re

from src.providers import apify
from src.providers.registry import VendorResponse
from src.providers.social_search.adapter import SocialSearchAdapter
from src.providers.social_search.platforms import platform_entry
from src.providers.social_search.shape import post, since_day

MAX_KEYWORDS = 3


def hashtag_of(keyword: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(keyword).lower())


INPUTS = {
    "reddit": lambda q: {
        "searches": q["keywords"],
        "searchPosts": True,
        "searchComments": False,
        "sort": "new",
        "time": "month",
        "maxPostCount": q["limit"],
        "maxItems": q["limit"],
        "skipComments": True,
    },
    "x": lambda q: {
        "searchTerms": q["keywords"],
        "queryType": "Latest",
        "lang": "en",
        "maxItems": q["limit"],
        **({"since": since_day(q.get("since"))} if since_day(q.get("since")) else {}),
    },
    "linkedin": lambda q: {
        "keyword": " ".join(q["keywords"]),
        "sort_type": "date_posted",
        "total_posts": min(q["limit"], 50),
    },
    "youtube": lambda q: {
        "searchQueries": q["keywords"],
        "maxResults": min(q["limit"], 30),
        "maxResultsShorts": 0,
        "maxResultStreams": 0,
    },
    "bluesky": lambda q: {
        "queries": q["keywords"],
        "limit": min(q["limit"], 50),
        "sort": "latest",
        "lang": "en",
        **({"since": since_day(q.get("since"))} if since_day(q.get("since")) else {}),
    },
    "instagram": lambda q: {
        "hashtags": [h for h in (hashtag_of(k) for k in q["keywords"]) if h],
        "resultsType": "posts",
        "resultsLimit": min(q["limit"], 30),
    },
    "tiktok": lambda q: {"searchQueries": q["keywords"], "resultsPerPage": min(q["limit"], 30)},
}

NORMALIZERS = {
    "reddit": lambda i: post(
        "reddit",
        {
            "id": i.get("id"),
            "url": i.get("url") or i.get("link"),
            "handle": i.get("username") or i.get("author") or "unknown",
            "title": i.get("title"),
            "text": i.get("body") or i.get("title") or "",
            "createdAt": i.get("createdAt") or i.get("created_utc"),
            "score": i.get("upVotes") if i.get("upVotes") is not None else i.get("score"),
            "comments": i.get("numberOfComments")
            if i.get("numberOfComments") is not None
            else i.get("numComments"),
            "subreddit": i.get("communityName") or i.get("parsedCommunityName"),
        },
    ),
    "x": lambda i: post(
        "x",
        {
            "id": i.get("id"),
            "url": i.get("url") or i.get("twitterUrl"),
            "handle": (i.get("author") or {}).get("userName")
            or (i.get("author") or {}).get("username")
            or "unknown",
            "displayName": (i.get("author") or {}).get("name"),
            "text": i.get("text") or i.get("fullText") or "",
            "createdAt": i.get("createdAt"),
            "score": i.get("likeCount"),
            "comments": i.get("replyCount"),
            "views": i.get("viewCount"),
        },
    ),
    "linkedin": lambda i: post(
        "linkedin",
        {
            "id": i.get("urn") or i.get("url"),
            "url": i.get("url") or i.get("post_url"),
            "handle": (i.get("author") or {}).get("username")
            or (i.get("author") or {}).get("name")
            or i.get("author_name")
            or "unknown",
            "displayName": (i.get("author") or {}).get("name") or i.get("author_name"),
            "text": i.get("text") or i.get("post_text") or "",
            "createdAt": (i.get("posted_at") or {}).get("date")
            or i.get("date_posted")
            or i.get("postedAt"),
            "score": (i.get("stats") or {}).get("total_reactions")
            or i.get("reactions_count")
            or i.get("likes"),
            "comments": (i.get("stats") or {}).get("comments") or i.get("comments_count"),
        },
    ),
    "youtube": lambda i: post(
        "youtube",
        {
            "id": i.get("id"),
            "url": i.get("url"),
            "handle": i.get("channelName") or "unknown",
            "title": i.get("title"),
            "text": i.get("text") or i.get("description") or i.get("title") or "",
            "createdAt": i.get("date"),
            "score": i.get("likes"),
            "comments": i.get("commentsCount"),
            "views": i.get("viewCount"),
        },
    ),
    "bluesky": lambda i: post(
        "bluesky",
        {
            "id": i.get("uri") or i.get("url"),
            "url": i.get("url"),
            "handle": (i.get("author") or {}).get("handle") or "unknown",
            "displayName": (i.get("author") or {}).get("displayName")
            or (i.get("author") or {}).get("name"),
            "text": i.get("text") or (i.get("record") or {}).get("text") or "",
            "createdAt": i.get("createdAt") or (i.get("record") or {}).get("createdAt"),
            "score": i.get("likeCount") if i.get("likeCount") is not None else i.get("likes"),
            "comments": i.get("replyCount")
            if i.get("replyCount") is not None
            else i.get("replies"),
        },
    ),
    "instagram": lambda i: post(
        "instagram",
        {
            "id": i.get("id"),
            "url": i.get("url"),
            "handle": i.get("ownerUsername") or "unknown",
            "text": i.get("caption") or "",
            "createdAt": i.get("timestamp"),
            "score": i.get("likesCount"),
            "comments": i.get("commentsCount"),
            "tags": i.get("hashtags"),
        },
    ),
    "tiktok": lambda i: post(
        "tiktok",
        {
            "id": i.get("id"),
            "url": i.get("webVideoUrl"),
            "handle": (i.get("authorMeta") or {}).get("name") or "unknown",
            "displayName": (i.get("authorMeta") or {}).get("nickName"),
            "text": i.get("text") or "",
            "createdAt": i.get("createTimeISO") or i.get("createTime"),
            "score": i.get("diggCount"),
            "comments": i.get("commentCount"),
            "views": i.get("playCount"),
        },
    ),
}


class ApifySocialAdapter(SocialSearchAdapter):
    id = "apify"
    name = "Apify"
    capabilities = frozenset(f"search.{p}" for p in INPUTS)

    def configured(self) -> bool:
        return apify.configured()

    async def search_posts(self, platform, query):
        entry = platform_entry(platform)
        build = INPUTS.get(platform)
        normalize = NORMALIZERS.get(platform)
        if not entry or not entry.get("actor") or not build or not normalize:
            raise self.unsupported(f"search.{platform}")
        keywords = [k for k in query.get("keywords") or [] if k][:MAX_KEYWORDS]
        actor_input = build({**query, "keywords": keywords, "limit": query.get("limit") or 30})
        run = await apify.run_actor(self.id, entry["actor"], actor_input)
        posts = [normalize(i) for i in run.data if isinstance(i, dict)]
        return VendorResponse([p for p in posts if p], run.cost_micros)
