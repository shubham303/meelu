from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.seo.models.competitor import SeoCompetitor
from src.seo.models.job import SeoJob
from src.seo.models.keyword import SeoKeyword, SeoKeywordCluster
from src.seo.models.keyword_pages import SeoKeywordContentPage, SeoKeywordGscPage
from src.seo.models.page_facts import SeoPageFacts
from src.seo.models.page_suggestion import SeoPageSuggestion, SeoPageSuggestionKeyword
from src.seo.models.site_state import SeoSiteState
from src.seo.schemas import (
    ClusterRecord,
    CompetitorRecord,
    KeywordContentPageRecord,
    KeywordFilter,
    KeywordGscPageRecord,
    KeywordRecord,
    PageFactsRecord,
    PageSuggestionFilter,
    PageSuggestionRecord,
    PageSuggestionSummary,
    SeoJobRecord,
    SiteStateRecord,
)


def _now() -> datetime:
    return datetime.now(UTC)


async def _count(db: AsyncSession, query: Select) -> int:
    return int((await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0)


async def _page(db, query: Select, order, paging: PaginationParams, record):
    clauses = order if isinstance(order, tuple) else (order,)
    rows = (
        await db.execute(query.order_by(*clauses).offset(paging.offset).limit(paging.page_size))
    ).scalars()
    total = await _count(db, query)
    return PaginatedApiResponse[record](
        data=[record.model_validate(r) for r in rows],
        pagination=PaginationService.build_pagination_meta(total, paging.page, paging.page_size),
    )


async def get_state(db: AsyncSession, site_id: str) -> SiteStateRecord | None:
    row = (
        await db.execute(select(SeoSiteState).where(SeoSiteState.site_id == site_id))
    ).scalar_one_or_none()
    return None if row is None else SiteStateRecord.model_validate(row)


async def ensure_state(db: AsyncSession, user_id: str, site_id: str) -> SiteStateRecord:
    now = _now()
    stmt = (
        insert(SeoSiteState)
        .values(id=uid("sst"), user_id=user_id, site_id=site_id, created_at=now, updated_at=now)
        .on_conflict_do_nothing(index_elements=["site_id"])
    )
    await db.execute(stmt)
    await db.flush()
    found = await get_state(db, site_id)
    assert found is not None
    return found


async def patch_state(db: AsyncSession, site_id: str, patch: dict[str, Any]) -> SiteStateRecord:
    await db.execute(
        update(SeoSiteState)
        .where(SeoSiteState.site_id == site_id)
        .values(**patch, updated_at=_now())
    )
    await db.flush()
    found = await get_state(db, site_id)
    assert found is not None
    return found


async def create_job(
    db: AsyncSession, user_id: str, site_id: str, prompt: str, ceiling: int
) -> SeoJobRecord:
    now = _now()
    row = SeoJob(
        id=uid("sjob"),
        user_id=user_id,
        site_id=site_id,
        prompt=prompt,
        status="RUNNING",
        vendor_ceiling_micros=ceiling,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.flush()
    return SeoJobRecord.model_validate(row)


async def fail_running_jobs(db: AsyncSession, site_id: str) -> int:
    result = await db.execute(
        update(SeoJob)
        .where(SeoJob.site_id == site_id, SeoJob.status == "RUNNING")
        .values(status="FAILED", updated_at=_now())
    )
    return result.rowcount or 0


async def get_job(db: AsyncSession, site_id: str, job_id: str) -> SeoJobRecord | None:
    row = (
        await db.execute(select(SeoJob).where(SeoJob.site_id == site_id, SeoJob.id == job_id))
    ).scalar_one_or_none()
    return None if row is None else SeoJobRecord.model_validate(row)


async def list_jobs(
    db: AsyncSession, site_id: str, paging: PaginationParams
) -> PaginatedApiResponse[SeoJobRecord]:
    query = select(SeoJob).where(SeoJob.site_id == site_id)
    return await _page(db, query, SeoJob.seq.desc(), paging, SeoJobRecord)


async def update_job_status(
    db: AsyncSession, site_id: str, job_id: str, status: str
) -> SeoJobRecord | None:
    await db.execute(
        update(SeoJob)
        .where(SeoJob.site_id == site_id, SeoJob.id == job_id)
        .values(status=status, updated_at=_now())
    )
    return await get_job(db, site_id, job_id)


async def add_spend(db: AsyncSession, job_id: str, calls: int, micros: int) -> None:
    await db.execute(
        update(SeoJob)
        .where(SeoJob.id == job_id)
        .values(
            vendor_calls=SeoJob.vendor_calls + calls,
            vendor_micros=SeoJob.vendor_micros + micros,
            updated_at=_now(),
        )
    )


async def list_page_facts(
    db: AsyncSession, site_id: str, paging: PaginationParams, live: bool | None
) -> PaginatedApiResponse[PageFactsRecord]:
    query = select(SeoPageFacts).where(SeoPageFacts.site_id == site_id)
    if live is not None:
        query = query.where(SeoPageFacts.live == live)
    return await _page(db, query, SeoPageFacts.url, paging, PageFactsRecord)


async def get_page_facts(db: AsyncSession, site_id: str, page_id: str) -> PageFactsRecord | None:
    row = (
        await db.execute(
            select(SeoPageFacts).where(
                SeoPageFacts.site_id == site_id, SeoPageFacts.page_id == page_id
            )
        )
    ).scalar_one_or_none()
    return None if row is None else PageFactsRecord.model_validate(row)


def _keyword_query(site_id: str, f: KeywordFilter) -> Select:
    query = select(SeoKeyword).where(SeoKeyword.site_id == site_id)
    if f.source:
        query = query.where(SeoKeyword.first_source == f.source)
    if f.cluster_id:
        query = query.where(SeoKeyword.cluster_id == f.cluster_id)
    if f.branded is not None:
        query = query.where(SeoKeyword.branded == f.branded)
    if f.has_facts is not None:
        query = query.where(
            SeoKeyword.facts_fetched_at.is_not(None)
            if f.has_facts
            else SeoKeyword.facts_fetched_at.is_(None)
        )
    if f.search:
        query = query.where(SeoKeyword.keyword.ilike(f"%{f.search}%"))
    return query


async def list_keywords(
    db: AsyncSession, site_id: str, f: KeywordFilter, paging: PaginationParams
) -> PaginatedApiResponse[KeywordRecord]:
    return await _page(
        db,
        _keyword_query(site_id, f),
        (SeoKeyword.impressions_28d.desc(), SeoKeyword.volume.desc().nulls_last(), SeoKeyword.seq),
        paging,
        KeywordRecord,
    )


async def get_keyword(db: AsyncSession, site_id: str, keyword_id: str) -> KeywordRecord | None:
    row = (
        await db.execute(
            select(SeoKeyword).where(SeoKeyword.site_id == site_id, SeoKeyword.id == keyword_id)
        )
    ).scalar_one_or_none()
    return None if row is None else KeywordRecord.model_validate(row)


async def find_keyword(db: AsyncSession, site_id: str, keyword: str) -> KeywordRecord | None:
    row = (
        await db.execute(
            select(SeoKeyword).where(SeoKeyword.site_id == site_id, SeoKeyword.keyword == keyword)
        )
    ).scalar_one_or_none()
    return None if row is None else KeywordRecord.model_validate(row)


async def insert_keywords(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    keywords: list[str],
    source: str,
    seed_keyword_id: str | None = None,
) -> list[str]:
    if not keywords:
        return []
    now = _now()
    stmt = (
        insert(SeoKeyword)
        .values(
            [
                {
                    "id": uid("kw"),
                    "user_id": user_id,
                    "site_id": site_id,
                    "keyword": k,
                    "first_source": source,
                    "seed_keyword_id": seed_keyword_id,
                    "created_at": now,
                    "updated_at": now,
                }
                for k in keywords
            ]
        )
        .on_conflict_do_nothing(index_elements=["site_id", "keyword"])
        .returning(SeoKeyword.id)
    )
    return list((await db.execute(stmt)).scalars().all())


async def keyword_ids_for(db: AsyncSession, site_id: str, keywords: list[str]) -> dict[str, str]:
    if not keywords:
        return {}
    rows = await db.execute(
        select(SeoKeyword.keyword, SeoKeyword.id).where(
            SeoKeyword.site_id == site_id, SeoKeyword.keyword.in_(keywords)
        )
    )
    return {k: i for k, i in rows.tuples()}


async def keyword_gsc_pages(
    db: AsyncSession, site_id: str, keyword_id: str
) -> list[KeywordGscPageRecord]:
    rows = (
        await db.execute(
            select(SeoKeywordGscPage)
            .where(SeoKeywordGscPage.site_id == site_id, SeoKeywordGscPage.keyword_id == keyword_id)
            .order_by(SeoKeywordGscPage.impressions_28d.desc())
        )
    ).scalars()
    return [KeywordGscPageRecord.model_validate(r) for r in rows]


async def keyword_content_pages(
    db: AsyncSession, site_id: str, keyword_id: str
) -> list[KeywordContentPageRecord]:
    rows = (
        await db.execute(
            select(SeoKeywordContentPage)
            .where(
                SeoKeywordContentPage.site_id == site_id,
                SeoKeywordContentPage.keyword_id == keyword_id,
            )
            .order_by(SeoKeywordContentPage.coverage.desc())
        )
    ).scalars()
    return [KeywordContentPageRecord.model_validate(r) for r in rows]


async def page_gsc_keywords(
    db: AsyncSession, site_id: str, page_id: str, paging: PaginationParams
) -> PaginatedApiResponse[KeywordGscPageRecord]:
    query = select(SeoKeywordGscPage).where(
        SeoKeywordGscPage.site_id == site_id, SeoKeywordGscPage.page_id == page_id
    )
    return await _page(
        db, query, SeoKeywordGscPage.impressions_28d.desc(), paging, KeywordGscPageRecord
    )


async def list_clusters(
    db: AsyncSession, site_id: str, paging: PaginationParams
) -> PaginatedApiResponse[ClusterRecord]:
    query = select(SeoKeywordCluster).where(SeoKeywordCluster.site_id == site_id)
    return await _page(db, query, SeoKeywordCluster.volume_sum.desc(), paging, ClusterRecord)


async def list_competitors(
    db: AsyncSession, site_id: str, state: str | None
) -> list[CompetitorRecord]:
    query = select(SeoCompetitor).where(SeoCompetitor.site_id == site_id)
    if state:
        query = query.where(SeoCompetitor.state == state)
    rows = (
        await db.execute(query.order_by(SeoCompetitor.intersections.desc().nulls_last()))
    ).scalars()
    return [CompetitorRecord.model_validate(r) for r in rows]


async def get_competitor(
    db: AsyncSession, site_id: str, competitor_id: str
) -> CompetitorRecord | None:
    row = (
        await db.execute(
            select(SeoCompetitor).where(
                SeoCompetitor.site_id == site_id, SeoCompetitor.id == competitor_id
            )
        )
    ).scalar_one_or_none()
    return None if row is None else CompetitorRecord.model_validate(row)


async def patch_competitor(
    db: AsyncSession, site_id: str, competitor_id: str, patch: dict[str, Any]
) -> CompetitorRecord | None:
    await db.execute(
        update(SeoCompetitor)
        .where(SeoCompetitor.site_id == site_id, SeoCompetitor.id == competitor_id)
        .values(**patch, updated_at=_now())
    )
    return await get_competitor(db, site_id, competitor_id)


async def upsert_competitor(
    db: AsyncSession, user_id: str, site_id: str, values: dict[str, Any]
) -> CompetitorRecord:
    now = _now()
    stmt = (
        insert(SeoCompetitor)
        .values(
            id=uid("cmp"),
            user_id=user_id,
            site_id=site_id,
            created_at=now,
            updated_at=now,
            **values,
        )
        .on_conflict_do_update(
            index_elements=["site_id", "domain"],
            set_={
                "intersections": values.get("intersections"),
                "avg_position": values.get("avg_position"),
                "fetched_at": values.get("fetched_at"),
                "updated_at": now,
            },
        )
        .returning(SeoCompetitor)
    )
    row = (await db.execute(stmt)).scalar_one()
    return CompetitorRecord.model_validate(row)


def _suggestion_query(site_id: str, f: PageSuggestionFilter) -> Select:
    query = select(SeoPageSuggestion).where(SeoPageSuggestion.site_id == site_id)
    if f.state:
        query = query.where(SeoPageSuggestion.state == f.state)
    if f.action:
        query = query.where(SeoPageSuggestion.action == f.action)
    if f.job_id:
        query = query.where(SeoPageSuggestion.job_id == f.job_id)
    if f.page_id:
        query = query.where(
            (SeoPageSuggestion.page_id == f.page_id)
            | (SeoPageSuggestion.merge_into_page_id == f.page_id)
        )
    if f.topic_key:
        query = query.where(SeoPageSuggestion.topic_key == f.topic_key)
    return query


async def list_suggestions(
    db: AsyncSession, site_id: str, f: PageSuggestionFilter, paging: PaginationParams
) -> PaginatedApiResponse[PageSuggestionRecord]:
    return await _page(
        db,
        _suggestion_query(site_id, f),
        (SeoPageSuggestion.score.desc().nulls_last(), SeoPageSuggestion.seq.desc()),
        paging,
        PageSuggestionRecord,
    )


async def get_suggestion(
    db: AsyncSession, site_id: str, suggestion_id: str
) -> PageSuggestionRecord | None:
    row = (
        await db.execute(
            select(SeoPageSuggestion).where(
                SeoPageSuggestion.site_id == site_id, SeoPageSuggestion.id == suggestion_id
            )
        )
    ).scalar_one_or_none()
    return None if row is None else PageSuggestionRecord.model_validate(row)


async def set_suggestion_state(
    db: AsyncSession, site_id: str, ids: list[str], state: str, only_from: tuple[str, ...]
) -> int:
    if not ids:
        return 0
    result = await db.execute(
        update(SeoPageSuggestion)
        .where(
            SeoPageSuggestion.site_id == site_id,
            SeoPageSuggestion.id.in_(ids),
            SeoPageSuggestion.state.in_(only_from),
        )
        .values(state=state, updated_at=_now())
    )
    return result.rowcount or 0


async def pair_of(db: AsyncSession, site_id: str, suggestion_id: str) -> list[str]:
    rows = await db.execute(
        select(SeoPageSuggestion.id).where(
            SeoPageSuggestion.site_id == site_id,
            (SeoPageSuggestion.id == suggestion_id) | (SeoPageSuggestion.pair_id == suggestion_id),
        )
    )
    ids = set(rows.scalars().all())
    found = await get_suggestion(db, site_id, suggestion_id)
    if found is not None and found.pair_id:
        ids.add(found.pair_id)
    return list(ids)


async def suggestion_summary(db: AsyncSession, site_id: str) -> PageSuggestionSummary:
    rows = await db.execute(
        select(SeoPageSuggestion.action, SeoPageSuggestion.state, func.count())
        .where(SeoPageSuggestion.site_id == site_id)
        .group_by(SeoPageSuggestion.action, SeoPageSuggestion.state)
    )
    summary = PageSuggestionSummary()
    for action, state, count in rows.tuples():
        getattr(summary, action)[state] = int(count)
    return summary


async def counts(db: AsyncSession, site_id: str) -> dict[str, int]:
    keywords = await _count(db, select(SeoKeyword).where(SeoKeyword.site_id == site_id))
    with_facts = await _count(
        db,
        select(SeoKeyword).where(
            SeoKeyword.site_id == site_id, SeoKeyword.facts_fetched_at.is_not(None)
        ),
    )
    clusters = await _count(
        db, select(SeoKeywordCluster).where(SeoKeywordCluster.site_id == site_id)
    )
    confirmed = await _count(
        db,
        select(SeoCompetitor).where(
            SeoCompetitor.site_id == site_id, SeoCompetitor.state == "confirmed"
        ),
    )
    return {
        "keywords": keywords,
        "keywords_with_facts": with_facts,
        "clusters": clusters,
        "competitors_confirmed": confirmed,
    }


async def find_suggestion(
    db: AsyncSession, site_id: str, action: str, page_id: str | None, topic_key: str
) -> PageSuggestionRecord | None:
    query = select(SeoPageSuggestion).where(
        SeoPageSuggestion.site_id == site_id,
        SeoPageSuggestion.action == action,
        SeoPageSuggestion.topic_key == topic_key,
        SeoPageSuggestion.page_id.is_(None)
        if page_id is None
        else SeoPageSuggestion.page_id == page_id,
    )
    row = (await db.execute(query)).scalar_one_or_none()
    return None if row is None else PageSuggestionRecord.model_validate(row)


async def insert_suggestion(
    db: AsyncSession, user_id: str, site_id: str, job_id: str, values: dict[str, Any]
) -> str:
    now = _now()
    row = SeoPageSuggestion(
        id=uid("psg"),
        user_id=user_id,
        site_id=site_id,
        job_id=job_id,
        created_at=now,
        updated_at=now,
        **values,
    )
    db.add(row)
    await db.flush()
    return row.id


async def revive_suggestion(
    db: AsyncSession, site_id: str, suggestion_id: str, job_id: str, values: dict[str, Any]
) -> None:
    await db.execute(
        update(SeoPageSuggestion)
        .where(SeoPageSuggestion.site_id == site_id, SeoPageSuggestion.id == suggestion_id)
        .values(
            **{**values, "state": "draft"},
            job_id=job_id,
            confidence=None,
            score=None,
            pair_id=None,
            verified_at=None,
            updated_at=_now(),
        )
    )


async def touch_suggestion(
    db: AsyncSession, site_id: str, suggestion_id: str, strategy: str, evidence: dict[str, Any]
) -> None:
    await db.execute(
        update(SeoPageSuggestion)
        .where(SeoPageSuggestion.site_id == site_id, SeoPageSuggestion.id == suggestion_id)
        .values(
            strategies=func.array_append(
                func.array_remove(SeoPageSuggestion.strategies, strategy), strategy
            ),
            evidence=evidence,
            updated_at=_now(),
        )
    )


async def link_pair(db: AsyncSession, site_id: str, first_id: str, second_id: str) -> None:
    await db.execute(
        update(SeoPageSuggestion)
        .where(SeoPageSuggestion.site_id == site_id, SeoPageSuggestion.id == first_id)
        .values(pair_id=second_id)
    )
    await db.execute(
        update(SeoPageSuggestion)
        .where(SeoPageSuggestion.site_id == site_id, SeoPageSuggestion.id == second_id)
        .values(pair_id=first_id)
    )


async def replace_suggestion_keywords(
    db: AsyncSession, suggestion_id: str, keyword_ids: list[str]
) -> None:
    await db.execute(
        delete(SeoPageSuggestionKeyword).where(
            SeoPageSuggestionKeyword.suggestion_id == suggestion_id
        )
    )
    if keyword_ids:
        await db.execute(
            insert(SeoPageSuggestionKeyword)
            .values([{"suggestion_id": suggestion_id, "keyword_id": k} for k in set(keyword_ids)])
            .on_conflict_do_nothing()
        )


async def suggestion_keyword_ids(db: AsyncSession, suggestion_id: str) -> list[str]:
    rows = await db.execute(
        select(SeoPageSuggestionKeyword.keyword_id).where(
            SeoPageSuggestionKeyword.suggestion_id == suggestion_id
        )
    )
    return list(rows.scalars().all())


async def cluster_by_head(db: AsyncSession, site_id: str, topic_key: str) -> ClusterRecord | None:
    row = (
        await db.execute(
            select(SeoKeywordCluster)
            .join(SeoKeyword, SeoKeyword.id == SeoKeywordCluster.head_keyword_id)
            .where(SeoKeywordCluster.site_id == site_id, SeoKeyword.keyword == topic_key)
        )
    ).scalar_one_or_none()
    return None if row is None else ClusterRecord.model_validate(row)


async def page_coverage(
    db: AsyncSession, site_id: str, keyword_id: str, page_id: str
) -> float | None:
    gsc = (
        await db.execute(
            select(SeoKeywordGscPage.coverage).where(
                SeoKeywordGscPage.site_id == site_id,
                SeoKeywordGscPage.keyword_id == keyword_id,
                SeoKeywordGscPage.page_id == page_id,
            )
        )
    ).scalar_one_or_none()
    if gsc is not None:
        return float(gsc)
    content = (
        await db.execute(
            select(SeoKeywordContentPage.coverage).where(
                SeoKeywordContentPage.site_id == site_id,
                SeoKeywordContentPage.keyword_id == keyword_id,
                SeoKeywordContentPage.page_id == page_id,
            )
        )
    ).scalar_one_or_none()
    return None if content is None else float(content)


async def inlinks_median(db: AsyncSession, site_id: str) -> float:
    value = (
        await db.execute(
            select(func.percentile_cont(0.5).within_group(SeoPageFacts.inlinks)).where(
                SeoPageFacts.site_id == site_id, SeoPageFacts.live
            )
        )
    ).scalar()
    return float(value or 0)


async def open_suggestions(db: AsyncSession, site_id: str) -> list[PageSuggestionRecord]:
    rows = (
        await db.execute(
            select(SeoPageSuggestion).where(
                SeoPageSuggestion.site_id == site_id,
                SeoPageSuggestion.state.in_(("draft", "reviewed", "ready")),
            )
        )
    ).scalars()
    return [PageSuggestionRecord.model_validate(r) for r in rows]


async def close_suggestions(db: AsyncSession, site_id: str, ids: list[str], state: str) -> int:
    if not ids:
        return 0
    result = await db.execute(
        update(SeoPageSuggestion)
        .where(
            SeoPageSuggestion.site_id == site_id,
            SeoPageSuggestion.id.in_(ids),
            SeoPageSuggestion.state.in_(("draft", "reviewed", "ready")),
        )
        .values(state=state, verified_at=_now(), updated_at=_now())
    )
    return result.rowcount or 0


async def job_rows(
    db: AsyncSession,
    site_id: str,
    job_id: str,
    ids: list[str] | None,
    states: tuple[str, ...],
    limit: int,
) -> list[PageSuggestionRecord]:
    query = select(SeoPageSuggestion).where(
        SeoPageSuggestion.site_id == site_id,
        SeoPageSuggestion.job_id == job_id,
        SeoPageSuggestion.state.in_(states),
    )
    if ids:
        query = query.where(SeoPageSuggestion.id.in_(ids))
    rows = (
        await db.execute(
            query.order_by(SeoPageSuggestion.search_score.desc().nulls_last()).limit(limit)
        )
    ).scalars()
    return [PageSuggestionRecord.model_validate(r) for r in rows]


async def update_suggestion(
    db: AsyncSession, site_id: str, suggestion_id: str, patch: dict[str, Any]
) -> None:
    await db.execute(
        update(SeoPageSuggestion)
        .where(SeoPageSuggestion.site_id == site_id, SeoPageSuggestion.id == suggestion_id)
        .values(**patch, updated_at=_now())
    )


async def keyword_facts_for(
    db: AsyncSession, site_id: str, keyword_ids: list[str]
) -> list[dict[str, Any]]:
    if not keyword_ids:
        return []
    rows = await db.execute(
        select(SeoKeyword).where(SeoKeyword.site_id == site_id, SeoKeyword.id.in_(keyword_ids))
    )
    return [
        {
            "keyword": k.keyword,
            "volume": k.volume,
            "difficulty": k.difficulty,
            "intent": k.intent,
            "impressions_28d": k.impressions_28d,
            "clicks_28d": k.clicks_28d,
        }
        for k in rows.scalars()
    ]


async def latest_serp(
    db: AsyncSession, site_id: str, keyword_id: str, top: int = 3
) -> dict[str, Any] | None:
    from src.seo.models.serp import SeoSerpResult, SeoSerpSnapshot

    snapshot = (
        await db.execute(
            select(SeoSerpSnapshot)
            .where(SeoSerpSnapshot.site_id == site_id, SeoSerpSnapshot.keyword_id == keyword_id)
            .order_by(SeoSerpSnapshot.fetched_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if snapshot is None:
        return None
    results = (
        await db.execute(
            select(SeoSerpResult)
            .where(SeoSerpResult.snapshot_id == snapshot.id)
            .order_by(SeoSerpResult.rank)
            .limit(top)
        )
    ).scalars()
    return {
        "features": list(snapshot.features),
        "results": [
            {
                "rank": r.rank,
                "domain": r.domain,
                "title": r.title,
                "description": r.description,
                "ours": r.is_ours,
            }
            for r in results
        ],
    }


async def page_brief(db: AsyncSession, site_id: str, page_id: str | None) -> dict[str, Any] | None:
    if page_id is None:
        return None
    page = await get_page_facts(db, site_id, page_id)
    if page is None:
        return None
    return {
        "url": page.url,
        "title": page.title,
        "h1": page.h1,
        "headings": list(page.headings)[:30],
        "meta_description": page.meta_description,
        "page_type": page.page_type,
        "word_count": page.word_count,
        "inlinks": page.inlinks,
        "impressions_28d": page.impressions_28d,
        "clicks_28d": page.clicks_28d,
        "questions_answered": list(page.questions_answered)[:20],
    }


async def nearest_page(db: AsyncSession, site_id: str, keyword_id: str) -> dict[str, Any] | None:
    for candidate in await keyword_content_pages(db, site_id, keyword_id):
        page = await get_page_facts(db, site_id, candidate.page_id)
        if page is not None and page.live:
            return {"url": page.url, "title": page.title, "coverage": round(candidate.coverage, 2)}
    return None


async def paa_questions(db: AsyncSession, site_id: str, keyword_id: str) -> list[str]:
    rows = await db.execute(
        select(SeoKeyword.keyword).where(
            SeoKeyword.site_id == site_id,
            SeoKeyword.seed_keyword_id == keyword_id,
            SeoKeyword.first_source == "serp_paa",
        )
    )
    return list(rows.scalars().all())[:10]


async def site_domain(db: AsyncSession, site_id: str) -> str | None:
    from src.sites.models.site import Site

    return (await db.execute(select(Site.domain).where(Site.id == site_id))).scalar_one_or_none()


async def competitor_keywords_fetched_at(db: AsyncSession, competitor_id: str) -> datetime | None:
    from src.seo.models.competitor import SeoCompetitorKeyword

    return (
        await db.execute(
            select(func.max(SeoCompetitorKeyword.fetched_at)).where(
                SeoCompetitorKeyword.competitor_id == competitor_id
            )
        )
    ).scalar()


async def insert_serp_snapshot(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    keyword_id: str,
    device: str,
    fetched_at: datetime,
    features: list[str],
    results: list[dict[str, Any]],
) -> str:
    from src.seo.models.serp import SeoSerpResult, SeoSerpSnapshot

    snapshot = SeoSerpSnapshot(
        id=uid("snap"),
        user_id=user_id,
        site_id=site_id,
        keyword_id=keyword_id,
        device=device,
        fetched_at=fetched_at,
        features=features,
        created_at=fetched_at,
        updated_at=fetched_at,
    )
    db.add(snapshot)
    await db.flush()
    for r in results:
        db.add(
            SeoSerpResult(
                user_id=user_id,
                site_id=site_id,
                snapshot_id=snapshot.id,
                created_at=fetched_at,
                updated_at=fetched_at,
                **r,
            )
        )
    await db.flush()
    return snapshot.id
