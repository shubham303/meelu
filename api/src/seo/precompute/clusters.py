import re
from datetime import UTC, datetime
from statistics import median
from typing import Any

import numpy as np
from sklearn.cluster import AgglomerativeClustering

from src.core.ids import uid
from src.seo.constants import CLUSTER_ATTACH_DISTANCE, CLUSTER_DISTANCE, CLUSTER_MAX_KEYWORDS
from src.seo.precompute.embed import CONTENT_SQL, GSC_COVERAGE_SQL, PRUNE_CONTENT_SQL

SITES_SQL = """
select s.site_id, s.user_id from seo_site_state s
where s.precompute_requested_at > coalesce(s.embedded_at, '-infinity'::timestamptz)
"""

PENDING_SQL = """
select id, keyword from seo_keywords
where site_id = %(site_id)s and embedding is null and embed_error is null
order by seq limit %(limit)s
"""

SET_EMBEDDING_SQL = """
update seo_keywords set embedding = %(embedding)s::vector, embed_model = %(model)s, updated_at = now()
where id = %(id)s
"""

KEYWORD_IDS_SQL = (
    "select id from seo_keywords where site_id = %(site_id)s and embedding is not null"
)

CLUSTERABLE_SQL = """
select id, keyword, volume, difficulty, impressions_28d, embedding::text as embedding
from seo_keywords
where site_id = %(site_id)s and embedding is not null and not branded
  and (coalesce(volume, 0) > 0 or impressions_28d > 0)
order by coalesce(volume, 0) desc, impressions_28d desc
limit %(limit)s
"""

REST_SQL = """
select id, embedding::text as embedding from seo_keywords
where site_id = %(site_id)s and embedding is not null and cluster_id is null
"""

DELETE_CLUSTERS_SQL = "delete from seo_keyword_clusters where site_id = %(site_id)s"

INSERT_CLUSTER_SQL = """
insert into seo_keyword_clusters (id, user_id, site_id, head_keyword_id, centroid, size, volume_sum,
  difficulty_median, site_similarity, rebuilt_at, created_at, updated_at)
values (%(id)s, %(user_id)s, %(site_id)s, %(head)s, %(centroid)s::vector, %(size)s, %(volume)s,
  %(difficulty)s, %(similarity)s, %(now)s, %(now)s, %(now)s)
"""

ASSIGN_SQL = "update seo_keywords set cluster_id = %(cluster_id)s where id = any(%(ids)s)"

OWNER_SQL = """
with members as (select id from seo_keywords where cluster_id = %(cluster_id)s),
scores as (
  select cp.page_id, cp.coverage from seo_keyword_content_pages cp join members m on m.id = cp.keyword_id
  union all
  select g.page_id, coalesce(g.coverage, 0) from seo_keyword_gsc_pages g join members m on m.id = g.keyword_id
)
select s.page_id, sum(s.coverage) / (select count(*) from members) as mean_coverage
from scores s join seo_page_facts f on f.page_id = s.page_id and f.live
group by s.page_id order by mean_coverage desc limit 1
"""

SET_OWNER_SQL = """
update seo_keyword_clusters set owner_page_id = %(page_id)s, owner_coverage = %(coverage)s
where id = %(cluster_id)s
"""

SITE_CENTROID_SQL = """
select avg(c.embedding)::text as centroid
from site_chunks c
join seo_page_facts f on f.page_id = c.page_id
where c.site_id = %(site_id)s and c.ordinal = 0 and c.embedding is not null and f.live
  and f.page_type in ('money', 'hub')
"""

STAMP_SQL = "update seo_site_state set embedded_at = %(now)s, updated_at = %(now)s where site_id = %(site_id)s"


def psycopg_sql(sqlalchemy_text: str) -> str:
    return re.sub(r"(?<![:\w]):(\w+)", r"%(\1)s", sqlalchemy_text)


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


def embed_pending(db, embedder, model: str, site_id: str, batch: int = 200) -> int:
    done = 0
    while True:
        rows, _ = db.query(PENDING_SQL, {"site_id": site_id, "limit": batch})
        if not rows:
            return done
        vectors = embedder.embed([f"query: {r['keyword']}" for r in rows])
        for row, vector in zip(rows, vectors, strict=True):
            db.query(
                SET_EMBEDDING_SQL,
                {"id": row["id"], "embedding": vector_text(np.asarray(vector)), "model": model},
            )
            done += 1


def refresh_coverage(db, user_id: str, site_id: str) -> int:
    rows, _ = db.query(KEYWORD_IDS_SQL, {"site_id": site_id})
    started = datetime.now(UTC)
    for row in rows:
        params = {
            "user_id": user_id,
            "site_id": site_id,
            "keyword_id": row["id"],
            "started": started,
        }
        db.query(psycopg_sql(CONTENT_SQL), params)
        db.query(psycopg_sql(PRUNE_CONTENT_SQL), params)
        db.query(psycopg_sql(GSC_COVERAGE_SQL), params)
    return len(rows)


def rebuild_clusters(db, user_id: str, site_id: str) -> int:
    rows, _ = db.query(CLUSTERABLE_SQL, {"site_id": site_id, "limit": CLUSTER_MAX_KEYWORDS})
    for r in rows:
        r["vector"] = parse_vector(r["embedding"])
    rows = [r for r in rows if r["vector"] is not None]
    site_row, _ = db.query(SITE_CENTROID_SQL, {"site_id": site_id})
    site_centroid = parse_vector(site_row[0]["centroid"]) if site_row else None
    db.query(DELETE_CLUSTERS_SQL, {"site_id": site_id})
    now = datetime.now(UTC)
    centroids: list[tuple[str, np.ndarray]] = []
    for members in group_keywords(rows):
        head = max(members, key=lambda r: (r["volume"] or 0, r["impressions_28d"]))
        centroid = unit(np.mean(np.stack([unit(r["vector"]) for r in members]), axis=0))
        difficulties = [r["difficulty"] for r in members if r["difficulty"] is not None]
        similarity = (
            float(np.dot(centroid, unit(site_centroid))) if site_centroid is not None else None
        )
        cluster_id = uid("cl")
        db.query(
            INSERT_CLUSTER_SQL,
            {
                "id": cluster_id,
                "user_id": user_id,
                "site_id": site_id,
                "head": head["id"],
                "centroid": vector_text(centroid),
                "size": len(members),
                "volume": int(sum(r["volume"] or 0 for r in members)),
                "difficulty": float(median(difficulties)) if difficulties else None,
                "similarity": similarity,
                "now": now,
            },
        )
        db.query(ASSIGN_SQL, {"cluster_id": cluster_id, "ids": [r["id"] for r in members]})
        centroids.append((cluster_id, centroid))
    rest, _ = db.query(REST_SQL, {"site_id": site_id})
    if centroids and rest:
        matrix = np.stack([c for _, c in centroids])
        for r in rest:
            vector = parse_vector(r["embedding"])
            if vector is None:
                continue
            distances = 1 - matrix @ unit(vector)
            best = int(np.argmin(distances))
            if distances[best] <= CLUSTER_ATTACH_DISTANCE:
                db.query(ASSIGN_SQL, {"cluster_id": centroids[best][0], "ids": [r["id"]]})
    for cluster_id, _ in centroids:
        owner, _ = db.query(OWNER_SQL, {"cluster_id": cluster_id})
        if owner:
            db.query(
                SET_OWNER_SQL,
                {
                    "cluster_id": cluster_id,
                    "page_id": owner[0]["page_id"],
                    "coverage": float(owner[0]["mean_coverage"] or 0),
                },
            )
    return len(centroids)


def run_seo_pass(db, embedder, model: str) -> int:
    sites, _ = db.query(SITES_SQL)
    for site in sites:
        site_id, user_id = site["site_id"], site["user_id"]
        embed_pending(db, embedder, model, site_id)
        refresh_coverage(db, user_id, site_id)
        rebuild_clusters(db, user_id, site_id)
        db.query(STAMP_SQL, {"site_id": site_id, "now": datetime.now(UTC)})
    return len(sites)
