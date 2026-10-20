import asyncio
import re
from datetime import UTC, datetime

from src.providers.errors import ProviderRequestError
from src.providers.http import vendor_request
from src.providers.registry import VendorResponse
from src.providers.social_search.adapter import SocialSearchAdapter, search_result
from src.providers.social_search.shape import epoch_seconds, post, strip_html
from src.settings import settings

PAGE_SIZE = 30
STACK_SITES = ("stackoverflow", "webmasters")
DEVTO_TAGS_PER_KEYWORD = 2
BLUESKY_SEARCH = "https://api.bsky.app/xrpc/app.bsky.feed.searchPosts"


class MeeluPublicAdapter(SocialSearchAdapter):
    id = "meelu-public"
    name = "Meelu public APIs"
    capabilities = frozenset(
        {
            "search.hackernews",
            "search.stackexchange",
            "search.devto",
            "search.github",
            "search.bluesky",
        }
    )
    charges = False

    async def search_posts(self, platform, query):
        handler = {
            "hackernews": self.hacker_news,
            "stackexchange": self.stack_exchange,
            "devto": self.dev_to,
            "github": self.github,
            "bluesky": self.bluesky,
        }.get(platform)
        if handler is None:
            raise self.unsupported(f"search.{platform}")
        keywords = [k for k in query.get("keywords") or [] if k]
        since = query.get("since")
        limit = min(int(query["per_keyword"]), PAGE_SIZE)
        seen: set[str] = set()
        posts, failed, last_error = [], [], None
        for keyword in keywords:
            try:
                found = await handler(keyword, since, limit, seen)
            except ProviderRequestError as exc:
                failed.append(keyword)
                last_error = exc
                continue
            posts.extend(p for p in found if p)
        if last_error is not None and len(failed) == len(keywords):
            raise last_error
        return VendorResponse(search_result(posts, failed))

    async def hacker_news(self, keyword, since, limit, seen):
        start = epoch_seconds(since)
        out = []
        for tag in ("story", "comment"):
            res = await vendor_request(
                self.id,
                "https://hn.algolia.com/api/v1/search",
                query={
                    "query": keyword,
                    "tags": tag,
                    "hitsPerPage": limit,
                    **({"numericFilters": f"created_at_i>{start}"} if start else {}),
                },
            )
            for hit in (res or {}).get("hits") or []:
                hit_id = hit.get("objectID")
                out.append(
                    post(
                        "hackernews",
                        {
                            "id": hit_id,
                            "url": f"https://news.ycombinator.com/item?id={hit_id}",
                            "handle": hit.get("author"),
                            "title": hit.get("title") or hit.get("story_title"),
                            "text": strip_html(
                                hit.get("comment_text")
                                or hit.get("story_text")
                                or hit.get("title")
                                or ""
                            ),
                            "createdAt": hit.get("created_at"),
                            "score": hit.get("points"),
                            "comments": hit.get("num_comments"),
                        },
                    )
                )
        return out

    async def stack_exchange(self, keyword, since, limit, seen):
        start = epoch_seconds(since)
        out = []
        for site in STACK_SITES:
            res = await vendor_request(
                self.id,
                "https://api.stackexchange.com/2.3/search/advanced",
                query={
                    "q": keyword,
                    "site": site,
                    "order": "desc",
                    "sort": "creation",
                    "filter": "withbody",
                    "pagesize": limit,
                    "key": settings.stackexchange_key or None,
                    **({"fromdate": start} if start else {}),
                },
            )
            for item in (res or {}).get("items") or []:
                owner = item.get("owner") or {}
                out.append(
                    post(
                        "stackexchange",
                        {
                            "id": f"{site}-{item.get('question_id')}",
                            "url": item.get("link"),
                            "handle": owner.get("display_name") or "unknown",
                            "displayName": owner.get("display_name"),
                            "title": strip_html(item.get("title")),
                            "text": strip_html(item.get("body") or item.get("title") or ""),
                            "createdAt": item.get("creation_date"),
                            "score": item.get("score"),
                            "comments": item.get("answer_count"),
                            "views": item.get("view_count"),
                            "tags": item.get("tags"),
                        },
                    )
                )
            backoff = (res or {}).get("backoff")
            if isinstance(backoff, (int, float)) and backoff > 0:
                await asyncio.sleep(backoff)
        return out

    async def dev_to(self, keyword, since, limit, seen):
        tags = []
        for word in str(keyword).lower().split():
            clean = re.sub(r"[^a-z0-9]", "", word)
            if len(clean) > 2 and clean not in seen and clean not in tags:
                tags.append(clean)
        out = []
        for tag in tags[:DEVTO_TAGS_PER_KEYWORD]:
            seen.add(tag)
            res = await vendor_request(
                self.id, "https://dev.to/api/articles", query={"tag": tag, "per_page": limit}
            )
            for item in res if isinstance(res, list) else []:
                user = item.get("user") or {}
                out.append(
                    post(
                        "devto",
                        {
                            "id": item.get("id"),
                            "url": item.get("url"),
                            "handle": user.get("username") or "unknown",
                            "displayName": user.get("name"),
                            "title": item.get("title"),
                            "text": item.get("description") or item.get("title") or "",
                            "createdAt": item.get("published_at"),
                            "score": item.get("public_reactions_count"),
                            "comments": item.get("comments_count"),
                            "tags": item.get("tag_list"),
                        },
                    )
                )
        return out

    async def github(self, keyword, since, limit, seen):
        day = str(since or "")[:10]
        q = " ".join([keyword, "type:issue", *([f"created:>={day}"] if day else [])])
        headers = {"accept": "application/vnd.github+json", "user-agent": "meelu-api"}
        if settings.github_token:
            headers["authorization"] = f"Bearer {settings.github_token}"
        res = await vendor_request(
            self.id,
            "https://api.github.com/search/issues",
            headers=headers,
            query={"q": q, "sort": "created", "order": "desc", "per_page": limit},
        )
        out = []
        for item in (res or {}).get("items") or []:
            out.append(
                post(
                    "github",
                    {
                        "id": item.get("id"),
                        "url": item.get("html_url"),
                        "handle": (item.get("user") or {}).get("login") or "unknown",
                        "title": item.get("title"),
                        "text": str(item.get("body") or item.get("title") or "")[:4000],
                        "createdAt": item.get("created_at"),
                        "score": (item.get("reactions") or {}).get("total_count"),
                        "comments": item.get("comments"),
                        "tags": [l.get("name") for l in item.get("labels") or [] if l.get("name")],
                    },
                )
            )
        return out

    async def bluesky(self, keyword, since, limit, seen):
        start = epoch_seconds(since)
        res = await vendor_request(
            self.id,
            BLUESKY_SEARCH,
            query={
                "q": keyword,
                "sort": "latest",
                "lang": "en",
                "limit": limit,
                "since": datetime.fromtimestamp(start, UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                if start
                else None,
            },
        )
        return [bluesky_post(item) for item in (res or {}).get("posts") or []]


def bluesky_post(item: dict) -> dict | None:
    author = item.get("author") or {}
    record = item.get("record") or {}
    handle = author.get("handle")
    rkey = str(item.get("uri") or "").rsplit("/", 1)[-1]
    return post(
        "bluesky",
        {
            "id": item.get("uri"),
            "url": f"https://bsky.app/profile/{handle}/post/{rkey}" if handle and rkey else None,
            "handle": handle,
            "displayName": author.get("displayName"),
            "text": record.get("text") or "",
            "createdAt": record.get("createdAt") or item.get("indexedAt"),
            "score": item.get("likeCount"),
            "comments": item.get("replyCount"),
        },
    )
