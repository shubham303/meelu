from typing import Any

from src.providers import apify
from src.providers.apify import ChargeEvents
from src.providers.people_search.adapter import PeopleSearchAdapter
from src.providers.registry import VendorResponse
from src.providers.social_search.shape import iso_date, strip_html

PROFILE_SEARCH = "harvestapi~linkedin-profile-search"
PROFILE_POSTS = "harvestapi~linkedin-profile-posts"
REDDIT_USERS = "harshmaur~reddit-user-scraper"
SEARCH_CHARGE_CAP_USD = 0.5
TEXT_CHARS = 500
PAGE_CHARGES_ONLY = ChargeEvents(result="")


def clip(text: Any) -> str:
    return " ".join(str(text or "").split())[:TEXT_CHARS]


def url_key(url: str) -> str:
    return url.strip().lower().rstrip("/")


def headline(profile: dict) -> str | None:
    if profile.get("headline"):
        return clip(profile["headline"])
    positions = profile.get("currentPositions") or []
    first = positions[0] if positions and isinstance(positions[0], dict) else {}
    title, company = first.get("title"), first.get("companyName")
    if title and company:
        return f"{title} at {company}"
    return title or company or None


def linkedin_person(item: dict) -> dict | None:
    url = item.get("linkedinUrl")
    if not url:
        return None
    name = " ".join(p for p in (item.get("firstName"), item.get("lastName")) if p).strip()
    location = (item.get("location") or {}).get("linkedinText")
    return {
        "id": str(item.get("id") or url),
        "name": name or None,
        "headline": headline(item),
        "profileUrl": url,
        "location": location,
        "summary": clip(item.get("summary")),
    }


def linkedin_post(item: dict) -> tuple[str, dict] | None:
    target = ((item.get("query") or {}).get("targetUrl")) or ""
    if item.get("type") not in (None, "post") or not target:
        return None
    posted = item.get("postedAt") or {}
    return url_key(target), {
        "url": item.get("linkedinUrl") or item.get("shareLinkedinUrl"),
        "text": clip(item.get("content")),
        "at": iso_date(posted.get("timestamp") or posted.get("date")),
        "kind": "post",
    }


def reddit_item(item: dict) -> tuple[str, dict] | None:
    kind = item.get("dataType")
    if kind == "user_profile":
        bio = clip(item.get("bio") or item.get("profileDescription"))
        if not bio:
            return None
        return str(item.get("username") or "").lower(), {
            "url": item.get("profileUrl"),
            "text": bio,
            "at": None,
            "kind": "profile",
        }
    author = str(item.get("authorName") or "").lower()
    if kind == "post":
        text = " — ".join(p for p in (clip(item.get("title")), clip(item.get("body"))) if p)
        return author, {
            "url": item.get("postUrl") or item.get("contentUrl"),
            "text": text[:TEXT_CHARS],
            "at": iso_date(item.get("createdAt")),
            "kind": "post",
            "where": item.get("communityName"),
        }
    if kind == "comment":
        return author, {
            "url": item.get("url"),
            "text": clip(strip_html(item.get("body"))),
            "at": iso_date(item.get("commentCreatedAt")),
            "kind": "comment",
            "where": f"r/{item.get('subredditName')}" if item.get("subredditName") else None,
        }
    return None


def grouped(pairs: list[tuple[str, dict] | None], wanted: dict[str, str]) -> dict[str, list]:
    out: dict[str, list] = {person: [] for person in wanted.values()}
    for pair in pairs:
        if pair is None:
            continue
        key, entry = pair
        person = wanted.get(key)
        if person is not None and entry.get("url") and entry.get("text"):
            out[person].append(entry)
    return out


class LinkedinProfileSearchAdapter(PeopleSearchAdapter):
    id = f"apify/{PROFILE_SEARCH}"
    name = f"Apify · {PROFILE_SEARCH}"
    capabilities = frozenset({"search.linkedin"})

    def configured(self) -> bool:
        return apify.configured()

    def actor_input(self, query: dict) -> dict:
        body: dict[str, Any] = {
            "searchQuery": query["query"],
            "profileScraperMode": "Short",
            "maxItems": query["limit"],
            "startPage": query.get("page") or 1,
            "takePages": 1,
        }
        if query.get("titles"):
            body["currentJobTitles"] = query["titles"]
        if query.get("locations"):
            body["locations"] = query["locations"]
        return body

    def vendor_query(self, capability: str, query: dict) -> dict:
        return {"actor": PROFILE_SEARCH, "input": self.actor_input(query)}

    async def search_people(self, query: dict) -> VendorResponse:
        run = await apify.run_actor(
            self.id,
            PROFILE_SEARCH,
            self.actor_input(query),
            query["limit"],
            PAGE_CHARGES_ONLY,
            SEARCH_CHARGE_CAP_USD,
        )
        people = [linkedin_person(i) for i in run.data if isinstance(i, dict)]
        return VendorResponse([p for p in people if p], run.cost_micros)


class LinkedinActivityAdapter(PeopleSearchAdapter):
    id = f"apify/{PROFILE_POSTS}"
    name = f"Apify · {PROFILE_POSTS}"
    capabilities = frozenset({"activity.linkedin"})

    def configured(self) -> bool:
        return apify.configured()

    def actor_input(self, query: dict) -> dict:
        return {
            "targetUrls": query["people"],
            "maxPosts": query["per_person"],
            "postedLimit": "month",
            "includeReposts": False,
        }

    def vendor_query(self, capability: str, query: dict) -> dict:
        return {"actor": PROFILE_POSTS, "input": self.actor_input(query)}

    async def activity(self, platform: str, query: dict) -> VendorResponse:
        if platform != "linkedin":
            raise self.unsupported(f"activity.{platform}")
        run = await apify.run_actor(
            self.id,
            PROFILE_POSTS,
            self.actor_input(query),
            query["per_person"] * len(query["people"]),
            ChargeEvents(result="post", start="apify-actor-start"),
        )
        wanted = {url_key(p): p for p in query["people"]}
        pairs = [linkedin_post(i) for i in run.data if isinstance(i, dict)]
        return VendorResponse(grouped(pairs, wanted), run.cost_micros)


class RedditActivityAdapter(PeopleSearchAdapter):
    id = f"apify/{REDDIT_USERS}"
    name = f"Apify · {REDDIT_USERS}"
    capabilities = frozenset({"activity.reddit"})

    def configured(self) -> bool:
        return apify.configured()

    def actor_input(self, query: dict) -> dict:
        half = max(query["per_person"] // 2, 1)
        return {
            "usernames": query["people"],
            "maxPostsCount": query["per_person"] - half,
            "maxCommentsCount": half,
        }

    def vendor_query(self, capability: str, query: dict) -> dict:
        return {"actor": REDDIT_USERS, "input": self.actor_input(query)}

    async def activity(self, platform: str, query: dict) -> VendorResponse:
        if platform != "reddit":
            raise self.unsupported(f"activity.{platform}")
        run = await apify.run_actor(
            self.id,
            REDDIT_USERS,
            self.actor_input(query),
            (query["per_person"] + 1) * len(query["people"]),
            ChargeEvents(result="result", start="init"),
        )
        wanted = {p.lower(): p for p in query["people"]}
        pairs = [reddit_item(i) for i in run.data if isinstance(i, dict)]
        return VendorResponse(grouped(pairs, wanted), run.cost_micros)


def apify_people_adapters() -> list[PeopleSearchAdapter]:
    return [LinkedinProfileSearchAdapter(), LinkedinActivityAdapter(), RedditActivityAdapter()]
