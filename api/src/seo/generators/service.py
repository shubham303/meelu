import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.seo.clusters.repository import seo_keyword_clusters
from src.seo.constants import (
    IMPRESSIONS_FLOOR,
    LEADER_MIN_DAYS,
    WEAK_COVERAGE,
)
from src.seo.generators.schemas import CannibalisationRequest, PageEditsRequest
from src.seo.jobs.service import seo_job_service
from src.seo.keyword_content_pages.repository import seo_keyword_content_pages
from src.seo.keyword_gsc_pages.repository import seo_keyword_gsc_pages
from src.seo.keywords.repository import seo_keywords
from src.seo.keywords.schemas import KeywordRecord
from src.seo.page_facts.repository import seo_page_facts
from src.seo.page_suggestions.schemas import CreateResult, NewPageSuggestion
from src.seo.page_suggestions.service import seo_page_suggestion_service

CTR_PERCENTILE = 0.75

QUESTION_WORDS = (
    "who",
    "what",
    "when",
    "where",
    "why",
    "how",
    "which",
    "can",
    "does",
    "is",
    "are",
    "should",
)

QUESTION_RE = re.compile(r"^(" + "|".join(QUESTION_WORDS) + r")\b")

STRONGER_TYPES = {"money", "hub", "informational", "support"}


@dataclass
class EditRow:
    page_id: str
    keyword_id: str
    keyword: str
    topic_key: str
    cluster_id: str | None
    intent: str | None
    volume: int | None
    difficulty: int | None
    position: float | None
    impressions_28d: int
    clicks_28d: int
    impressions_prev_28d: int
    clicks_prev_28d: int
    clicks_ly_28d: int | None
    impressions_ly_28d: int | None
    ctr: float | None
    ctr_gap: float | None
    coverage: float | None
    lexical_hit: bool
    title: str | None
    meta_description: str | None
    title_pixels: int | None
    content_hash: str | None
    page_type: str | None


@dataclass
class OwnerRow:
    page_id: str
    topic_key: str
    cluster_id: str
    keyword_id: str
    keyword: str
    volume: int | None
    intent: str | None
    content_hash: str | None
    page_type: str | None
    coverage: float


@dataclass
class CannibalRow:
    strong_page: str
    weak_page: str
    keyword_id: str
    keyword: str
    topic_key: str
    cluster_id: str | None
    shared_impressions: int
    strong_days: int
    weak_days: int
    strong_position: float | None
    weak_position: float | None
    strong_type: str | None
    weak_type: str | None
    content_hash: str | None


def percentile_cont(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = fraction * (len(ordered) - 1)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


def strength(page) -> tuple:
    return (page.clicks_28d, page.inlinks, page.link_score or 0, page.page_id)


def _f(value: Any) -> float:
    return float(value) if value is not None else 0.0


def _weak(row: Any) -> bool:
    return _f(row.coverage) < WEAK_COVERAGE and not row.lexical_hit


def _leading_topic(rows: list[Any]) -> str:
    return max(rows, key=lambda r: r.impressions_28d).topic_key


def _keyword_evidence(row: Any) -> dict[str, Any]:
    return {
        "keyword": row.keyword,
        "position": None if row.position is None else round(float(row.position), 1),
        "impressions": row.impressions_28d,
        "coverage": None if row.coverage is None else round(float(row.coverage), 2),
        "volume": row.volume,
    }


def gsc_edits(rows: list[Any], min_position: float, max_position: float, min_impressions: int):
    groups: dict[tuple[str, str], list[Any]] = defaultdict(list)
    for r in rows:
        if r.position is None or not (min_position <= r.position <= max_position):
            continue
        if r.impressions_28d < min_impressions or not _weak(r):
            continue
        groups[(r.page_id, r.topic_key)].append(r)
    out = []
    for (page_id, topic_key), members in groups.items():
        score = sum(r.impressions_28d * (1 - _f(r.coverage)) for r in members)
        out.append(
            NewPageSuggestion(
                action="edit",
                page_id=page_id,
                topic_key=topic_key,
                cluster_id=members[0].cluster_id,
                keyword_ids=[r.keyword_id for r in members],
                strategy="gsc",
                suggestion=f"Cover {topic_key} more fully: the page ranks for it but barely mentions it.",
                evidence={
                    "keywords": [_keyword_evidence(r) for r in members],
                    "content_hash": members[0].content_hash,
                },
                search_score=score,
                target_position=3.0,
            )
        )
    return out


def cluster_edits(rows: list[Any]):
    groups: dict[tuple[str, str], list[Any]] = defaultdict(list)
    for r in rows:
        if _f(r.coverage) < WEAK_COVERAGE:
            groups[(r.page_id, r.topic_key)].append(r)
    out = []
    for (page_id, topic_key), members in groups.items():
        out.append(
            NewPageSuggestion(
                action="edit",
                page_id=page_id,
                topic_key=topic_key,
                cluster_id=members[0].cluster_id,
                keyword_ids=[r.keyword_id for r in members],
                strategy="cluster",
                suggestion=f"Extend the {topic_key} page to its missing subtopics.",
                evidence={
                    "missing": [{"keyword": r.keyword, "volume": r.volume} for r in members],
                    "content_hash": members[0].content_hash,
                },
                search_score=float(sum(r.volume or 0 for r in members)),
            )
        )
    return out


def ctr_edits(rows: list[Any], cutoff: float, max_position: float, min_impressions: int):
    by_page: dict[str, list[Any]] = defaultdict(list)
    for r in rows:
        if r.position is None or r.position > max_position or r.ctr_gap is None:
            continue
        if r.impressions_28d < min_impressions or r.ctr_gap * r.impressions_28d < cutoff:
            continue
        by_page[r.page_id].append(r)
    out = []
    for page_id, members in by_page.items():
        first = members[0]
        out.append(
            NewPageSuggestion(
                action="edit",
                page_id=page_id,
                topic_key=_leading_topic(members),
                cluster_id=first.cluster_id,
                keyword_ids=[r.keyword_id for r in members],
                strategy="ctr",
                suggestion="Rewrite the title and meta description: the page ranks but is not clicked.",
                evidence={
                    "title": first.title,
                    "meta_description": first.meta_description,
                    "title_pixels": first.title_pixels,
                    "queries": [
                        {
                            **_keyword_evidence(r),
                            "ctr": round(_f(r.ctr), 3),
                            "ctr_gap": round(_f(r.ctr_gap), 3),
                        }
                        for r in members
                    ],
                },
                search_score=sum(_f(r.ctr_gap) * r.impressions_28d for r in members),
            )
        )
    return out


def question_edits(rows: list[Any], min_questions: int):
    by_page: dict[str, list[Any]] = defaultdict(list)
    for r in rows:
        if not QUESTION_RE.match(r.keyword) or r.position is None or not (5 <= r.position <= 20):
            continue
        by_page[r.page_id].append(r)
    out = []
    for page_id, members in by_page.items():
        if len(members) < min_questions:
            continue
        out.append(
            NewPageSuggestion(
                action="edit",
                page_id=page_id,
                topic_key=_leading_topic(members),
                cluster_id=members[0].cluster_id,
                keyword_ids=[r.keyword_id for r in members],
                strategy="questions",
                suggestion="Answer the questions searchers ask this page in a FAQ section.",
                evidence={"questions": [r.keyword for r in members]},
                search_score=float(sum(r.impressions_28d for r in members)),
            )
        )
    return out


def decay_edits(rows: list[Any], min_drop: float):
    by_page: dict[str, list[Any]] = defaultdict(list)
    for r in rows:
        by_page[r.page_id].append(r)
    out = []
    for page_id, members in by_page.items():
        clicks = sum(r.clicks_28d for r in members)
        prev = sum(r.clicks_prev_28d for r in members)
        impressions = sum(r.impressions_28d for r in members)
        prev_impressions = sum(r.impressions_prev_28d for r in members)
        if prev == 0 or impressions < IMPRESSIONS_FLOOR or prev_impressions < IMPRESSIONS_FLOOR:
            continue
        drop = (prev - clicks) / prev
        if drop < min_drop:
            continue
        ly = [r.clicks_ly_28d for r in members if r.clicks_ly_28d is not None]
        if ly and sum(ly) > 0 and (sum(ly) - clicks) / sum(ly) < min_drop:
            continue
        losers = sorted(members, key=lambda r: r.clicks_prev_28d - r.clicks_28d, reverse=True)[:10]
        out.append(
            NewPageSuggestion(
                action="edit",
                page_id=page_id,
                topic_key=_leading_topic(members),
                cluster_id=losers[0].cluster_id,
                keyword_ids=[r.keyword_id for r in losers],
                strategy="decay",
                suggestion="Refresh this page: its clicks fell sharply against the previous period.",
                evidence={
                    "clicks": clicks,
                    "clicks_prev": prev,
                    "drop": round(drop, 2),
                    "losing_queries": [
                        {
                            "keyword": r.keyword,
                            "clicks": r.clicks_28d,
                            "clicks_prev": r.clicks_prev_28d,
                        }
                        for r in losers
                    ],
                    "content_hash": losers[0].content_hash,
                },
                search_score=float(prev - clicks),
            )
        )
    return out


def _compatible_pair(a: str | None, b: str | None) -> bool:
    if a is None or b is None:
        return True
    return a == b or {a, b} <= {"informational", "hub", "support"}


def cannibal_pairs(rows: list[Any]):
    by_pair: dict[tuple[str, str], list[Any]] = defaultdict(list)
    for r in rows:
        if _compatible_pair(r.strong_type, r.weak_type):
            by_pair[(r.strong_page, r.weak_page)].append(r)
    out = []
    for (strong, weak), members in by_pair.items():
        lead = max(members, key=lambda r: r.shared_impressions)
        shared = [
            {
                "keyword": r.keyword,
                "impressions": r.shared_impressions,
                "strong_days": r.strong_days,
                "weak_days": r.weak_days,
                "strong_position": None
                if r.strong_position is None
                else round(float(r.strong_position), 1),
                "weak_position": None
                if r.weak_position is None
                else round(float(r.weak_position), 1),
            }
            for r in members
        ]
        index = len(out)
        out.append(
            NewPageSuggestion(
                action="edit",
                page_id=strong,
                topic_key=lead.topic_key,
                cluster_id=lead.cluster_id,
                keyword_ids=[r.keyword_id for r in members],
                strategy="cannibalisation",
                suggestion=f"Absorb the weaker page's angle on {lead.topic_key} into this one.",
                evidence={
                    "absorb_page_id": weak,
                    "shared": shared,
                    "content_hash": lead.content_hash,
                },
                search_score=float(sum(r.shared_impressions for r in members)),
                pair_with=index + 1,
            )
        )
        out.append(
            NewPageSuggestion(
                action="delete",
                page_id=weak,
                topic_key=lead.topic_key,
                cluster_id=lead.cluster_id,
                merge_into_page_id=strong,
                keyword_ids=[r.keyword_id for r in members],
                strategy="cannibalisation",
                suggestion=f"Merge into the stronger page and redirect: both compete for {lead.topic_key}.",
                evidence={"shared": shared},
                search_score=float(sum(r.shared_impressions for r in members)),
            )
        )
    return out


class SeoGeneratorService:
    async def topic_keys(
        self, db: AsyncSession, site_id: str, keywords: list[KeywordRecord]
    ) -> dict[str, str]:
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
        return {
            k.id: (head_of.get(k.cluster_id) if k.cluster_id else None) or k.keyword
            for k in keywords
        }

    async def edit_rows(
        self,
        db: AsyncSession,
        site_id: str,
        page_ids: list[str] | None,
        keyword_ids: list[str] | None,
    ) -> list[EditRow]:
        pairs = await seo_keyword_gsc_pages.list_for_site(db, site_id, page_ids, keyword_ids)
        keywords = {
            k.id: k
            for k in await seo_keywords.list_by_ids(
                db, site_id, list({p.keyword_id for p in pairs})
            )
            if not k.branded
        }
        facts = {
            f.page_id: f
            for f in await seo_page_facts.list_by_page_ids(
                db, site_id, list({p.page_id for p in pairs})
            )
            if f.live and f.indexable
        }
        topics = await self.topic_keys(db, site_id, list(keywords.values()))
        rows: list[EditRow] = []
        for g in pairs:
            k = keywords.get(g.keyword_id)
            f = facts.get(g.page_id)
            if k is None or f is None:
                continue
            rows.append(
                EditRow(
                    page_id=g.page_id,
                    keyword_id=k.id,
                    keyword=k.keyword,
                    topic_key=topics[k.id],
                    cluster_id=k.cluster_id,
                    intent=k.intent,
                    volume=k.volume,
                    difficulty=k.difficulty,
                    position=g.position,
                    impressions_28d=g.impressions_28d,
                    clicks_28d=g.clicks_28d,
                    impressions_prev_28d=g.impressions_prev_28d,
                    clicks_prev_28d=g.clicks_prev_28d,
                    clicks_ly_28d=g.clicks_ly_28d,
                    impressions_ly_28d=g.impressions_ly_28d,
                    ctr=g.ctr,
                    ctr_gap=g.ctr_gap,
                    coverage=g.coverage,
                    lexical_hit=g.lexical_hit,
                    title=f.title,
                    meta_description=f.meta_description,
                    title_pixels=f.title_pixels,
                    content_hash=f.content_hash,
                    page_type=f.page_type,
                )
            )
        return rows

    async def owner_rows(
        self,
        db: AsyncSession,
        site_id: str,
        page_ids: list[str] | None,
        keyword_ids: list[str] | None,
    ) -> list[OwnerRow]:
        clusters = {
            c.id: c
            for c in await seo_keyword_clusters.list_owned(db, site_id)
            if page_ids is None or c.owner_page_id in page_ids
        }
        heads = {
            k.id: k.keyword
            for k in await seo_keywords.list_by_ids(
                db, site_id, [c.head_keyword_id for c in clusters.values()]
            )
        }
        facts = {
            f.page_id: f
            for f in await seo_page_facts.list_by_page_ids(
                db, site_id, list({c.owner_page_id for c in clusters.values() if c.owner_page_id})
            )
            if f.live and f.indexable
        }
        keywords = [
            k
            for k in await seo_keywords.list_by_cluster_ids(db, site_id, list(clusters))
            if not k.branded
            and (k.volume or 0) > 0
            and (keyword_ids is None or k.id in keyword_ids)
        ]
        ids = [k.id for k in keywords]
        gsc = {
            (g.keyword_id, g.page_id): g.coverage
            for g in await seo_keyword_gsc_pages.list_for_keywords(db, site_id, ids)
        }
        content = {
            (c.keyword_id, c.page_id): c.coverage
            for c in await seo_keyword_content_pages.list_for_keywords(db, site_id, ids)
        }
        rows: list[OwnerRow] = []
        for k in keywords:
            cluster = clusters[k.cluster_id or ""]
            page = facts.get(cluster.owner_page_id or "")
            if page is None or cluster.head_keyword_id not in heads:
                continue
            pair = (k.id, page.page_id)
            rows.append(
                OwnerRow(
                    page_id=page.page_id,
                    topic_key=heads[cluster.head_keyword_id],
                    cluster_id=cluster.id,
                    keyword_id=k.id,
                    keyword=k.keyword,
                    volume=k.volume,
                    intent=k.intent,
                    content_hash=page.content_hash,
                    page_type=page.page_type,
                    coverage=max(gsc.get(pair) or 0.0, content.get(pair) or 0.0),
                )
            )
        return rows

    async def ctr_gap_cutoff(self, db: AsyncSession, site_id: str, fraction: float) -> float | None:
        branded = await seo_keywords.branded_ids(db, site_id)
        values = [
            v
            for keyword_id, v in await seo_keyword_gsc_pages.ctr_gap_values(db, site_id)
            if keyword_id not in branded
        ]
        return percentile_cont(values, fraction)

    async def cannibal_rows(
        self,
        db: AsyncSession,
        site_id: str,
        min_days: int,
        min_shared: int,
        page_ids: list[str] | None,
    ) -> list[CannibalRow]:
        leaders = await seo_keyword_gsc_pages.list_leaders(db, site_id, min_days)
        keywords = {
            k.id: k
            for k in await seo_keywords.list_by_ids(
                db, site_id, list({g.keyword_id for g in leaders})
            )
            if not k.branded
        }
        facts = {
            f.page_id: f
            for f in await seo_page_facts.list_by_page_ids(
                db, site_id, list({g.page_id for g in leaders})
            )
            if f.live
        }
        topics = await self.topic_keys(db, site_id, list(keywords.values()))
        by_keyword: dict[str, list] = defaultdict(list)
        for g in leaders:
            if g.keyword_id in keywords and g.page_id in facts:
                by_keyword[g.keyword_id].append(g)
        wanted = set(page_ids) if page_ids else None
        rows: list[CannibalRow] = []
        for keyword_id, members in by_keyword.items():
            k = keywords[keyword_id]
            for a in members:
                for b in members:
                    if a.page_id == b.page_id:
                        continue
                    fa, fb = facts[a.page_id], facts[b.page_id]
                    shared = a.impressions_28d + b.impressions_28d
                    if shared < min_shared or strength(fa) <= strength(fb):
                        continue
                    if wanted is not None and a.page_id not in wanted and b.page_id not in wanted:
                        continue
                    rows.append(
                        CannibalRow(
                            strong_page=a.page_id,
                            weak_page=b.page_id,
                            keyword_id=k.id,
                            keyword=k.keyword,
                            topic_key=topics[k.id],
                            cluster_id=k.cluster_id,
                            shared_impressions=shared,
                            strong_days=a.leader_days_90d,
                            weak_days=b.leader_days_90d,
                            strong_position=a.position,
                            weak_position=b.position,
                            strong_type=fa.page_type,
                            weak_type=fb.page_type,
                            content_hash=fa.content_hash,
                        )
                    )
        return rows

    async def _propose_page_edits(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        job_id: str,
        evidence: str,
        page_ids: list[str] | None,
        keyword_ids: list[str] | None,
        min_position: float,
        max_position: float,
        min_impressions: int,
        min_questions: int,
        min_drop: float,
    ) -> CreateResult:
        kinds = (
            ("gsc", "cluster", "ctr", "questions", "decay") if evidence == "all" else (evidence,)
        )
        page_ids = page_ids or None
        keyword_ids = keyword_ids or None
        drafts: list[NewPageSuggestion] = []
        gsc_rows = (
            await self.edit_rows(db, site_id, page_ids, keyword_ids)
            if kinds != ("cluster",)
            else []
        )
        if "gsc" in kinds:
            drafts += gsc_edits(gsc_rows, min_position, max_position, min_impressions)
        if "cluster" in kinds:
            drafts += cluster_edits(await self.owner_rows(db, site_id, page_ids, keyword_ids))
        if "ctr" in kinds:
            cutoff = await self.ctr_gap_cutoff(db, site_id, CTR_PERCENTILE)
            drafts += ctr_edits(gsc_rows, _f(cutoff), min(max_position, 10.0), min_impressions)
        if "questions" in kinds:
            drafts += question_edits(gsc_rows, min_questions)
        if "decay" in kinds:
            drafts += decay_edits(gsc_rows, min_drop)
        return await seo_page_suggestion_service.create_many(db, user_id, site_id, job_id, drafts)

    async def _propose_cannibalisation(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        job_id: str,
        page_ids: list[str] | None,
        min_shared_impressions: int,
    ) -> CreateResult:
        rows = await self.cannibal_rows(
            db, site_id, LEADER_MIN_DAYS, min_shared_impressions, page_ids or None
        )
        return await seo_page_suggestion_service.create_many(
            db, user_id, site_id, job_id, cannibal_pairs(rows)
        )

    async def propose_page_edits(
        self, db: AsyncSession, user_id: str, site_id: str, body: PageEditsRequest
    ) -> CreateResult:
        await seo_job_service.get(db, site_id, body.job_id)
        return await self._propose_page_edits(
            db,
            user_id,
            site_id,
            body.job_id,
            body.evidence,
            body.page_ids,
            body.keyword_ids,
            body.min_position,
            body.max_position,
            body.min_impressions,
            body.min_questions,
            body.min_drop,
        )

    async def propose_cannibalisation(
        self, db: AsyncSession, user_id: str, site_id: str, body: CannibalisationRequest
    ) -> CreateResult:
        await seo_job_service.get(db, site_id, body.job_id)
        return await self._propose_cannibalisation(
            db, user_id, site_id, body.job_id, body.page_ids, body.min_shared_impressions
        )


seo_generator_service = SeoGeneratorService()
