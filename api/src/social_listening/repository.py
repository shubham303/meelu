from datetime import UTC, datetime
from typing import Any

from sqlalchemy import REAL, cast, func, or_, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.social_listening.models.config import SocialListeningConfig
from src.social_listening.models.post import SocialListeningPost
from src.social_listening.models.query import SocialListeningQuery
from src.social_listening.models.run import SocialListeningRun
from src.social_listening.models.target import SocialListeningTarget
from src.social_listening.schemas import (
    ConfigResponse,
    PostFilters,
    PostResponse,
    QueryResponse,
    RunResponse,
    TargetResponse,
)


def _now() -> datetime:
    return datetime.now(UTC)


async def get_config(db: AsyncSession, site_id: str) -> SocialListeningConfig | None:
    result = await db.execute(
        select(SocialListeningConfig).where(SocialListeningConfig.site_id == site_id).limit(1)
    )
    return result.scalars().first()


async def create_config(db: AsyncSession, user_id: str, site_id: str) -> SocialListeningConfig:
    row = SocialListeningConfig(
        id=uid("slc"),
        user_id=user_id,
        site_id=site_id,
        platforms=[],
        results_per_keyword=50,
        min_relevance=0.6,
        min_similarity=0.8,
        max_age_days=365,
        drop_dead_posts=True,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


async def merge_config(
    db: AsyncSession, row: SocialListeningConfig, values: dict[str, Any]
) -> ConfigResponse:
    for key, value in values.items():
        setattr(row, key, value)
    row.updated_at = _now()
    await db.flush()
    return ConfigResponse.model_validate(row)


def query_response(row: SocialListeningQuery) -> QueryResponse:
    return QueryResponse(
        id=row.id,
        site_id=row.site_id,
        text=row.text,
        enabled=row.enabled,
        source=row.source,
        keywords=row.keywords,
        negative_keywords=row.negative_keywords,
        embedded=row.embedding is not None,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def list_queries(db: AsyncSession, site_id: str) -> list[QueryResponse]:
    result = await db.execute(
        select(SocialListeningQuery)
        .where(SocialListeningQuery.site_id == site_id)
        .order_by(SocialListeningQuery.seq.asc())
    )
    return [query_response(r) for r in result.scalars().all()]


async def existing_query_texts(db: AsyncSession, site_id: str, texts: list[str]) -> set[str]:
    if not texts:
        return set()
    result = await db.execute(
        select(SocialListeningQuery.text).where(
            SocialListeningQuery.site_id == site_id,
            SocialListeningQuery.text.in_(texts),
        )
    )
    return set(result.scalars().all())


async def upsert_queries(
    db: AsyncSession, user_id: str, site_id: str, items: list[dict[str, Any]]
) -> None:
    now = _now()
    for item in items:
        stmt = pg_insert(SocialListeningQuery).values(
            id=uid("slq"), user_id=user_id, site_id=site_id, created_at=now, updated_at=now, **item
        )
        stmt = stmt.on_conflict_do_update(
            constraint="social_listening_query_site_text_key",
            set_={
                "enabled": stmt.excluded.enabled,
                "source": stmt.excluded.source,
                "updated_at": now,
            },
        )
        await db.execute(stmt)
    await db.flush()


async def query_by_id(db: AsyncSession, site_id: str, query_id: str) -> SocialListeningQuery | None:
    result = await db.execute(
        select(SocialListeningQuery)
        .where(SocialListeningQuery.site_id == site_id, SocialListeningQuery.id == query_id)
        .limit(1)
    )
    return result.scalars().first()


async def list_targets(db: AsyncSession, site_id: str) -> list[TargetResponse]:
    result = await db.execute(
        select(SocialListeningTarget)
        .where(SocialListeningTarget.site_id == site_id)
        .order_by(SocialListeningTarget.kind.asc(), SocialListeningTarget.seq.asc())
    )
    return [TargetResponse.model_validate(r) for r in result.scalars().all()]


async def existing_target_keys(
    db: AsyncSession, site_id: str, keys: list[tuple[str, str]]
) -> set[tuple[str, str]]:
    if not keys:
        return set()
    result = await db.execute(
        select(SocialListeningTarget.kind, SocialListeningTarget.name).where(
            SocialListeningTarget.site_id == site_id
        )
    )
    have = {(kind, name) for kind, name in result.all()}
    return {k for k in keys if k in have}


async def upsert_targets(
    db: AsyncSession, user_id: str, site_id: str, items: list[dict[str, Any]]
) -> None:
    now = _now()
    for item in items:
        stmt = pg_insert(SocialListeningTarget).values(
            id=uid("slt"), user_id=user_id, site_id=site_id, created_at=now, updated_at=now, **item
        )
        stmt = stmt.on_conflict_do_update(
            constraint="social_listening_target_site_kind_name_key",
            set_={
                "enabled": stmt.excluded.enabled,
                "source": stmt.excluded.source,
                "updated_at": now,
            },
        )
        await db.execute(stmt)
    await db.flush()


async def target_by_id(
    db: AsyncSession, site_id: str, target_id: str
) -> SocialListeningTarget | None:
    result = await db.execute(
        select(SocialListeningTarget)
        .where(SocialListeningTarget.site_id == site_id, SocialListeningTarget.id == target_id)
        .limit(1)
    )
    return result.scalars().first()


async def merge_row(db: AsyncSession, row: Any, values: dict[str, Any]) -> Any:
    for key, value in values.items():
        setattr(row, key, value)
    row.updated_at = _now()
    await db.flush()
    return row


async def delete_row(db: AsyncSession, row: Any) -> None:
    await db.delete(row)
    await db.flush()


async def create_run(db: AsyncSession, user_id: str, site_id: str) -> RunResponse:
    now = _now()
    row = SocialListeningRun(
        id=uid("slr"),
        user_id=user_id,
        site_id=site_id,
        status="running",
        started_at=now,
        fetched_count=0,
        kept_count=0,
        platform_stats={},
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.flush()
    return RunResponse.model_validate(row)


async def run_by_id(db: AsyncSession, site_id: str, run_id: str) -> SocialListeningRun | None:
    result = await db.execute(
        select(SocialListeningRun)
        .where(SocialListeningRun.site_id == site_id, SocialListeningRun.id == run_id)
        .limit(1)
    )
    return result.scalars().first()


async def list_runs(
    db: AsyncSession, site_id: str, paging: PaginationParams
) -> PaginatedApiResponse[RunResponse]:
    query = (
        select(SocialListeningRun)
        .where(SocialListeningRun.site_id == site_id)
        .order_by(SocialListeningRun.seq.desc())
    )
    return await PaginationService.paginate_query(
        db, query, paging.page, paging.page_size, RunResponse
    )


async def latest_run(db: AsyncSession, site_id: str) -> RunResponse | None:
    result = await db.execute(
        select(SocialListeningRun)
        .where(SocialListeningRun.site_id == site_id)
        .order_by(SocialListeningRun.seq.desc())
        .limit(1)
    )
    row = result.scalars().first()
    return None if row is None else RunResponse.model_validate(row)


async def posts_by_urls(
    db: AsyncSession, site_id: str, urls: list[str]
) -> dict[str, SocialListeningPost]:
    if not urls:
        return {}
    result = await db.execute(
        select(SocialListeningPost).where(
            SocialListeningPost.site_id == site_id, SocialListeningPost.url.in_(urls)
        )
    )
    return {row.url: row for row in result.scalars().all()}


def add_post(db: AsyncSession, user_id: str, site_id: str, values: dict[str, Any]) -> None:
    now = _now()
    db.add(
        SocialListeningPost(
            id=uid("slp"),
            user_id=user_id,
            site_id=site_id,
            created_at=now,
            updated_at=now,
            **values,
        )
    )


async def posts_by_ids(
    db: AsyncSession, site_id: str, ids: list[str]
) -> dict[str, SocialListeningPost]:
    if not ids:
        return {}
    result = await db.execute(
        select(SocialListeningPost).where(
            SocialListeningPost.site_id == site_id, SocialListeningPost.id.in_(ids)
        )
    )
    return {row.id: row for row in result.scalars().all()}


async def pending_gate_count(db: AsyncSession, site_id: str) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(SocialListeningPost)
        .join(SocialListeningQuery, SocialListeningQuery.id == SocialListeningPost.query_id)
        .where(
            SocialListeningPost.site_id == site_id,
            SocialListeningPost.status == "fetched",
            SocialListeningPost.embed_attempts < 3,
            SocialListeningQuery.embed_attempts < 3,
            or_(
                SocialListeningPost.embedding.is_(None),
                SocialListeningQuery.embedding.is_(None),
            ),
        )
    )
    return int(result.scalar_one())


async def gate_by_similarity(
    db: AsyncSession, site_id: str, min_similarity: float
) -> dict[str, int]:
    result = await db.execute(
        text(
            """
            with scored as (
                select p.id, 1 - (p.embedding <=> q.embedding) as similarity
                  from social_listening_post p
                  join social_listening_query q on q.id = p.query_id
                 where p.site_id = :site_id
                   and p.status = 'fetched'
                   and p.embedding is not null
                   and q.embedding is not null
            ),
            updated as (
                update social_listening_post p
                   set similarity = s.similarity,
                       status = case when s.similarity >= :min_similarity
                                     then 'matched' else 'filtered' end,
                       keep_reason = case when s.similarity >= :min_similarity
                                          then null else 'Too far from the query' end,
                       updated_at = now()
                  from scored s
                 where p.id = s.id
             returning p.status
            )
            select status, count(*) from updated group by status
            """
        ),
        {"site_id": site_id, "min_similarity": min_similarity},
    )
    return {status: int(n) for status, n in result.all()}


async def gate_unembeddable(db: AsyncSession, site_id: str) -> int:
    result = await db.execute(
        text(
            """
            with stuck as (
                select p.id
                  from social_listening_post p
                  left join social_listening_query q on q.id = p.query_id
                 where p.site_id = :site_id
                   and p.status = 'fetched'
                   and p.query_id is not null
                   and (p.embed_attempts >= 3 or q.embed_attempts >= 3 or q.id is null)
            )
            update social_listening_post p
               set status = 'filtered', keep_reason = 'Could not be embedded', updated_at = now()
              from stuck s
             where p.id = s.id
            """
        ),
        {"site_id": site_id},
    )
    return int(result.rowcount or 0)


async def gate_targets(db: AsyncSession, site_id: str) -> int:
    result = await db.execute(
        text(
            """
            update social_listening_post
               set status = 'matched', updated_at = now()
             where site_id = :site_id and status = 'fetched' and query_id is null
            """
        ),
        {"site_id": site_id},
    )
    return int(result.rowcount or 0)


async def post_by_id(db: AsyncSession, site_id: str, post_id: str) -> SocialListeningPost | None:
    result = await db.execute(
        select(SocialListeningPost)
        .where(SocialListeningPost.site_id == site_id, SocialListeningPost.id == post_id)
        .limit(1)
    )
    return result.scalars().first()


def _post_order(sort: str | None):
    if sort == "newest":
        return (SocialListeningPost.posted_at.desc().nulls_last(), SocialListeningPost.seq.desc())
    if sort == "engaged":
        return (
            func.coalesce(cast(SocialListeningPost.engagement["score"].astext, REAL), 0.0).desc(),
            SocialListeningPost.seq.desc(),
        )
    if sort == "similarity":
        return (SocialListeningPost.similarity.desc().nulls_last(), SocialListeningPost.seq.asc())
    return (
        SocialListeningPost.composite_score.desc().nulls_last(),
        SocialListeningPost.seq.desc(),
    )


def _post_conditions(site_id: str, f: PostFilters):
    conds = [SocialListeningPost.site_id == site_id]
    if f.kind:
        conds.append(SocialListeningPost.kind == f.kind)
    if f.status:
        conds.append(SocialListeningPost.status == f.status)
    if f.platform:
        conds.append(SocialListeningPost.platform == f.platform)
    if f.intent:
        conds.append(SocialListeningPost.intent == f.intent)
    if f.sentiment:
        conds.append(SocialListeningPost.sentiment == f.sentiment)
    if f.cls:
        conds.append(SocialListeningPost.classes.contains([f.cls]))
    if f.target:
        conds.append(SocialListeningPost.matched_targets.contains([f.target]))
    if f.query_id:
        conds.append(SocialListeningPost.query_id == f.query_id)
    if f.run_id:
        conds.append(SocialListeningPost.run_id == f.run_id)
    if f.min_relevance is not None:
        conds.append(SocialListeningPost.relevance >= f.min_relevance)
    if f.q:
        like = f"%{f.q}%"
        conds.append(
            or_(
                func.coalesce(SocialListeningPost.title, "").ilike(like),
                func.coalesce(SocialListeningPost.text, "").ilike(like),
            )
        )
    return conds


async def list_posts(
    db: AsyncSession, site_id: str, filters: PostFilters, paging: PaginationParams
) -> PaginatedApiResponse[PostResponse]:
    query = (
        select(SocialListeningPost)
        .where(*_post_conditions(site_id, filters))
        .order_by(*_post_order(filters.sort))
    )
    return await PaginationService.paginate_query(
        db, query, paging.page, paging.page_size, PostResponse
    )


async def status_counts(db: AsyncSession, site_id: str) -> dict[str, int]:
    result = await db.execute(
        select(SocialListeningPost.status, func.count())
        .where(SocialListeningPost.site_id == site_id)
        .group_by(SocialListeningPost.status)
    )
    return dict(result.all())


async def kind_counts(db: AsyncSession, site_id: str) -> dict[str, int]:
    result = await db.execute(
        select(SocialListeningPost.kind, func.count())
        .where(SocialListeningPost.site_id == site_id)
        .group_by(SocialListeningPost.kind)
    )
    return dict(result.all())


async def kept_by_query(
    db: AsyncSession, site_id: str, limit: int = 8
) -> list[tuple[str, str, int]]:
    result = await db.execute(
        select(SocialListeningQuery.id, SocialListeningQuery.text, func.count())
        .select_from(SocialListeningPost)
        .join(SocialListeningQuery, SocialListeningQuery.id == SocialListeningPost.query_id)
        .where(
            SocialListeningPost.site_id == site_id,
            SocialListeningPost.status.in_(("needs_reply", "drafted", "replied", "skipped")),
        )
        .group_by(SocialListeningQuery.id, SocialListeningQuery.text)
        .order_by(func.count().desc(), SocialListeningQuery.text.asc())
        .limit(limit)
    )
    return [(i, t, n) for i, t, n in result.all()]


async def class_counts(db: AsyncSession, site_id: str, classes: tuple[str, ...]) -> dict[str, int]:
    cols = [func.count().filter(SocialListeningPost.classes.contains([cls])) for cls in classes]
    result = await db.execute(select(*cols).where(SocialListeningPost.site_id == site_id))
    row = result.one()
    return dict(zip(classes, row))


async def sentiment_counts(db: AsyncSession, site_id: str) -> dict[str, int]:
    result = await db.execute(
        select(SocialListeningPost.sentiment, func.count())
        .where(SocialListeningPost.site_id == site_id, SocialListeningPost.sentiment.is_not(None))
        .group_by(SocialListeningPost.sentiment)
    )
    return dict(result.all())


async def all_posts(
    db: AsyncSession, site_id: str, filters: PostFilters
) -> list[SocialListeningPost]:
    result = await db.execute(
        select(SocialListeningPost)
        .where(*_post_conditions(site_id, filters))
        .order_by(*_post_order(filters.sort))
    )
    return list(result.scalars().all())


async def known_urls(db: AsyncSession, site_id: str, urls: list[str]) -> list[str]:
    if not urls:
        return []
    result = await db.execute(
        select(SocialListeningPost.url).where(
            SocialListeningPost.site_id == site_id, SocialListeningPost.url.in_(urls)
        )
    )
    return [u for (u,) in result.all()]
