from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, delete, exists, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from src.agent.sql import quote_ident
from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.site_pages.models.site_chunk import SiteChunk
from src.site_pages.models.site_page import SitePage
from src.site_pages.models.site_page_link import SitePageLink
from src.site_pages.models.site_page_llm_extraction import SitePageLlmExtraction
from src.site_structure.constants import (
    HIERARCHY_TYPES,
    OPEN_STATES,
    REMOVAL_REGION,
    REVIVABLE_STATES,
)
from src.site_structure.models.link_suggestion import LinkSuggestion
from src.site_structure.models.structure_job import StructureJob
from src.site_structure.ranking import Candidate, PageFacts, SiteDistribution
from src.site_structure.schemas import (
    EdgeFacts,
    HierarchyPage,
    LinkSuggestionChanges,
    LinkSuggestionFilter,
    LinkSuggestionRecord,
    LinkSuggestionSummaryResponse,
    NewLinkSuggestion,
    ScreeningInput,
    StructureJobRecord,
    WorkspaceEdge,
)

FROM_TEXT_CHARS = 3000

FromPage = aliased(SitePage, name="from_page")
ToPage = aliased(SitePage, name="to_page")
ToPageType = aliased(SitePageLlmExtraction, name="to_page_type")


def _is_home(page):
    return func.regexp_replace(page.url, "^[a-z]+://[^/]+", "").in_(("", "/"))


def _now() -> datetime:
    return datetime.now(UTC)


async def create_job(
    db: AsyncSession, user_id: str, site_id: str, prompt: str
) -> StructureJobRecord:
    now = _now()
    job = StructureJob(
        id=uid("sjb"),
        user_id=user_id,
        site_id=site_id,
        prompt=prompt,
        status="RUNNING",
        created_at=now,
        updated_at=now,
    )
    db.add(job)
    await db.flush()
    return StructureJobRecord.model_validate(job)


async def get_job(db: AsyncSession, site_id: str, job_id: str) -> StructureJobRecord | None:
    row = (
        await db.execute(
            select(StructureJob).where(StructureJob.site_id == site_id, StructureJob.id == job_id)
        )
    ).scalar_one_or_none()
    return None if row is None else StructureJobRecord.model_validate(row)


async def list_jobs(
    db: AsyncSession, site_id: str, paging: PaginationParams
) -> PaginatedApiResponse[StructureJobRecord]:
    query = select(StructureJob).where(StructureJob.site_id == site_id)
    rows = (
        await db.execute(
            query.order_by(StructureJob.seq.desc()).offset(paging.offset).limit(paging.page_size)
        )
    ).scalars()
    total = await _count(db, query)
    return PaginatedApiResponse[StructureJobRecord](
        data=[StructureJobRecord.model_validate(r) for r in rows],
        pagination=PaginationService.build_pagination_meta(total, paging.page, paging.page_size),
    )


async def update_job_status(
    db: AsyncSession, site_id: str, job_id: str, status: str
) -> StructureJobRecord | None:
    row = (
        await db.execute(
            select(StructureJob).where(StructureJob.site_id == site_id, StructureJob.id == job_id)
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    row.status = status
    row.updated_at = _now()
    await db.flush()
    return StructureJobRecord.model_validate(row)


def _record(row: Any) -> LinkSuggestionRecord:
    suggestion, from_url, to_url, heading, ordinal = row
    return LinkSuggestionRecord.model_validate(suggestion).model_copy(
        update={
            "from_url": from_url,
            "to_url": to_url,
            "from_chunk_heading": heading,
            "from_chunk_ordinal": ordinal,
        }
    )


def _joined(site_id: str) -> Select:
    return (
        select(LinkSuggestion, FromPage.url, ToPage.url, SiteChunk.heading_path, SiteChunk.ordinal)
        .join(FromPage, FromPage.id == LinkSuggestion.from_page_id)
        .join(ToPage, ToPage.id == LinkSuggestion.to_page_id)
        .outerjoin(SiteChunk, SiteChunk.id == LinkSuggestion.from_chunk_id)
        .where(LinkSuggestion.site_id == site_id)
    )


async def _count(db: AsyncSession, query: Select) -> int:
    return (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()


async def _row(db: AsyncSession, site_id: str, suggestion_id: str) -> LinkSuggestion | None:
    return (
        await db.execute(
            select(LinkSuggestion)
            .where(LinkSuggestion.site_id == site_id, LinkSuggestion.id == suggestion_id)
            .limit(1)
        )
    ).scalar_one_or_none()


async def get(db: AsyncSession, site_id: str, suggestion_id: str) -> LinkSuggestionRecord | None:
    row = (await db.execute(_joined(site_id).where(LinkSuggestion.id == suggestion_id))).first()
    return None if row is None else _record(row)


async def find_edge(
    db: AsyncSession, site_id: str, from_page_id: str, to_page_id: str, action: str
) -> LinkSuggestionRecord | None:
    row = (
        await db.execute(
            _joined(site_id).where(
                LinkSuggestion.from_page_id == from_page_id,
                LinkSuggestion.to_page_id == to_page_id,
                LinkSuggestion.action == action,
            )
        )
    ).first()
    return None if row is None else _record(row)


def _values(user_id: str, site_id: str, new: NewLinkSuggestion) -> dict[str, Any]:
    now = _now()
    return {
        "id": uid("lks"),
        "user_id": user_id,
        "site_id": site_id,
        "job_id": new.job_id,
        "from_page_id": new.from_page_id,
        "to_page_id": new.to_page_id,
        "from_chunk_id": new.from_chunk_id,
        "action": new.action,
        "suggestion": new.suggestion,
        "search_score": new.search_score,
        "state": new.state,
        "created_at": now,
        "updated_at": now,
    }


async def create(
    db: AsyncSession, user_id: str, site_id: str, new: NewLinkSuggestion
) -> LinkSuggestionRecord:
    values = _values(user_id, site_id, new)
    db.add(LinkSuggestion(**values))
    await db.flush()
    found = await get(db, site_id, values["id"])
    assert found is not None
    return found


async def create_many(
    db: AsyncSession, user_id: str, site_id: str, rows: list[NewLinkSuggestion]
) -> int:
    if not rows:
        return 0
    stmt = insert(LinkSuggestion).values([_values(user_id, site_id, r) for r in rows])
    stmt = stmt.on_conflict_do_update(
        constraint="link_suggestions_edge_idx",
        set_={
            "job_id": stmt.excluded.job_id,
            "from_chunk_id": stmt.excluded.from_chunk_id,
            "suggestion": stmt.excluded.suggestion,
            "search_score": stmt.excluded.search_score,
            "state": "draft",
            "confidence": None,
            "score": None,
            "updated_at": stmt.excluded.updated_at,
        },
        where=LinkSuggestion.state.in_(REVIVABLE_STATES),
    ).returning(LinkSuggestion.id)
    return len((await db.execute(stmt)).all())


async def edge_exists(db: AsyncSession, site_id: str, from_page_id: str, to_page_id: str) -> bool:
    row = (
        await db.execute(
            select(SitePageLink.id)
            .where(
                SitePageLink.site_id == site_id,
                SitePageLink.src_page_id == from_page_id,
                SitePageLink.dst_page_id == to_page_id,
            )
            .limit(1)
        )
    ).first()
    return row is not None


async def workspace_edges(db: AsyncSession, schema: str, table: str) -> list[WorkspaceEdge]:
    rows = (
        await db.execute(text(f"SELECT * FROM {quote_ident(schema)}.{quote_ident(table)}"))
    ).mappings()
    edges: list[WorkspaceEdge] = []
    for row in rows:
        if not row.get("from_page_id") or not row.get("to_page_id"):
            raise ValueError(
                f"{table} needs from_page_id and to_page_id columns (reason is optional)."
            )
        reason = row.get("reason")
        edges.append(
            WorkspaceEdge(
                from_page_id=str(row["from_page_id"]),
                to_page_id=str(row["to_page_id"]),
                reason=None if reason is None else str(reason),
            )
        )
    return edges


async def edge_facts(
    db: AsyncSession, site_id: str, pairs: list[tuple[str, str]]
) -> dict[tuple[str, str], EdgeFacts]:
    if not pairs:
        return {}
    inlinks = (
        select(SitePageLink.dst_page_id, func.count().label("n"))
        .where(SitePageLink.site_id == site_id)
        .group_by(SitePageLink.dst_page_id)
        .subquery()
    )
    rows = (
        await db.execute(
            select(
                SitePageLink.src_page_id,
                SitePageLink.dst_page_id,
                SitePageLink.region,
                SitePageLink.anchor,
                ToPage.url,
                _is_home(ToPage),
                SitePageLlmExtraction.page_type,
                func.coalesce(inlinks.c.n, 0),
            )
            .join(ToPage, ToPage.id == SitePageLink.dst_page_id)
            .outerjoin(SitePageLlmExtraction, SitePageLlmExtraction.page_id == ToPage.id)
            .outerjoin(inlinks, inlinks.c.dst_page_id == ToPage.id)
            .where(
                SitePageLink.site_id == site_id,
                SitePageLink.src_page_id.in_({p[0] for p in pairs}),
                SitePageLink.dst_page_id.in_({p[1] for p in pairs}),
            )
            .order_by(SitePageLink.region != REMOVAL_REGION)
        )
    ).all()
    wanted = set(pairs)
    facts: dict[tuple[str, str], EdgeFacts] = {}
    for r in rows:
        key = (r[0], r[1])
        if key not in wanted or key in facts:
            continue
        facts[key] = EdgeFacts(
            from_page_id=r[0],
            to_page_id=r[1],
            region=r[2],
            anchor=r[3],
            to_url=r[4],
            to_inlinks=r[7],
            to_is_hub=bool(r[5]) or r[6] == "hub",
        )
    return facts


ANCHOR_CHUNK_SQL = text(
    """
    SELECT c.id
    FROM site_chunks c
    WHERE c.site_id = :site_id AND c.page_id = :page_id AND c.text ILIKE :needle
    ORDER BY c.ordinal
    LIMIT 1
    """
)

CHUNK_RELEVANCE_SQL = text(
    """
    SELECT 1 - min(c.embedding <=> t.embedding)
    FROM site_chunks c, site_chunks t
    WHERE c.id = :chunk_id AND c.embedding IS NOT NULL
      AND t.site_id = :site_id AND t.page_id = :to_page_id AND t.embedding IS NOT NULL
    """
)

PAGE_RELEVANCE_SQL = text(
    """
    SELECT 1 - (
      (SELECT avg(embedding) FROM site_chunks WHERE site_id = :site_id AND page_id = :from_page_id AND embedding IS NOT NULL)
      <=>
      (SELECT avg(embedding) FROM site_chunks WHERE site_id = :site_id AND page_id = :to_page_id AND embedding IS NOT NULL)
    )
    """
)


async def anchor_chunk(
    db: AsyncSession, site_id: str, page_id: str, anchor: str | None
) -> str | None:
    needle = (anchor or "").strip()
    if not needle:
        return None
    return (
        await db.execute(
            ANCHOR_CHUNK_SQL, {"site_id": site_id, "page_id": page_id, "needle": f"%{needle}%"}
        )
    ).scalar_one_or_none()


async def edge_relevance(
    db: AsyncSession, site_id: str, from_page_id: str, to_page_id: str, chunk_id: str | None
) -> float | None:
    if chunk_id:
        found = (
            await db.execute(
                CHUNK_RELEVANCE_SQL,
                {"site_id": site_id, "chunk_id": chunk_id, "to_page_id": to_page_id},
            )
        ).scalar_one_or_none()
        if found is not None:
            return float(found)
    found = (
        await db.execute(
            PAGE_RELEVANCE_SQL,
            {"site_id": site_id, "from_page_id": from_page_id, "to_page_id": to_page_id},
        )
    ).scalar_one_or_none()
    return None if found is None else float(found)


def _query(site_id: str, filters: LinkSuggestionFilter) -> Select:
    conds: list[Any] = []
    if filters.state:
        conds.append(LinkSuggestion.state == filters.state)
    if filters.action:
        conds.append(LinkSuggestion.action == filters.action)
    if filters.job_id:
        conds.append(LinkSuggestion.job_id == filters.job_id)
    if filters.from_page_id:
        conds.append(LinkSuggestion.from_page_id == filters.from_page_id)
    if filters.to_page_id:
        conds.append(LinkSuggestion.to_page_id == filters.to_page_id)
    if filters.page_id:
        conds.append(
            or_(
                LinkSuggestion.from_page_id == filters.page_id,
                LinkSuggestion.to_page_id == filters.page_id,
            )
        )
    if filters.url:
        needle = f"%{filters.url}%"
        conds.append(or_(FromPage.url.ilike(needle), ToPage.url.ilike(needle)))
    return (
        _joined(site_id)
        .where(*conds)
        .order_by(LinkSuggestion.score.desc().nulls_last(), LinkSuggestion.seq.desc())
    )


async def list_suggestions(
    db: AsyncSession, site_id: str, filters: LinkSuggestionFilter, paging: PaginationParams
) -> PaginatedApiResponse[LinkSuggestionRecord]:
    query = _query(site_id, filters)
    rows = (await db.execute(query.offset(paging.offset).limit(paging.page_size))).all()
    total = await _count(db, query)
    return PaginatedApiResponse[LinkSuggestionRecord](
        data=[_record(row) for row in rows],
        pagination=PaginationService.build_pagination_meta(total, paging.page, paging.page_size),
    )


async def update_one(
    db: AsyncSession, site_id: str, suggestion_id: str, patch: LinkSuggestionChanges
) -> LinkSuggestionRecord | None:
    row = await _row(db, site_id, suggestion_id)
    if row is None:
        return None
    for key, value in patch.changes().items():
        setattr(row, key, value)
    row.updated_at = _now()
    await db.flush()
    return await get(db, site_id, suggestion_id)


async def update_scores(
    db: AsyncSession, site_id: str, scores: dict[str, float], cut: set[str]
) -> None:
    if not scores:
        return
    now = _now()
    await db.execute(
        update(LinkSuggestion),
        [{"id": sid, "score": score, "updated_at": now} for sid, score in scores.items()],
    )
    if cut:
        await db.execute(
            update(LinkSuggestion)
            .where(LinkSuggestion.site_id == site_id, LinkSuggestion.id.in_(cut))
            .values(state="llm_rejected", updated_at=now)
        )


async def delete_one(db: AsyncSession, site_id: str, suggestion_id: str) -> None:
    row = await _row(db, site_id, suggestion_id)
    if row is not None:
        await db.delete(row)
        await db.flush()


async def summary(db: AsyncSession, site_id: str) -> LinkSuggestionSummaryResponse:
    rows = (
        await db.execute(
            select(LinkSuggestion.state, func.count())
            .where(LinkSuggestion.site_id == site_id)
            .group_by(LinkSuggestion.state)
        )
    ).all()
    return LinkSuggestionSummaryResponse(**{state: n for state, n in rows})


def _link_exists() -> Any:
    return exists().where(
        SitePageLink.site_id == LinkSuggestion.site_id,
        SitePageLink.src_page_id == LinkSuggestion.from_page_id,
        SitePageLink.dst_page_id == LinkSuggestion.to_page_id,
    )


async def delete_where_unlinked(db: AsyncSession, site_id: str) -> int:
    result = await db.execute(
        delete(LinkSuggestion).where(
            LinkSuggestion.site_id == site_id,
            LinkSuggestion.state != "done",
            LinkSuggestion.action == "delete",
            ~_link_exists(),
        )
    )
    return result.rowcount or 0


def _page_gone(page: Any) -> Any:
    return or_(
        page.status.is_(None),
        page.status >= 300,
        page.redirect_to.is_not(None),
        page.blocked_by_robots.is_(True),
    )


async def delete_where_linked(db: AsyncSession, site_id: str) -> int:
    result = await db.execute(
        delete(LinkSuggestion).where(
            LinkSuggestion.site_id == site_id,
            LinkSuggestion.state != "done",
            LinkSuggestion.action == "create",
            _link_exists(),
        )
    )
    return result.rowcount or 0


async def delete_where_page_gone(db: AsyncSession, site_id: str) -> int:
    gone_ids = select(SitePage.id).where(SitePage.site_id == site_id, _page_gone(SitePage))
    result = await db.execute(
        delete(LinkSuggestion).where(
            LinkSuggestion.site_id == site_id,
            or_(
                LinkSuggestion.from_page_id.in_(gone_ids),
                LinkSuggestion.to_page_id.in_(gone_ids),
            ),
        )
    )
    return result.rowcount or 0


async def open_candidates(db: AsyncSession, site_id: str) -> list[Candidate]:
    rows = (
        await db.execute(
            select(
                LinkSuggestion.id,
                LinkSuggestion.from_page_id,
                LinkSuggestion.to_page_id,
                LinkSuggestion.search_score,
                LinkSuggestion.confidence,
                LinkSuggestion.action,
            ).where(
                LinkSuggestion.site_id == site_id,
                LinkSuggestion.state.in_(OPEN_STATES),
                LinkSuggestion.action.in_(("create", "delete")),
            )
        )
    ).all()
    return [
        Candidate(
            suggestion_id=r[0],
            from_page_id=r[1],
            to_page_id=r[2],
            search_score=r[3] if r[3] is not None else 1.0,
            confidence=r[4],
            action=r[5],
        )
        for r in rows
    ]


async def page_facts(
    db: AsyncSession, site_id: str
) -> tuple[dict[str, PageFacts], SiteDistribution]:
    outlinks = (
        select(SitePageLink.src_page_id, func.count().label("n"))
        .where(SitePageLink.site_id == site_id, SitePageLink.region == "body")
        .group_by(SitePageLink.src_page_id)
        .subquery()
    )
    done = (
        select(LinkSuggestion.from_page_id, func.count().label("n"))
        .where(LinkSuggestion.site_id == site_id, LinkSuggestion.state == "done")
        .group_by(LinkSuggestion.from_page_id)
        .subquery()
    )
    rows = (
        await db.execute(
            select(
                SitePage.id,
                SitePage.inlinks,
                func.coalesce(outlinks.c.n, 0),
                SitePage.word_count,
                SitePageLlmExtraction.page_type,
                func.coalesce(done.c.n, 0),
                _is_home(SitePage),
            )
            .outerjoin(outlinks, outlinks.c.src_page_id == SitePage.id)
            .outerjoin(done, done.c.from_page_id == SitePage.id)
            .outerjoin(SitePageLlmExtraction, SitePageLlmExtraction.page_id == SitePage.id)
            .where(SitePage.site_id == site_id)
        )
    ).all()
    pages = {
        r[0]: PageFacts(
            page_id=r[0],
            inlinks=r[1],
            outlinks=r[2],
            word_count=r[3],
            page_type=r[4],
            existing_suggestions=r[5],
            is_home=r[6],
        )
        for r in rows
    }
    return pages, SiteDistribution.from_pages(list(pages.values()))


async def hierarchy_pages(db: AsyncSession, site_id: str) -> list[HierarchyPage]:
    rows = (
        await db.execute(
            select(SitePage.id, SitePage.url, _is_home(SitePage), SitePageLlmExtraction.page_type)
            .outerjoin(SitePageLlmExtraction, SitePageLlmExtraction.page_id == SitePage.id)
            .where(
                SitePage.site_id == site_id,
                ~_page_gone(SitePage),
                or_(_is_home(SitePage), SitePageLlmExtraction.page_type.in_(HIERARCHY_TYPES)),
            )
        )
    ).all()
    return [HierarchyPage(id=r[0], url=r[1], is_home=r[2], page_type=r[3]) for r in rows]


async def linked_pairs(db: AsyncSession, site_id: str, page_ids: list[str]) -> set[tuple[str, str]]:
    if not page_ids:
        return set()
    rows = (
        await db.execute(
            select(SitePageLink.src_page_id, SitePageLink.dst_page_id).where(
                SitePageLink.site_id == site_id,
                SitePageLink.src_page_id.in_(page_ids),
                SitePageLink.dst_page_id.in_(page_ids),
            )
        )
    ).all()
    return {(r[0], r[1]) for r in rows}


async def chunks_mentioning(
    db: AsyncSession, site_id: str, to_page_id: str, phrase: str, limit: int
) -> list[tuple[str, str]]:
    already_linked = exists().where(
        SitePageLink.site_id == site_id,
        SitePageLink.src_page_id == SiteChunk.page_id,
        SitePageLink.dst_page_id == to_page_id,
    )
    rows = (
        await db.execute(
            select(SiteChunk.id, SiteChunk.page_id)
            .where(
                SiteChunk.site_id == site_id,
                SiteChunk.page_id != to_page_id,
                SiteChunk.text.ilike(f"%{phrase}%"),
                ~already_linked,
            )
            .order_by(SiteChunk.page_id, SiteChunk.ordinal)
            .limit(limit)
        )
    ).all()
    return [(r[0], r[1]) for r in rows]


async def screening_inputs(
    db: AsyncSession, site_id: str, job_id: str | None, ids: list[str] | None, limit: int
) -> list[ScreeningInput]:
    return await _inputs(db, site_id, job_id, ids, limit, [LinkSuggestion.confidence.is_(None)])


async def review_inputs(
    db: AsyncSession, site_id: str, job_id: str | None, ids: list[str] | None, limit: int
) -> list[ScreeningInput]:
    return await _inputs(db, site_id, job_id, ids, limit, [])


async def _inputs(
    db: AsyncSession,
    site_id: str,
    job_id: str | None,
    ids: list[str] | None,
    limit: int,
    unscreened: list[Any],
) -> list[ScreeningInput]:
    conds: list[Any] = [LinkSuggestion.site_id == site_id]
    if ids:
        conds.append(LinkSuggestion.id.in_(ids))
    else:
        conds.append(LinkSuggestion.state == "draft")
        conds.extend(unscreened)
    if job_id:
        conds.append(LinkSuggestion.job_id == job_id)
    rows = (
        await db.execute(
            select(
                LinkSuggestion,
                FromPage.url,
                FromPage.title,
                FromPage.content_hash,
                func.left(FromPage.body_text, FROM_TEXT_CHARS),
                SiteChunk.text,
                ToPage.url,
                ToPage.title,
                ToPage.meta_description,
                ToPage.h1,
                ToPageType.page_type,
                ToPage.content_hash,
                SitePageLink.anchor,
            )
            .join(FromPage, FromPage.id == LinkSuggestion.from_page_id)
            .join(ToPage, ToPage.id == LinkSuggestion.to_page_id)
            .outerjoin(SiteChunk, SiteChunk.id == LinkSuggestion.from_chunk_id)
            .outerjoin(ToPageType, ToPageType.page_id == ToPage.id)
            .outerjoin(
                SitePageLink,
                (SitePageLink.src_page_id == LinkSuggestion.from_page_id)
                & (SitePageLink.dst_page_id == LinkSuggestion.to_page_id)
                & (SitePageLink.region == REMOVAL_REGION),
            )
            .where(*conds)
            .order_by(LinkSuggestion.seq)
            .limit(limit)
        )
    ).all()
    return [
        ScreeningInput(
            id=r[0].id,
            action=r[0].action,
            suggestion=r[0].suggestion,
            from_url=r[1],
            from_title=r[2],
            from_content_hash=r[3],
            from_text=r[5] or r[4] or "",
            to_url=r[6],
            to_title=r[7],
            to_meta_description=r[8],
            to_h1=list(r[9] or []),
            to_page_type=r[10],
            to_content_hash=r[11],
            anchor=r[12],
        )
        for r in rows
    ]


async def page_exists(db: AsyncSession, site_id: str, page_id: str) -> bool:
    row = (
        await db.execute(
            select(SitePage.id).where(SitePage.site_id == site_id, SitePage.id == page_id)
        )
    ).first()
    return row is not None


async def page_ids_exist(db: AsyncSession, site_id: str, page_ids: list[str]) -> set[str]:
    rows = (
        await db.execute(
            select(SitePage.id).where(SitePage.site_id == site_id, SitePage.id.in_(page_ids))
        )
    ).scalars()
    return set(rows)


async def page_id_by_url(db: AsyncSession, site_id: str, url: str) -> str | None:
    return (
        await db.execute(
            select(SitePage.id).where(SitePage.site_id == site_id, SitePage.url == url)
        )
    ).scalar_one_or_none()


async def chunk_page_id(db: AsyncSession, site_id: str, chunk_id: str) -> str | None:
    return (
        await db.execute(
            select(SiteChunk.page_id).where(SiteChunk.site_id == site_id, SiteChunk.id == chunk_id)
        )
    ).scalar_one_or_none()
