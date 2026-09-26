from datetime import UTC, datetime
from statistics import median
from typing import Any

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import unit_of_work
from src.seo.clusters.repository import seo_keyword_clusters
from src.seo.constants import CLUSTER_ATTACH_DISTANCE, CLUSTER_DISTANCE, CLUSTER_MAX_KEYWORDS
from src.seo.keyword_content_pages.repository import seo_keyword_content_pages
from src.seo.keyword_gsc_pages.repository import seo_keyword_gsc_pages
from src.seo.keywords.repository import seo_keywords
from src.seo.page_facts.repository import seo_page_facts
from src.seo.precompute.coverage import seo_coverage_service
from src.seo.state.repository import seo_site_states
from src.site_pages.repositories.chunks import site_chunks

EMBED_BATCH = 200

CENTROID_PAGE_TYPES = ("money", "hub")


def parse_vector(raw: str | None) -> np.ndarray | None:
    if not raw:
        return None
    return np.array([float(x) for x in raw.strip("[]").split(",")], dtype=np.float32)


def unit(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    return vector / norm if norm > 0 else vector


def vector_text(vector: np.ndarray) -> str:
    return "[" + ",".join(f"{float(x):.6f}" for x in vector) + "]"


def group_keywords(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    if len(rows) < 2:
        return [[r] for r in rows]
    matrix = np.stack([unit(r["vector"]) for r in rows])
    labels = AgglomerativeClustering(
        n_clusters=None, distance_threshold=CLUSTER_DISTANCE, metric="cosine", linkage="average"
    ).fit_predict(matrix)
    groups: dict[int, list[dict[str, Any]]] = {}
    for row, label in zip(rows, labels, strict=True):
        groups.setdefault(int(label), []).append(row)
    return list(groups.values())


class SeoClusterService:
    async def embed_pending(
        self, db: AsyncSession, embedder, model: str, site_id: str, batch: int = EMBED_BATCH
    ) -> int:
        done = 0
        while True:
            rows = await seo_keywords.pending_embedding(db, site_id, batch)
            if not rows:
                return done
            vectors = embedder.embed([f"query: {keyword}" for _, keyword in rows])
            await seo_keywords.set_embeddings(
                db,
                [
                    {"id": keyword_id, "embedding": vector_text(np.asarray(vector)), "model": model}
                    for (keyword_id, _), vector in zip(rows, vectors, strict=True)
                ],
            )
            done += len(rows)

    async def refresh_coverage(self, db: AsyncSession, user_id: str, site_id: str) -> int:
        keywords = await seo_keywords.list_embedded(db, site_id)
        await seo_coverage_service.refresh(db, user_id, site_id, keywords, attach=False)
        return len(keywords)

    async def site_centroid(self, db: AsyncSession, site_id: str) -> np.ndarray | None:
        page_ids = await seo_page_facts.live_page_ids(db, site_id, list(CENTROID_PAGE_TYPES))
        centroid = await site_chunks.mean_embedding(db, site_id, page_ids, ordinal=0)
        return None if centroid is None else np.array(centroid, dtype=np.float32)

    async def assign_owners(
        self, db: AsyncSession, site_id: str, members: dict[str, list[str]]
    ) -> None:
        cluster_of = {k: c for c, ids in members.items() for k in ids}
        keyword_ids = list(cluster_of)
        scores: list[tuple[str, str, float]] = [
            (cluster_of[r.keyword_id], r.page_id, float(r.coverage))
            for r in await seo_keyword_content_pages.list_for_keywords(db, site_id, keyword_ids)
        ] + [
            (cluster_of[r.keyword_id], r.page_id, float(r.coverage or 0))
            for r in await seo_keyword_gsc_pages.list_for_keywords(db, site_id, keyword_ids)
        ]
        live = {
            f.page_id
            for f in await seo_page_facts.list_by_page_ids(
                db, site_id, list({page_id for _, page_id, _ in scores})
            )
            if f.live
        }
        totals: dict[str, dict[str, float]] = {}
        for cluster_id, page_id, coverage in scores:
            if page_id in live:
                by_page = totals.setdefault(cluster_id, {})
                by_page[page_id] = by_page.get(page_id, 0.0) + coverage
        for cluster_id, by_page in totals.items():
            page_id, total = max(by_page.items(), key=lambda kv: (kv[1], kv[0]))
            await seo_keyword_clusters.set_owner(
                db, cluster_id, page_id, total / len(members[cluster_id])
            )

    async def rebuild_clusters(self, db: AsyncSession, user_id: str, site_id: str) -> int:
        rows = await seo_keywords.clusterable(db, site_id, CLUSTER_MAX_KEYWORDS)
        for r in rows:
            r["vector"] = parse_vector(r["embedding"])
        rows = [r for r in rows if r["vector"] is not None]
        site_centroid = await self.site_centroid(db, site_id)
        await seo_keyword_clusters.delete_for_site(db, site_id)
        at = datetime.now(UTC)
        centroids: list[tuple[str, np.ndarray]] = []
        members: dict[str, list[str]] = {}
        for group in group_keywords(rows):
            head = max(group, key=lambda r: (r["volume"] or 0, r["impressions_28d"]))
            centroid = unit(np.mean(np.stack([unit(r["vector"]) for r in group]), axis=0))
            difficulties = [r["difficulty"] for r in group if r["difficulty"] is not None]
            similarity = (
                float(np.dot(centroid, unit(site_centroid))) if site_centroid is not None else None
            )
            cluster_id = await seo_keyword_clusters.create(
                db,
                user_id,
                site_id,
                head["id"],
                vector_text(centroid),
                len(group),
                int(sum(r["volume"] or 0 for r in group)),
                float(median(difficulties)) if difficulties else None,
                similarity,
                at,
            )
            members[cluster_id] = [r["id"] for r in group]
            await seo_keywords.assign_cluster(db, cluster_id, members[cluster_id])
            centroids.append((cluster_id, centroid))
        rest = await seo_keywords.unclustered_embedded(db, site_id)
        if centroids and rest:
            matrix = np.stack([c for _, c in centroids])
            attached: dict[str, list[str]] = {}
            for r in rest:
                vector = parse_vector(r["embedding"])
                if vector is None:
                    continue
                distances = 1 - matrix @ unit(vector)
                best = int(np.argmin(distances))
                if distances[best] <= CLUSTER_ATTACH_DISTANCE:
                    attached.setdefault(centroids[best][0], []).append(r["id"])
            for cluster_id, keyword_ids in attached.items():
                members[cluster_id] += keyword_ids
                await seo_keywords.assign_cluster(db, cluster_id, keyword_ids)
        await self.assign_owners(db, site_id, members)
        return len(centroids)

    async def run_seo_pass(self, embedder, model: str) -> int:
        async with unit_of_work() as db:
            sites = await seo_site_states.list_awaiting_embedding(db)
        for site_id, user_id in sites:
            async with unit_of_work() as db:
                await self.embed_pending(db, embedder, model, site_id)
                await self.refresh_coverage(db, user_id, site_id)
                await self.rebuild_clusters(db, user_id, site_id)
                await seo_site_states.mark_embedded(db, site_id)
        return len(sites)


seo_cluster_service = SeoClusterService()
