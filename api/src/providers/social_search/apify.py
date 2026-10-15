import asyncio

from src.providers import apify
from src.providers.errors import ProviderRequestError
from src.providers.registry import VendorResponse
from src.providers.social_search.actors import (
    ActorSpec,
    SearchQuery,
    bluesky,
    facebook,
    linkedin,
    reddit,
    x,
)
from src.providers.social_search.adapter import SocialSearchAdapter, search_result
from src.providers.social_search.shape import epoch_seconds

SINGLE_QUERY_CONCURRENCY = 3

ACTORS: list[ActorSpec] = [
    *reddit.ACTORS,
    *x.ACTORS,
    *linkedin.ACTORS,
    *bluesky.ACTORS,
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

    async def search_posts(self, platform, query):
        if platform != self.spec.platform:
            raise self.unsupported(f"search.{platform}")
        q = search_query(query)
        if not q.keywords:
            return VendorResponse(search_result([], []))
        if self.spec.one_query_per_run:
            return await self._run_each_keyword(q)
        run = await apify.run_actor(
            self.id, self.spec.actor_id, self.spec.build_input(q), q.run_cap(), self.spec.charges
        )
        return VendorResponse(search_result(self._posts(run.data, q.since), []), run.cost_micros)

    async def _run_each_keyword(self, q: SearchQuery) -> VendorResponse:
        slots = asyncio.Semaphore(SINGLE_QUERY_CONCURRENCY)

        async def one(keyword: str):
            single = SearchQuery(keywords=[keyword], since=q.since, per_keyword=q.per_keyword)
            async with slots:
                return await apify.run_actor(
                    self.id,
                    self.spec.actor_id,
                    self.spec.build_input(single),
                    single.run_cap(),
                    self.spec.charges,
                )

        outcomes = await asyncio.gather(*(one(k) for k in q.keywords), return_exceptions=True)
        rows, failed, cost, last_error = [], [], 0, None
        for keyword, outcome in zip(q.keywords, outcomes):
            if isinstance(outcome, ProviderRequestError):
                failed.append(keyword)
                last_error = outcome
                continue
            if isinstance(outcome, BaseException):
                raise outcome
            rows.extend(outcome.data)
            cost += outcome.cost_micros
        if last_error is not None and len(failed) == len(q.keywords):
            raise last_error
        return VendorResponse(search_result(self._posts(rows, q.since), failed), cost)

    def _posts(self, rows: list, since: str | None) -> list[dict]:
        posts = [self.spec.normalize(i) for i in rows if isinstance(i, dict)]
        unique = {p["id"]: p for p in posts if p}
        return posted_since(list(unique.values()), since)


def apify_adapters() -> list[ApifyActorAdapter]:
    return [ApifyActorAdapter(spec) for spec in ACTORS]
