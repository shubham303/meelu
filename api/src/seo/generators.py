import re
from collections import defaultdict
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.seo import suggestions
from src.seo.constants import (
    IMPRESSIONS_FLOOR,
    LEADER_MIN_DAYS,
    WEAK_COVERAGE,
)
from src.seo.schemas import CreateResult, NewPageSuggestion

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

NARROW = """
  and (cast(:page_ids as text[]) is null or g.page_id = any(cast(:page_ids as text[])))
  and (cast(:keyword_ids as text[]) is null or k.id = any(cast(:keyword_ids as text[])))
"""

GSC_ROWS_SQL = f"""
select g.page_id, k.id as keyword_id, k.keyword, coalesce(hk.keyword, k.keyword) as topic_key,
       k.cluster_id, k.intent, k.volume, k.difficulty, g.position, g.impressions_28d,
       g.clicks_28d, g.impressions_prev_28d, g.clicks_prev_28d, g.clicks_ly_28d,
       g.impressions_ly_28d, g.ctr, g.ctr_gap, g.coverage, g.lexical_hit,
       f.title, f.meta_description, f.title_pixels, f.content_hash, f.page_type,
       f.questions_answered
from seo_keyword_gsc_pages g
join seo_keywords k on k.id = g.keyword_id
left join seo_keyword_clusters c on c.id = k.cluster_id
left join seo_keywords hk on hk.id = c.head_keyword_id
join seo_page_facts f on f.page_id = g.page_id
where g.site_id = :site_id and f.live and f.indexable and not k.branded
{NARROW}
"""

CLUSTER_ROWS_SQL = """
select c.owner_page_id as page_id, hk.keyword as topic_key, c.id as cluster_id,
       k.id as keyword_id, k.keyword, k.volume, k.intent, f.content_hash, f.page_type,
       greatest(coalesce(g.coverage, 0), coalesce(cp.coverage, 0)) as coverage
from seo_keyword_clusters c
join seo_keywords hk on hk.id = c.head_keyword_id
join seo_keywords k on k.cluster_id = c.id and not k.branded and coalesce(k.volume, 0) > 0
join seo_page_facts f on f.page_id = c.owner_page_id and f.live and f.indexable
left join seo_keyword_gsc_pages g on g.keyword_id = k.id and g.page_id = c.owner_page_id
left join seo_keyword_content_pages cp on cp.keyword_id = k.id and cp.page_id = c.owner_page_id
where c.site_id = :site_id and c.owner_page_id is not null
  and (cast(:page_ids as text[]) is null or c.owner_page_id = any(cast(:page_ids as text[])))
  and (cast(:keyword_ids as text[]) is null or k.id = any(cast(:keyword_ids as text[])))
"""

CTR_CUTOFF_SQL = """
select percentile_cont(:pct) within group (order by g.ctr_gap * g.impressions_28d)
from seo_keyword_gsc_pages g
join seo_keywords k on k.id = g.keyword_id
where g.site_id = :site_id and g.ctr_gap > 0 and not k.branded
"""

CANNIBAL_SQL = """
select a.page_id as strong_page, b.page_id as weak_page, k.id as keyword_id, k.keyword,
       coalesce(hk.keyword, k.keyword) as topic_key, k.cluster_id,
       a.impressions_28d + b.impressions_28d as shared_impressions,
       a.leader_days_90d as strong_days, b.leader_days_90d as weak_days,
       a.position as strong_position, b.position as weak_position,
       fa.page_type as strong_type, fb.page_type as weak_type, fa.content_hash
from seo_keyword_gsc_pages a
join seo_keyword_gsc_pages b on b.keyword_id = a.keyword_id and b.page_id <> a.page_id
join seo_keywords k on k.id = a.keyword_id and not k.branded
left join seo_keyword_clusters c on c.id = k.cluster_id
left join seo_keywords hk on hk.id = c.head_keyword_id
join seo_page_facts fa on fa.page_id = a.page_id and fa.live
join seo_page_facts fb on fb.page_id = b.page_id and fb.live
where a.site_id = :site_id
  and a.leader_days_90d >= :min_days and b.leader_days_90d >= :min_days
  and a.impressions_28d + b.impressions_28d >= :min_shared
  and (fa.clicks_28d, fa.inlinks, coalesce(fa.link_score, 0), fa.page_id)
      > (fb.clicks_28d, fb.inlinks, coalesce(fb.link_score, 0), fb.page_id)
  and (cast(:page_ids as text[]) is null or a.page_id = any(cast(:page_ids as text[]))
       or b.page_id = any(cast(:page_ids as text[])))
"""


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
        answered = " ".join(q.lower() for q in (r.questions_answered or []))
        if r.keyword in answered:
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


def _narrow(page_ids: list[str] | None, keyword_ids: list[str] | None) -> dict[str, Any]:
    return {"page_ids": page_ids or None, "keyword_ids": keyword_ids or None}


async def propose_page_edits(
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
    kinds = ("gsc", "cluster", "ctr", "questions", "decay") if evidence == "all" else (evidence,)
    params = {"site_id": site_id, **_narrow(page_ids, keyword_ids)}
    drafts: list[NewPageSuggestion] = []
    gsc_rows = (await db.execute(text(GSC_ROWS_SQL), params)).all() if kinds != ("cluster",) else []
    if "gsc" in kinds:
        drafts += gsc_edits(gsc_rows, min_position, max_position, min_impressions)
    if "cluster" in kinds:
        drafts += cluster_edits((await db.execute(text(CLUSTER_ROWS_SQL), params)).all())
    if "ctr" in kinds:
        cutoff = (
            await db.execute(text(CTR_CUTOFF_SQL), {"site_id": site_id, "pct": CTR_PERCENTILE})
        ).scalar()
        drafts += ctr_edits(gsc_rows, _f(cutoff), min(max_position, 10.0), min_impressions)
    if "questions" in kinds:
        drafts += question_edits(gsc_rows, min_questions)
    if "decay" in kinds:
        drafts += decay_edits(gsc_rows, min_drop)
    return await suggestions.create_many(db, user_id, site_id, job_id, drafts)


async def propose_cannibalisation(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    job_id: str,
    page_ids: list[str] | None,
    min_shared_impressions: int,
) -> CreateResult:
    rows = (
        await db.execute(
            text(CANNIBAL_SQL),
            {
                "site_id": site_id,
                "min_days": LEADER_MIN_DAYS,
                "min_shared": min_shared_impressions,
                "page_ids": page_ids or None,
            },
        )
    ).all()
    return await suggestions.create_many(db, user_id, site_id, job_id, cannibal_pairs(rows))
