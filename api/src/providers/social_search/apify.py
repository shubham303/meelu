from src.providers import apify
from src.providers.registry import VendorResponse
from src.providers.social_search.actors import (
    ActorSpec,
    SearchQuery,
    facebook,
    linkedin,
    reddit,
    x,
)
from src.providers.social_search.adapter import SocialSearchAdapter, search_result
from src.providers.social_search.shape import epoch_seconds

ACTORS: list[ActorSpec] = [
    *reddit.ACTORS,
    *x.ACTORS,
    *linkedin.ACTORS,
    *facebook.ACTORS,
]


def search_query(query: dict) -> SearchQuery:
    keywords = [str(k).strip() for k in query.get("keywords") or [] if str(k).strip()]
    return SearchQuery(
        keywords=keywords, since=query.get("since"), per_keyword=int(query["per_keyword"])
    )


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

    async def max_cost_micros(self, keyword_count: int, per_keyword: int) -> int | None:
        return await apify.max_charge_micros(
            self.id, self.spec.actor_id, self.spec.charges, 1, keyword_count * per_keyword
        )

    async def search_posts(self, platform, query):
        if platform != self.spec.platform:
            raise self.unsupported(f"search.{platform}")
        q = search_query(query)
        if not q.keywords:
            return VendorResponse(search_result([], []))
        run = await apify.run_actor(
            self.id, self.spec.actor_id, self.spec.build_input(q), q.run_cap(), self.spec.charges
        )
        return VendorResponse(search_result(self._posts(run.data, q.since), []), run.cost_micros)

    def _posts(self, rows: list, since: str | None) -> list[dict]:
        posts = [self.spec.normalize(i) for i in rows if isinstance(i, dict)]
        unique = {p["id"]: p for p in posts if p}
        return posted_since(list(unique.values()), since)


def apify_adapters() -> list[ApifyActorAdapter]:
    return [ApifyActorAdapter(spec) for spec in ACTORS]
