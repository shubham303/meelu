from datetime import datetime
from typing import Any

import numpy as np
from pgvector.sqlalchemy import Vector
from sqlalchemy import Select, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.sql import quote_ident
from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.site_page_llm_extraction.models.site_page_llm_extraction import SitePageLlmExtraction
from src.site_pages.models.site_chunk import SiteChunk
from src.site_pages.models.site_page import SitePage
from src.site_pages.models.site_page_link import SitePageLink
from src.site_structure.constants import OPEN_STATES
from src.site_structure.models.pillar_page_suggestion import PillarPageSuggestion
from src.site_structure.pillars.clustering import PagePoint
from src.site_structure.repository import _count, _now, _page_gone
from src.site_structure.schemas import (
    NewPillarPageSuggestion,
    PillarMember,
    PillarPageSuggestionChanges,
    PillarPageSuggestionFilter,
    PillarPageSuggestionRecord,
    PillarPageSuggestionSummaryResponse,
    PillarReviewInput,
    WorkspaceGroup,
)

EMBEDDING_DIMENSIONS = 384


async def _members(db: AsyncSession, site_id: str, page_ids: list[str]) -> list[PillarMember]:
    if not page_ids:
        return []
    rows = (
        await db.execute(
            select(SitePage.id, SitePage.url, SitePage.title).where(
                SitePage.site_id == site_id, SitePage.id.in_(page_ids)
            )
        )
    ).all()
    by_id = {r[0]: PillarMember(id=r[0], url=r[1], title=r[2]) for r in rows}
    return [by_id[p] for p in page_ids if p in by_id]


async def _record(
    db: AsyncSession, row: PillarPageSuggestion, covering_url: str | None
) -> PillarPageSuggestionRecord:
    return PillarPageSuggestionRecord.model_validate(row).model_copy(
        update={
            "covering_url": covering_url,
            "members": await _members(db, row.site_id, list(row.member_page_ids)),
        }
    )


def _joined(site_id: str) -> Select:
    return (
        select(PillarPageSuggestion, SitePage.url)
        .outerjoin(SitePage, SitePage.id == PillarPageSuggestion.covering_page_id)
        .where(PillarPageSuggestion.site_id == site_id)
    )


async def _row(db: AsyncSession, site_id: str, suggestion_id: str) -> PillarPageSuggestion | None:
    return (
        await db.execute(
            select(PillarPageSuggestion).where(
                PillarPageSuggestion.site_id == site_id, PillarPageSuggestion.id == suggestion_id
            )
        )
    ).scalar_one_or_none()


async def get(
    db: AsyncSession, site_id: str, suggestion_id: str
) -> PillarPageSuggestionRecord | None:
    row = (
        await db.execute(_joined(site_id).where(PillarPageSuggestion.id == suggestion_id))
    ).first()
    return None if row is None else await _record(db, row[0], row[1])


def _values(user_id: str, site_id: str, new: NewPillarPageSuggestion) -> dict[str, Any]:
    now = _now()
    return {
        "id": uid("plr"),
        "user_id": user_id,
        "site_id": site_id,
        "job_id": new.job_id,
        "action": new.action,
        "topic": new.topic,
        "member_page_ids": new.member_page_ids,
        "covering_page_id": new.covering_page_id,
        "suggestion": new.suggestion,
        "search_score": new.search_score,
        "state": new.state,
        "created_at": now,
        "updated_at": now,
    }


async def create_many(
    db: AsyncSession, user_id: str, site_id: str, rows: list[NewPillarPageSuggestion]
) -> int:
    if not rows:
        return 0
    db.add_all(PillarPageSuggestion(**_values(user_id, site_id, r)) for r in rows)
    await db.flush()
    return len(rows)


def _query(site_id: str, filters: PillarPageSuggestionFilter) -> Select:
    conds: list[Any] = []
    if filters.state:
        conds.append(PillarPageSuggestion.state == filters.state)
    if filters.action:
        conds.append(PillarPageSuggestion.action == filters.action)
    if filters.job_id:
        conds.append(PillarPageSuggestion.job_id == filters.job_id)
    return (
        _joined(site_id)
        .where(*conds)
        .order_by(PillarPageSuggestion.score.desc().nulls_last(), PillarPageSuggestion.seq.desc())
    )


async def list_suggestions(
    db: AsyncSession, site_id: str, filters: PillarPageSuggestionFilter, paging: PaginationParams
) -> PaginatedApiResponse[PillarPageSuggestionRecord]:
    query = _query(site_id, filters)
    rows = (await db.execute(query.offset(paging.offset).limit(paging.page_size))).all()
    total = await _count(db, query)
    return PaginatedApiResponse[PillarPageSuggestionRecord](
        data=[await _record(db, r[0], r[1]) for r in rows],
        pagination=PaginationService.build_pagination_meta(total, paging.page, paging.page_size),
    )


async def update_one(
    db: AsyncSession, site_id: str, suggestion_id: str, patch: PillarPageSuggestionChanges
) -> PillarPageSuggestionRecord | None:
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
        update(PillarPageSuggestion),
        [{"id": sid, "score": score, "updated_at": now} for sid, score in scores.items()],
    )
    if cut:
        await db.execute(
            update(PillarPageSuggestion)
            .where(PillarPageSuggestion.site_id == site_id, PillarPageSuggestion.id.in_(cut))
            .values(state="llm_rejected", updated_at=now)
        )


async def delete_one(db: AsyncSession, site_id: str, suggestion_id: str) -> None:
    row = await _row(db, site_id, suggestion_id)
    if row is not None:
        await db.delete(row)
        await db.flush()


async def summary(db: AsyncSession, site_id: str) -> PillarPageSuggestionSummaryResponse:
    rows = (
        await db.execute(
            select(PillarPageSuggestion.state, func.count())
            .where(PillarPageSuggestion.site_id == site_id)
            .group_by(PillarPageSuggestion.state)
        )
    ).all()
    return PillarPageSuggestionSummaryResponse(**{state: n for state, n in rows})


async def page_points(db: AsyncSession, site_id: str) -> list[PagePoint]:
    vectors = (
        select(
            SiteChunk.page_id,
            func.avg(SiteChunk.embedding, type_=Vector(EMBEDDING_DIMENSIONS)).label("vector"),
        )
        .where(SiteChunk.site_id == site_id, SiteChunk.embedding.is_not(None))
        .group_by(SiteChunk.page_id)
        .subquery()
    )
    rows = (
        await db.execute(
            select(
                SitePage.id,
                SitePage.url,
                SitePage.title,
                SitePageLlmExtraction.page_type,
                SitePage.inlinks,
                SitePage.keywords,
                vectors.c.vector,
            )
            .join(vectors, vectors.c.page_id == SitePage.id)
            .outerjoin(SitePageLlmExtraction, SitePageLlmExtraction.page_id == SitePage.id)
            .where(SitePage.site_id == site_id, ~_page_gone(SitePage))
        )
    ).all()
    return [
        PagePoint(
            id=r[0],
            url=r[1],
            title=r[2],
            page_type=r[3],
            inlinks=r[4],
            keywords=tuple(r[5] or ()),
            vector=np.asarray(r[6], dtype=float),
        )
        for r in rows
    ]


async def link_map(db: AsyncSession, site_id: str) -> dict[str, set[str]]:
    rows = (
        await db.execute(
            select(SitePageLink.src_page_id, SitePageLink.dst_page_id).where(
                SitePageLink.site_id == site_id
            )
        )
    ).all()
    links: dict[str, set[str]] = {}
    for src, dst in rows:
        links.setdefault(src, set()).add(dst)
    return links


async def page_changed_at(db: AsyncSession, site_id: str) -> dict[str, datetime]:
    rows = (
        await db.execute(
            select(
                SitePage.id, func.coalesce(SitePage.content_changed_at, SitePage.created_at)
            ).where(SitePage.site_id == site_id)
        )
    ).all()
    return {r[0]: r[1] for r in rows}


async def live_page_ids(db: AsyncSession, site_id: str) -> set[str]:
    rows = (
        await db.execute(
            select(SitePage.id).where(SitePage.site_id == site_id, ~_page_gone(SitePage))
        )
    ).scalars()
    return set(rows)


async def workspace_groups(db: AsyncSession, schema: str, table: str) -> list[WorkspaceGroup]:
    rows = (
        await db.execute(text(f"SELECT * FROM {quote_ident(schema)}.{quote_ident(table)}"))
    ).mappings()
    groups: dict[str, WorkspaceGroup] = {}
    for row in rows:
        if not row.get("group_key") or not row.get("page_id"):
            raise ValueError(f"{table} needs group_key and page_id columns (topic is optional).")
        key = str(row["group_key"])
        group = groups.setdefault(key, WorkspaceGroup(key=key))
        group.page_ids.append(str(row["page_id"]))
        topic = row.get("topic")
        if topic and not group.topic:
            group.topic = str(topic)
    return list(groups.values())


async def member_sets(
    db: AsyncSession, site_id: str, states: tuple[str, ...]
) -> list[tuple[str, list[str]]]:
    rows = (
        await db.execute(
            select(PillarPageSuggestion.id, PillarPageSuggestion.member_page_ids).where(
                PillarPageSuggestion.site_id == site_id, PillarPageSuggestion.state.in_(states)
            )
        )
    ).all()
    return [(r[0], list(r[1])) for r in rows]


async def open_rows(db: AsyncSession, site_id: str) -> list[PillarPageSuggestion]:
    rows = (
        await db.execute(
            select(PillarPageSuggestion).where(
                PillarPageSuggestion.site_id == site_id,
                PillarPageSuggestion.state.in_(OPEN_STATES),
            )
        )
    ).scalars()
    return list(rows)


async def set_states(db: AsyncSession, site_id: str, ids: list[str], state: str) -> int:
    if not ids:
        return 0
    result = await db.execute(
        update(PillarPageSuggestion)
        .where(PillarPageSuggestion.site_id == site_id, PillarPageSuggestion.id.in_(ids))
        .values(state=state, updated_at=_now())
    )
    return result.rowcount or 0


async def review_inputs(
    db: AsyncSession,
    site_id: str,
    job_id: str | None,
    ids: list[str] | None,
    limit: int,
    unscreened_only: bool,
) -> list[PillarReviewInput]:
    conds: list[Any] = [PillarPageSuggestion.site_id == site_id]
    if ids:
        conds.append(PillarPageSuggestion.id.in_(ids))
    else:
        conds.append(PillarPageSuggestion.state == "draft")
        if unscreened_only:
            conds.append(PillarPageSuggestion.confidence.is_(None))
    if job_id:
        conds.append(PillarPageSuggestion.job_id == job_id)
    rows = (
        await db.execute(
            select(PillarPageSuggestion, SitePage.url, SitePage.title)
            .outerjoin(SitePage, SitePage.id == PillarPageSuggestion.covering_page_id)
            .where(*conds)
            .order_by(PillarPageSuggestion.seq)
            .limit(limit)
        )
    ).all()
    items: list[PillarReviewInput] = []
    for row, covering_url, covering_title in rows:
        members = (
            await db.execute(
                select(
                    SitePage.url,
                    SitePage.title,
                    SitePage.meta_description,
                    SitePage.inlinks,
                    SitePageLlmExtraction.page_type,
                )
                .outerjoin(SitePageLlmExtraction, SitePageLlmExtraction.page_id == SitePage.id)
                .where(SitePage.site_id == site_id, SitePage.id.in_(list(row.member_page_ids)))
            )
        ).all()
        items.append(
            PillarReviewInput(
                id=row.id,
                action=row.action,
                topic=row.topic,
                suggestion=row.suggestion,
                search_score=row.search_score,
                covering_url=covering_url,
                covering_title=covering_title,
                members=[
                    {
                        "url": m[0],
                        "title": m[1] or "",
                        "meta_description": m[2] or "",
                        "inlinks": m[3],
                        "page_type": m[4],
                    }
                    for m in members
                ],
            )
        )
    return items
