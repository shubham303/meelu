from src.providers import apify
from src.providers.registry import VendorResponse
from src.providers.social_search.actors import (
    ActorSpec,
    SearchQuery,
    bluesky,
    instagram,
    linkedin,
    reddit,
    tiktok,
    x,
    youtube,
)
from src.providers.social_search.adapter import SocialSearchAdapter
from src.providers.social_search.shape import epoch_seconds

MAX_KEYWORDS = 3
MAX_LIMIT = 100

ACTORS: list[ActorSpec] = [
    *reddit.ACTORS,
    *x.ACTORS,
    *linkedin.ACTORS,
    *youtube.ACTORS,
    *bluesky.ACTORS,
    *instagram.ACTORS,
    *tiktok.ACTORS,
]


def search_query(query: dict) -> SearchQuery:
    keywords = [str(k).strip() for k in query.get("keywords") or [] if str(k).strip()]
    limit = max(1, min(int(query.get("limit") or 30), MAX_LIMIT))
    return SearchQuery(keywords=keywords[:MAX_KEYWORDS], since=query.get("since"), limit=limit)


def posted_since(posts: list[dict], since: str | None) -> list[dict]:
    start = epoch_seconds(since)
    if start is None:
        return posts
    return [p for p in posts if (epoch_seconds(p["createdAt"]) or start) >= start]


class ApifyActorAdapter(SocialSearchAdapter):
    def __init__(self, spec: ActorSpec):
        self.spec = spec
        self.id = f"apify/{spec.actor_id}"
        self.name = f"Apify · {spec.actor_id}"
        self.capabilities = frozenset({f"search.{spec.platform}"})

    def configured(self) -> bool:
        return apify.configured()

    def vendor_query(self, platform: str, query: dict) -> dict:
        return {"actor": self.spec.actor_id, "input": self.spec.build_input(search_query(query))}

    async def search_posts(self, platform, query):
        if platform != self.spec.platform:
            raise self.unsupported(f"search.{platform}")
        q = search_query(query)
        if not q.keywords:
            return VendorResponse([])
        run = await apify.run_actor(
            self.id, self.spec.actor_id, self.spec.build_input(q), q.limit, self.spec.charges
        )
        posts = [self.spec.normalize(i) for i in run.data if isinstance(i, dict)]
        unique = {p["id"]: p for p in posts if p}
        return VendorResponse(
            posted_since(list(unique.values()), q.since)[: q.limit], run.cost_micros
        )


def apify_adapters() -> list[ApifyActorAdapter]:
    return [ApifyActorAdapter(spec) for spec in ACTORS]
