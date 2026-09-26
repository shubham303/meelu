from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.site_structure.constants import OPEN_STATES, REVIVABLE_STATES
from src.site_structure.models.link_suggestion import LinkSuggestion
from src.site_structure.models.structure_job import StructureJob
from src.site_structure.ranking import Candidate
from src.site_structure.schemas import (
    LinkSuggestionChanges,
    LinkSuggestionFilter,
    LinkSuggestionRecord,
    LinkSuggestionSummaryResponse,
    NewLinkSuggestion,
    StructureJobRecord,
)


def _now() -> datetime:
    return datetime.now(UTC)


class StructureJobRepository:
    async def create(
        self, db: AsyncSession, user_id: str, site_id: str, prompt: str
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

    async def get(self, db: AsyncSession, site_id: str, job_id: str) -> StructureJobRecord | None:
        row = (
            await db.execute(
                select(StructureJob).where(
                    StructureJob.site_id == site_id, StructureJob.id == job_id
                )
            )
        ).scalar_one_or_none()
        return None if row is None else StructureJobRecord.model_validate(row)

    async def update_status(
        self, db: AsyncSession, site_id: str, job_id: str, status: str
    ) -> StructureJobRecord | None:
        row = (
            await db.execute(
                select(StructureJob).where(
                    StructureJob.site_id == site_id, StructureJob.id == job_id
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        row.status = status
        row.updated_at = _now()
        await db.flush()
        return StructureJobRecord.model_validate(row)

    async def _count(self, db: AsyncSession, query: Select) -> int:
        return (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()

    async def list(
        self, db: AsyncSession, site_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[StructureJobRecord]:
        query = select(StructureJob).where(StructureJob.site_id == site_id)
        rows = (
            await db.execute(
                query.order_by(StructureJob.seq.desc())
                .offset(paging.offset)
                .limit(paging.page_size)
            )
        ).scalars()
        total = await self._count(db, query)
        return PaginatedApiResponse[StructureJobRecord](
            data=[StructureJobRecord.model_validate(r) for r in rows],
            pagination=PaginationService.build_pagination_meta(
                total, paging.page, paging.page_size
            ),
        )


structure_jobs = StructureJobRepository()


class LinkSuggestionRepository:
    async def create(
        self, db: AsyncSession, user_id: str, site_id: str, new: NewLinkSuggestion
    ) -> LinkSuggestionRecord:
        row = LinkSuggestion(**self._values(user_id, site_id, new))
        db.add(row)
        await db.flush()
        return LinkSuggestionRecord.model_validate(row)

    async def create_many(
        self, db: AsyncSession, user_id: str, site_id: str, rows: list[NewLinkSuggestion]
    ) -> int:
        if not rows:
            return 0
        stmt = insert(LinkSuggestion).values([self._values(user_id, site_id, r) for r in rows])
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

    async def get(
        self, db: AsyncSession, site_id: str, suggestion_id: str
    ) -> LinkSuggestionRecord | None:
        row = await self._row(db, site_id, suggestion_id)
        return None if row is None else LinkSuggestionRecord.model_validate(row)

    async def find_edge(
        self, db: AsyncSession, site_id: str, from_page_id: str, to_page_id: str, action: str
    ) -> LinkSuggestionRecord | None:
        row = (
            await db.execute(
                select(LinkSuggestion)
                .where(
                    LinkSuggestion.site_id == site_id,
                    LinkSuggestion.from_page_id == from_page_id,
                    LinkSuggestion.to_page_id == to_page_id,
                    LinkSuggestion.action == action,
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        return None if row is None else LinkSuggestionRecord.model_validate(row)

    async def update(
        self, db: AsyncSession, site_id: str, suggestion_id: str, patch: LinkSuggestionChanges
    ) -> LinkSuggestionRecord | None:
        row = await self._row(db, site_id, suggestion_id)
        if row is None:
            return None
        for key, value in patch.changes().items():
            setattr(row, key, value)
        row.updated_at = _now()
        await db.flush()
        return LinkSuggestionRecord.model_validate(row)

    async def update_scores(
        self, db: AsyncSession, site_id: str, scores: dict[str, float], cut: set[str]
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

    async def delete(self, db: AsyncSession, site_id: str, suggestion_id: str) -> None:
        row = await self._row(db, site_id, suggestion_id)
        if row is not None:
            await db.delete(row)
            await db.flush()

    async def delete_by_ids(self, db: AsyncSession, site_id: str, ids: list[str]) -> int:
        if not ids:
            return 0
        result = await db.execute(
            delete(LinkSuggestion).where(
                LinkSuggestion.site_id == site_id, LinkSuggestion.id.in_(ids)
            )
        )
        return result.rowcount or 0

    async def delete_touching_pages(
        self, db: AsyncSession, site_id: str, page_ids: list[str]
    ) -> int:
        if not page_ids:
            return 0
        result = await db.execute(
            delete(LinkSuggestion).where(
                LinkSuggestion.site_id == site_id,
                or_(
                    LinkSuggestion.from_page_id.in_(page_ids),
                    LinkSuggestion.to_page_id.in_(page_ids),
                ),
            )
        )
        return result.rowcount or 0

    async def summary(self, db: AsyncSession, site_id: str) -> LinkSuggestionSummaryResponse:
        rows = (
            await db.execute(
                select(LinkSuggestion.state, func.count())
                .where(LinkSuggestion.site_id == site_id)
                .group_by(LinkSuggestion.state)
            )
        ).all()
        return LinkSuggestionSummaryResponse(**{state: n for state, n in rows})

    async def list_undone_edges(
        self, db: AsyncSession, site_id: str, action: str
    ) -> list[tuple[str, str, str]]:
        rows = (
            await db.execute(
                select(
                    LinkSuggestion.id, LinkSuggestion.from_page_id, LinkSuggestion.to_page_id
                ).where(
                    LinkSuggestion.site_id == site_id,
                    LinkSuggestion.state != "done",
                    LinkSuggestion.action == action,
                )
            )
        ).all()
        return [(r[0], r[1], r[2]) for r in rows]

    async def done_counts_by_from_page(self, db: AsyncSession, site_id: str) -> dict[str, int]:
        rows = (
            await db.execute(
                select(LinkSuggestion.from_page_id, func.count())
                .where(LinkSuggestion.site_id == site_id, LinkSuggestion.state == "done")
                .group_by(LinkSuggestion.from_page_id)
            )
        ).all()
        return {r[0]: int(r[1]) for r in rows}

    async def open_candidates(self, db: AsyncSession, site_id: str) -> list[Candidate]:
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

    async def list_for_review(
        self,
        db: AsyncSession,
        site_id: str,
        job_id: str | None,
        ids: list[str] | None,
        limit: int,
        unscreened_only: bool,
    ) -> list[LinkSuggestionRecord]:
        conds: list[Any] = [LinkSuggestion.site_id == site_id]
        if ids:
            conds.append(LinkSuggestion.id.in_(ids))
        else:
            conds.append(LinkSuggestion.state == "draft")
            if unscreened_only:
                conds.append(LinkSuggestion.confidence.is_(None))
        if job_id:
            conds.append(LinkSuggestion.job_id == job_id)
        rows = (
            await db.execute(
                select(LinkSuggestion).where(*conds).order_by(LinkSuggestion.seq).limit(limit)
            )
        ).scalars()
        return [LinkSuggestionRecord.model_validate(r) for r in rows]

    async def _row(
        self, db: AsyncSession, site_id: str, suggestion_id: str
    ) -> LinkSuggestion | None:
        return (
            await db.execute(
                select(LinkSuggestion)
                .where(LinkSuggestion.site_id == site_id, LinkSuggestion.id == suggestion_id)
                .limit(1)
            )
        ).scalar_one_or_none()

    def _values(self, user_id: str, site_id: str, new: NewLinkSuggestion) -> dict[str, Any]:
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

    def _order(self, filters: LinkSuggestionFilter) -> tuple[Any, Any]:
        column = {
            "score": LinkSuggestion.score,
            "searchScore": LinkSuggestion.search_score,
            "confidence": LinkSuggestion.confidence,
            "createdAt": LinkSuggestion.created_at,
            "updatedAt": LinkSuggestion.updated_at,
        }[filters.sort_by]
        if filters.sort_order == "asc":
            return column.asc().nulls_last(), LinkSuggestion.seq.asc()
        return column.desc().nulls_last(), LinkSuggestion.seq.desc()

    def _query(
        self, site_id: str, filters: LinkSuggestionFilter, page_ids_any: list[str] | None
    ) -> Select:
        conds: list[Any] = [LinkSuggestion.site_id == site_id]
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
        if page_ids_any is not None:
            conds.append(
                or_(
                    LinkSuggestion.from_page_id.in_(page_ids_any),
                    LinkSuggestion.to_page_id.in_(page_ids_any),
                )
            )
        return select(LinkSuggestion).where(*conds).order_by(*self._order(filters))

    async def _count(self, db: AsyncSession, query: Select) -> int:
        return (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()

    async def list(
        self,
        db: AsyncSession,
        site_id: str,
        filters: LinkSuggestionFilter,
        paging: PaginationParams,
        page_ids_any: list[str] | None = None,
    ) -> PaginatedApiResponse[LinkSuggestionRecord]:
        query = self._query(site_id, filters, page_ids_any)
        rows = (
            (await db.execute(query.offset(paging.offset).limit(paging.page_size))).scalars().all()
        )
        total = await self._count(db, query)
        return PaginatedApiResponse[LinkSuggestionRecord](
            data=[LinkSuggestionRecord.model_validate(r) for r in rows],
            pagination=PaginationService.build_pagination_meta(
                total, paging.page, paging.page_size
            ),
        )


link_suggestions = LinkSuggestionRepository()
