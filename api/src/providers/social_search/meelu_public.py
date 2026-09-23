import re

from src.providers.http import vendor_request
from src.providers.registry import VendorResponse
from src.providers.social_search.adapter import SocialSearchAdapter
from src.providers.social_search.shape import epoch_seconds, post, strip_html

MAX_KEYWORDS = 3
STACK_SITES = ("stackoverflow", "webmasters")


class MeeluPublicAdapter(SocialSearchAdapter):
    id = "meelu-public"
    name = "Meelu public APIs"
    capabilities = frozenset(
        {"search.hackernews", "search.stackexchange", "search.devto", "search.github"}
    )
    charges = False

    async def search_posts(self, platform, query):
        handler = {
            "hackernews": self.hacker_news,
            "stackexchange": self.stack_exchange,
            "devto": self.dev_to,
            "github": self.github,
        }.get(platform)
        if handler is None:
            raise self.unsupported(f"search.{platform}")
        posts = await handler(query)
        return VendorResponse([p for p in posts if p])

    @staticmethod
    def keywords_of(query: dict) -> list[str]:
        return [k for k in query.get("keywords") or [] if k][:MAX_KEYWORDS]

    async def hacker_news(self, query):
        start = epoch_seconds(query.get("since"))
        limit = min(query.get("limit") or 30, 30)
        out = []
        for keyword in self.keywords_of(query):
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

    async def stack_exchange(self, query):
        start = epoch_seconds(query.get("since"))
        limit = min(query.get("limit") or 30, 30)
        out = []
        for keyword in self.keywords_of(query):
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
        return out

    async def dev_to(self, query):
        limit = min(query.get("limit") or 30, 30)
        tags: dict[str, None] = {}
        for keyword in self.keywords_of(query):
            for word in str(keyword).lower().split():
                clean = re.sub(r"[^a-z0-9]", "", word)
                if len(clean) > 2:
                    tags[clean] = None
        out = []
        for tag in list(tags)[:4]:
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

    async def github(self, query):
        day = str(query.get("since") or "")[:10]
        limit = min(query.get("limit") or 30, 30)
        out = []
        for keyword in self.keywords_of(query):
            q = " ".join([keyword, "type:issue", *([f"created:>={day}"] if day else [])])
            res = await vendor_request(
                self.id,
                "https://api.github.com/search/issues",
                headers={"accept": "application/vnd.github+json", "user-agent": "meelu-api"},
                query={"q": q, "sort": "created", "order": "desc", "per_page": limit},
            )
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
                            "tags": [
                                l.get("name") for l in item.get("labels") or [] if l.get("name")
                            ],
                        },
                    )
                )
        return out
