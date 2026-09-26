from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.seo.collect import seo_collect_service
from src.seo.constants import (
    ADJACENT_DISTANCE,
    CLUSTER_ATTACH_DISTANCE,
    OWNER_COVERAGE,
    SITE_SIMILARITY_PCT,
)
from src.seo.repositories import (
    seo_competitor_keywords,
    seo_competitors,
    seo_keyword_clusters,
    seo_keyword_content_pages,
    seo_keyword_gsc_pages,
    seo_keywords,
    seo_page_facts,
)
from src.seo.schemas import ClusterRecord, CreateResult, KeywordRecord, NewPageSuggestion
from src.seo.suggestions import seo_suggestion_service

RANKING_NEIGHBOUR_POSITION = 30

COMPETITOR_TOP = 10


@dataclass
class GapRow:
    cluster: ClusterRecord
    topic_key: str
    keyword: KeywordRecord
    competitor_id: str
    domain: str
    position: int | None
    url: str | None


@dataclass
class TopicRow:
    id: str
    keyword: str
    volume: int | None
    difficulty: int | None
    intent: str | None
    cluster_id: str | None
    embedding: list[float] | None
    head: str | None


def _score(volume: int, difficulty: float | None, competitors: int) -> float:
    return volume * (1 + competitors) / ((difficulty or 50) + 1)


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


class SeoGapService:
    async def gap_rows(
        self, db: AsyncSession, site_id: str, keyword_ids: list[str] | None
    ) -> list[GapRow]:
        clusters = {
            c.id: c for c in await seo_keyword_clusters.list_uncovered(db, site_id, OWNER_COVERAGE)
        }
        wanted = set(keyword_ids) if keyword_ids else None
        keywords = {
            k.id: k
            for k in await seo_keywords.list_by_cluster_ids(db, site_id, list(clusters))
            if not k.branded
            and (k.intent or "") != "navigational"
            and (wanted is None or k.id in wanted)
        }
        heads = {
            k.id: k.keyword
            for k in await seo_keywords.list_by_ids(
                db, site_id, [c.head_keyword_id for c in clusters.values()]
            )
        }
        competitors = {c.id: c for c in await seo_competitors.list(db, site_id, "confirmed")}
        rows: list[GapRow] = []
        for ranked in await seo_competitor_keywords.list_by_keyword_ids(
            db, site_id, list(keywords), max_position=COMPETITOR_TOP
        ):
            keyword = keywords[ranked.keyword_id]
            cluster = clusters[keyword.cluster_id or ""]
            competitor = competitors.get(ranked.competitor_id)
            if competitor is None or cluster.head_keyword_id not in heads:
                continue
            rows.append(
                GapRow(
                    cluster=cluster,
                    topic_key=heads[cluster.head_keyword_id],
                    keyword=keyword,
                    competitor_id=competitor.id,
                    domain=competitor.domain,
                    position=ranked.position,
                    url=ranked.url,
                )
            )
        return rows

    async def ranking_neighbours(
        self, db: AsyncSession, site_id: str, cluster_ids: list[str]
    ) -> set[str]:
        neighbours = await seo_keyword_clusters.neighbour_ids(
            db, site_id, cluster_ids, ADJACENT_DISTANCE
        )
        keywords = await seo_keywords.list_by_cluster_ids(
            db, site_id, list({n for found in neighbours.values() for n in found})
        )
        ranking = await seo_keyword_gsc_pages.ranking_keyword_ids(
            db, site_id, [k.id for k in keywords], RANKING_NEIGHBOUR_POSITION
        )
        ranking_clusters = {
            k.cluster_id
            for k in keywords
            if k.id in ranking
            or (k.our_position is not None and k.our_position <= RANKING_NEIGHBOUR_POSITION)
        }
        return {c for c, found in neighbours.items() if found & ranking_clusters}

    async def propose_gap_pages(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        job_id: str,
        keyword_ids: list[str] | None,
        min_volume: int,
        max_difficulty: int,
    ) -> CreateResult:
        cutoff = await seo_keyword_clusters.similarity_cutoff(db, site_id, SITE_SIMILARITY_PCT)
        by_cluster: dict[str, list[GapRow]] = defaultdict(list)
        for r in await self.gap_rows(db, site_id, keyword_ids or None):
            by_cluster[r.cluster.id].append(r)
        filtered: dict[str, int] = defaultdict(int)
        kept: dict[str, list[GapRow]] = {}
        for cluster_id, members in by_cluster.items():
            cluster = members[0].cluster
            if (
                cutoff is not None
                and cluster.site_similarity is not None
                and cluster.site_similarity < cutoff
            ):
                filtered["off_topic"] += 1
                continue
            if cluster.difficulty_median is not None and cluster.difficulty_median > max_difficulty:
                filtered["too_hard"] += 1
                continue
            competitors = {r.competitor_id for r in members}
            if len(competitors) < 2 and int(cluster.volume_sum or 0) < min_volume:
                filtered["thin_evidence"] += 1
                continue
            kept[cluster_id] = members
        adjacent_clusters = await self.ranking_neighbours(db, site_id, list(kept))
        drafts: list[NewPageSuggestion] = []
        for cluster_id, members in kept.items():
            cluster = members[0].cluster
            topic_key = members[0].topic_key
            volume = int(cluster.volume_sum or 0)
            competitors = {r.competitor_id for r in members}
            adjacent = cluster_id in adjacent_clusters
            competitor_rows = sorted(
                {(r.domain, r.position, r.url) for r in members}, key=lambda t: t[1] or 99
            )[:10]
            drafts.append(
                NewPageSuggestion(
                    action="add",
                    topic_key=topic_key,
                    cluster_id=cluster_id,
                    keyword_ids=list({r.keyword.id for r in members}),
                    strategy="gap",
                    suggestion=f"Write a page on {topic_key}: competitors rank for it and no page of ours covers it.",
                    evidence={
                        "volume_sum": volume,
                        "difficulty": cluster.difficulty_median,
                        "competitors": [
                            {"domain": d, "position": p, "url": u} for d, p, u in competitor_rows
                        ],
                        "adjacent": adjacent,
                        "keywords": [
                            {"keyword": r.keyword.keyword, "volume": r.keyword.volume}
                            for r in {m.keyword.id: m for m in members}.values()
                        ][:20],
                    },
                    search_score=_score(volume, cluster.difficulty_median, len(competitors))
                    * (1.5 if adjacent else 1.0),
                )
            )
        result = await seo_suggestion_service.create_many(db, user_id, site_id, job_id, drafts)
        for reason, count in filtered.items():
            result.filtered[reason] = result.filtered.get(reason, 0) + count
        return result

    async def topic_rows(self, db: AsyncSession, site_id: str, topic_id: str) -> list[TopicRow]:
        keywords = await seo_keywords.list_for_topic(db, site_id, topic_id)
        embeddings = await seo_keywords.embeddings_by_ids(db, site_id, [k.id for k in keywords])
        clusters = await seo_keyword_clusters.list_by_ids(
            db, site_id, list({k.cluster_id for k in keywords if k.cluster_id})
        )
        heads = {
            k.id: k.keyword
            for k in await seo_keywords.list_by_ids(
                db, site_id, [c.head_keyword_id for c in clusters]
            )
        }
        head_of = {c.id: heads.get(c.head_keyword_id) for c in clusters}
        return [
            TopicRow(
                id=k.id,
                keyword=k.keyword,
                volume=k.volume,
                difficulty=k.difficulty,
                intent=k.intent,
                cluster_id=k.cluster_id,
                embedding=embeddings.get(k.id),
                head=head_of.get(k.cluster_id) if k.cluster_id else None,
            )
            for k in keywords
        ]

    async def max_live_coverage(
        self, db: AsyncSession, site_id: str, keyword_ids: list[str]
    ) -> dict[str, float]:
        content = await seo_keyword_content_pages.list_for_keywords(db, site_id, keyword_ids)
        live = {
            f.page_id
            for f in await seo_page_facts.list_by_page_ids(
                db, site_id, list({c.page_id for c in content})
            )
            if f.live
        }
        best: dict[str, float] = {}
        for c in content:
            if c.page_id in live:
                best[c.keyword_id] = max(best.get(c.keyword_id, c.coverage), c.coverage)
        return best

    async def propose_topic_pages(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        job_id: str,
        topic: str,
        source_table: str | None,
        ideas_per_seed: int,
        dry_run: bool,
    ) -> tuple[CreateResult, dict[str, Any]]:
        collected = await seo_collect_service.collect_keywords(
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
        topic_id = (await seo_keywords.ids_for(db, site_id, [topic.strip().lower()])).get(
            topic.strip().lower()
        )
        rows = await self.topic_rows(db, site_id, topic_id) if topic_id else []
        groups = {
            head: (max(members, key=lambda r: r.volume or 0), members)
            for head, members in group_topic_rows(rows).items()
        }
        covered = await self.max_live_coverage(
            db, site_id, [head_row.id for head_row, _ in groups.values()]
        )
        drafts: list[NewPageSuggestion] = []
        filtered: dict[str, int] = defaultdict(int)
        for head, (head_row, members) in groups.items():
            coverage = covered.get(head_row.id)
            if coverage is not None and coverage >= OWNER_COVERAGE:
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
        result = await seo_suggestion_service.create_many(db, user_id, site_id, job_id, drafts)
        for reason, count in filtered.items():
            result.filtered[reason] = result.filtered.get(reason, 0) + count
        return result, collected.model_dump()


seo_gap_service = SeoGapService()
