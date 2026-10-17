from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.providers.registry import Caller
from src.seo.keyword_clusters.constants import (
    DEFAULT_COMPETITOR_CLUSTERS,
    DEFAULT_IMPRESSIONS_LOOKBACK,
    DEFAULT_METRICS_LIMIT,
    DEFAULT_SEARCH_CONSOLE_QUERIES,
    MAX_METRICS_LIMIT,
)
from src.seo.keyword_clusters.schemas import (
    ClusterRecord,
    ClustersDeleted,
    ClustersDeleteRequest,
    CompetitorClustersRequest,
    KeywordsClusterRequest,
    MetricsComputed,
    SearchConsoleClustersRequest,
    SeedClustersRequest,
)
from src.seo.keyword_clusters.service import keyword_cluster_service
from src.sites.service import site_service

DESK = "seo"


@tool(writes=True, desk=DESK)
async def create_keyword_clusters_from_seeds(
    seeds: list[str], min_volume: int | None = None
) -> list[str]:
    """Grow seed keywords through the vendor and cluster the results into
    `seo_keyword_clusters`: noise and off-topic keywords are dropped, then keywords Google
    answers with the same pages share one cluster. min_volume replaces the relative noise
    floor only when a hard limit is wanted. Returns the main keyword of every cluster it
    created or grew, highest volume first. Spends vendor credit."""
    ctx = require_site()
    body = SeedClustersRequest(seeds=seeds, min_volume=min_volume)
    async with unit_of_work() as db:
        site = await site_service.get(db, ctx.user_id, ctx.site_id)
        return await keyword_cluster_service.from_seeds(
            db, Caller(user_id=ctx.user_id, site_id=ctx.site_id), ctx.user_id, site, body
        )


@tool(writes=True, desk=DESK)
async def add_keywords_to_clusters(keywords: list[str]) -> list[tuple[str, str]]:
    """Put keywords you already have into `seo_keyword_clusters` without growing them or
    filtering them: each joins the existing cluster Google answers with the same pages, or
    starts a new one, and an unclustered core keyword is clustered too. Returns
    (keyword, cluster_id) per keyword. Spends vendor credit."""
    ctx = require_site()
    body = KeywordsClusterRequest(keywords=keywords)
    async with unit_of_work() as db:
        site = await site_service.get(db, ctx.user_id, ctx.site_id)
        return await keyword_cluster_service.add_keywords(
            db, Caller(user_id=ctx.user_id, site_id=ctx.site_id), ctx.user_id, site, body
        )


@tool(writes=True, desk=DESK)
async def create_keyword_clusters_from_search_console(
    limit: int = DEFAULT_SEARCH_CONSOLE_QUERIES, min_volume: int | None = None
) -> list[str]:
    """Cluster this website's Search Console queries, most impressions first, into
    `seo_keyword_clusters` the same way as seed clusters, without growing them. Returns the
    main keyword of every cluster it created or grew, highest volume first. Spends vendor
    credit on volumes only."""
    ctx = require_site()
    body = SearchConsoleClustersRequest(limit=limit, min_volume=min_volume)
    async with unit_of_work() as db:
        site = await site_service.get(db, ctx.user_id, ctx.site_id)
        return await keyword_cluster_service.from_search_console(
            db, Caller(user_id=ctx.user_id, site_id=ctx.site_id), ctx.user_id, site, body
        )


@tool(writes=True, desk=DESK)
async def create_keyword_clusters_from_competitors(
    limit: int = DEFAULT_COMPETITOR_CLUSTERS,
    min_volume: int | None = None,
    lookback: int = DEFAULT_IMPRESSIONS_LOOKBACK,
) -> list[str]:
    """Save keywords the saved competitors rank for but this website got no Search Console
    impressions for in the last `lookback` days (28, at most 180), one keyword per cluster
    with no grouping. Noise and off-topic keywords are dropped, then at most `limit` (100)
    are picked at random. Returns the main keyword of every cluster saved, highest volume
    first. Spends vendor credit."""
    ctx = require_site()
    body = CompetitorClustersRequest(limit=limit, min_volume=min_volume, lookback=lookback)
    async with unit_of_work() as db:
        site = await site_service.get(db, ctx.user_id, ctx.site_id)
        return await keyword_cluster_service.from_competitors(
            db, Caller(user_id=ctx.user_id, site_id=ctx.site_id), ctx.user_id, site, body
        )


@tool(writes=True, desk=DESK)
async def compute_metrics_for_cluster(
    cluster_ids: list[str] | None = None, limit: int = DEFAULT_METRICS_LIMIT
) -> MetricsComputed:
    """Score how winnable each keyword cluster's main keyword is for this website (0-100,
    from the authority and intent fit of the results above it) and save it on the cluster.
    Without ids it scores the highest-volume clusters that have no score or a stale one.
    A cluster whose results page is poisoned gets no score. Spends vendor credit."""
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


@tool(writes=True, desk=DESK)
async def remove_keywords_from_cluster(cluster_id: str, keywords: list[str]) -> ClusterRecord:
    """Take keywords out of one keyword cluster and lower the cluster's volume by theirs.
    Nothing is removed if any keyword is not in the cluster or is its main keyword; delete
    the cluster instead. Only when the user asks. Spends vendor credit on their volumes."""
    ctx = require_site()
    body = KeywordsClusterRequest(keywords=keywords)
    async with unit_of_work() as db:
        return await keyword_cluster_service.remove_keywords(
            db, Caller(user_id=ctx.user_id, site_id=ctx.site_id), ctx.site_id, cluster_id, body
        )


@tool(writes=True, desk=DESK)
async def delete_keyword_clusters(
    cluster_ids: list[str] | None = None, keywords: list[str] | None = None
) -> ClustersDeleted:
    """Delete keyword clusters by id and/or by any keyword they contain. Ids and keywords
    that match no cluster are reported back. Only when the user asks."""
    ctx = require_site()
    body = ClustersDeleteRequest(cluster_ids=cluster_ids or [], keywords=keywords or [])
    async with unit_of_work() as db:
        site = await site_service.get(db, ctx.user_id, ctx.site_id)
        return await keyword_cluster_service.delete_many(db, site, body)
