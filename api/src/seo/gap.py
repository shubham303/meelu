from collections import defaultdict
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.seo import collect, suggestions
from src.seo import repository as repo
from src.seo.constants import (
    ADJACENT_DISTANCE,
    CLUSTER_ATTACH_DISTANCE,
    OWNER_COVERAGE,
    SITE_SIMILARITY_PCT,
)
from src.seo.schemas import CreateResult, NewPageSuggestion

SIMILARITY_CUTOFF_SQL = """
select percentile_cont(:pct / 100.0) within group (order by site_similarity)
from seo_keyword_clusters where site_id = :site_id and site_similarity is not null
"""

GAP_ROWS_SQL = """
select c.id as cluster_id, hk.keyword as topic_key, hk.id as head_id, c.volume_sum,
       c.difficulty_median, c.owner_page_id, c.owner_coverage, c.site_similarity,
       k.id as keyword_id, k.keyword, k.volume, k.intent,
       ck.competitor_id, cm.domain, ck.position, ck.url
from seo_keyword_clusters c
join seo_keywords hk on hk.id = c.head_keyword_id
join seo_keywords k on k.cluster_id = c.id and not k.branded
  and coalesce(k.intent, '') <> 'navigational'
join seo_competitor_keywords ck on ck.keyword_id = k.id and ck.position <= 10
join seo_competitors cm on cm.id = ck.competitor_id and cm.state = 'confirmed'
where c.site_id = :site_id
  and (c.owner_page_id is null or coalesce(c.owner_coverage, 0) < :owner)
  and (cast(:keyword_ids as text[]) is null or k.id = any(cast(:keyword_ids as text[])))
"""

ADJACENT_SQL = """
select exists (
  select 1 from seo_keyword_clusters n
  join seo_keywords k on k.cluster_id = n.id
  left join seo_keyword_gsc_pages g on g.keyword_id = k.id and g.position <= 30
  where n.site_id = :site_id and n.id <> :cluster_id and n.centroid is not null
    and (n.centroid <=> (select centroid from seo_keyword_clusters where id = :cluster_id)) <= :distance
    and (g.id is not null or k.our_position <= 30)
)
"""

TOPIC_ROWS_SQL = """
select k.id, k.keyword, k.volume, k.difficulty, k.intent, k.cluster_id, k.embedding,
       hk.keyword as head
from seo_keywords k
left join seo_keyword_clusters c on c.id = k.cluster_id
left join seo_keywords hk on hk.id = c.head_keyword_id
where k.site_id = :site_id and (k.id = :topic_id or k.seed_keyword_id = :topic_id)
  and not k.branded
"""

COVERED_HEAD_SQL = """
select max(coverage) from seo_keyword_content_pages cp
join seo_page_facts f on f.page_id = cp.page_id and f.live
where cp.keyword_id = :keyword_id
"""


def _score(volume: int, difficulty: float | None, competitors: int) -> float:
    return volume * (1 + competitors) / ((difficulty or 50) + 1)


async def propose_gap_pages(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    job_id: str,
    keyword_ids: list[str] | None,
    min_volume: int,
    max_difficulty: int,
) -> CreateResult:
    cutoff = (
        await db.execute(
            text(SIMILARITY_CUTOFF_SQL), {"site_id": site_id, "pct": SITE_SIMILARITY_PCT}
        )
    ).scalar()
    rows = (
        await db.execute(
            text(GAP_ROWS_SQL),
            {"site_id": site_id, "owner": OWNER_COVERAGE, "keyword_ids": keyword_ids or None},
        )
    ).all()
    by_cluster: dict[str, list[Any]] = defaultdict(list)
    for r in rows:
        by_cluster[r.cluster_id].append(r)
    drafts: list[NewPageSuggestion] = []
    filtered: dict[str, int] = defaultdict(int)
    for cluster_id, members in by_cluster.items():
        head = members[0]
        if (
            cutoff is not None
            and head.site_similarity is not None
            and head.site_similarity < cutoff
        ):
            filtered["off_topic"] += 1
            continue
        if head.difficulty_median is not None and head.difficulty_median > max_difficulty:
            filtered["too_hard"] += 1
            continue
        competitors = {r.competitor_id for r in members}
        volume = int(head.volume_sum or 0)
        if len(competitors) < 2 and volume < min_volume:
            filtered["thin_evidence"] += 1
            continue
        adjacent = bool(
            (
                await db.execute(
                    text(ADJACENT_SQL),
                    {"site_id": site_id, "cluster_id": cluster_id, "distance": ADJACENT_DISTANCE},
                )
            ).scalar()
        )
        keyword_ids_here = list({r.keyword_id for r in members})
        competitor_rows = sorted(
            {(r.domain, r.position, r.url) for r in members}, key=lambda t: t[1] or 99
        )[:10]
        drafts.append(
            NewPageSuggestion(
                action="add",
                topic_key=head.topic_key,
                cluster_id=cluster_id,
                keyword_ids=keyword_ids_here,
                strategy="gap",
                suggestion=f"Write a page on {head.topic_key}: competitors rank for it and no page of ours covers it.",
                evidence={
                    "volume_sum": volume,
                    "difficulty": head.difficulty_median,
                    "competitors": [
                        {"domain": d, "position": p, "url": u} for d, p, u in competitor_rows
                    ],
                    "adjacent": adjacent,
                    "keywords": [
                        {"keyword": r.keyword, "volume": r.volume}
                        for r in {m.keyword_id: m for m in members}.values()
                    ][:20],
                },
                search_score=_score(volume, head.difficulty_median, len(competitors))
                * (1.5 if adjacent else 1.0),
            )
        )
    result = await suggestions.create_many(db, user_id, site_id, job_id, drafts)
    for reason, count in filtered.items():
        result.filtered[reason] = result.filtered.get(reason, 0) + count
    return result


def _cosine_distance(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return 1 - dot / (na * nb) if na and nb else 1.0


def group_topic_rows(rows: list[Any]) -> dict[str, list[Any]]:
    groups: dict[str, list[Any]] = defaultdict(list)
    loose = []
    for r in rows:
        if r.head:
            groups[r.head].append(r)
        else:
            loose.append(r)
    loose.sort(key=lambda r: -(r.volume or 0))
    heads: list[Any] = []
    for r in loose:
        vector = list(r.embedding) if r.embedding is not None else None
        home = None
        if vector is not None:
            for h in heads:
                hv = list(h.embedding) if h.embedding is not None else None
                if hv is not None and _cosine_distance(vector, hv) <= CLUSTER_ATTACH_DISTANCE:
                    home = h
                    break
        if home is None:
            heads.append(r)
            groups[r.keyword].append(r)
        else:
            groups[home.keyword].append(r)
    return groups


async def propose_topic_pages(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    job_id: str,
    topic: str,
    source_table: str | None,
    ideas_per_seed: int,
    dry_run: bool,
) -> tuple[CreateResult, dict[str, Any]]:
    collected = await collect.collect_keywords(
        db,
        user_id,
        site_id,
        job_id,
        [topic],
        None,
        source_table,
        False,
        False,
        1,
        ideas_per_seed,
        dry_run,
    )
    if dry_run:
        return CreateResult(), collected.model_dump()
    topic_id = (await repo.keyword_ids_for(db, site_id, [topic.strip().lower()])).get(
        topic.strip().lower()
    )
    rows = (
        await db.execute(text(TOPIC_ROWS_SQL), {"site_id": site_id, "topic_id": topic_id})
    ).all()
    drafts: list[NewPageSuggestion] = []
    filtered: dict[str, int] = defaultdict(int)
    for head, members in group_topic_rows(rows).items():
        head_row = max(members, key=lambda r: r.volume or 0)
        covered = (await db.execute(text(COVERED_HEAD_SQL), {"keyword_id": head_row.id})).scalar()
        if covered is not None and covered >= OWNER_COVERAGE:
            filtered["covered"] += 1
            continue
        volume = sum(r.volume or 0 for r in members)
        if volume == 0:
            filtered["no_volume"] += 1
            continue
        drafts.append(
            NewPageSuggestion(
                action="add",
                topic_key=head,
                cluster_id=head_row.cluster_id,
                keyword_ids=[r.id for r in members],
                strategy="topic",
                suggestion=f"Write a page on {head} for the {topic} topic.",
                evidence={
                    "topic": topic,
                    "volume_sum": volume,
                    "difficulty": head_row.difficulty,
                    "keywords": [
                        {"keyword": r.keyword, "volume": r.volume, "difficulty": r.difficulty}
                        for r in members
                    ][:20],
                },
                search_score=volume / ((head_row.difficulty or 50) + 1),
            )
        )
    result = await suggestions.create_many(db, user_id, site_id, job_id, drafts)
    for reason, count in filtered.items():
        result.filtered[reason] = result.filtered.get(reason, 0) + count
    return result, collected.model_dump()
