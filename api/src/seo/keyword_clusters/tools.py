from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.providers.registry import Caller
from src.seo.keyword_clusters.constants import (
    DEFAULT_METRICS_LIMIT,
    DEFAULT_SOURCE_KEYWORDS,
    MAX_METRICS_LIMIT,
    ClusterSource,
)
from src.seo.keyword_clusters.schemas import (
    ClustersCreated,
    CreateClustersRequest,
    MetricsComputed,
)
from src.seo.keyword_clusters.service import keyword_cluster_service
from src.sites.service import site_service

DESK = "seo"


@tool(writes=True, desk=DESK)
async def create_keyword_clusters(
    source: ClusterSource = "seeds",
    seeds: list[str] | None = None,
    limit: int = DEFAULT_SOURCE_KEYWORDS,
    min_volume: int | None = None,
) -> ClustersCreated:
    """Build keyword clusters for this website into `seo_keyword_clusters` from one source:
    seed keywords grown by the vendor, its Search Console queries, the keywords it ranks for,
    or keywords two or more saved competitors rank for and it does not. Noise and off-topic
    keywords are dropped first, then keywords Google answers with the same pages are grouped
    under their highest-volume main keyword. min_volume replaces the relative noise floor only
    when a hard limit is wanted. Spends vendor credit."""
    ctx = require_site()
    body = CreateClustersRequest(
        source=source, seeds=seeds or [], limit=limit, min_volume=min_volume
    )
    async with unit_of_work() as db:
        site = await site_service.get(db, ctx.user_id, ctx.site_id)
        return await keyword_cluster_service.create_clusters(
            db, Caller(user_id=ctx.user_id, site_id=ctx.site_id), ctx.user_id, site, body
        )


@tool(writes=True, desk=DESK)
async def compute_metrics_for_cluster(
    cluster_ids: list[str] | None = None, limit: int = DEFAULT_METRICS_LIMIT
) -> MetricsComputed:
    """Score how winnable each keyword cluster's main keyword is for this website (0-100,
    from the authority and intent fit of the results above it) and save it on the cluster.
    Without ids it scores the highest-volume clusters that have no score or a stale one.
    Spends vendor credit."""
    ctx = require_site()
    async with unit_of_work() as db:
        site = await site_service.get(db, ctx.user_id, ctx.site_id)
        return await keyword_cluster_service.compute_metrics(
            db,
            Caller(user_id=ctx.user_id, site_id=ctx.site_id),
            site,
            cluster_ids,
            min(max(int(limit), 1), MAX_METRICS_LIMIT),
        )
