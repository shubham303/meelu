from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.site_structure.constants import OPEN_STATES
from src.site_structure.models.pillar_page_suggestion import PillarPageSuggestion
from src.site_structure.schemas import (
    NewPillarPageSuggestion,
    PillarPageSuggestionChanges,
    PillarPageSuggestionFilter,
    PillarPageSuggestionRecord,
    PillarPageSuggestionSummaryResponse,
)


def _now() -> datetime:
    return datetime.now(UTC)


class PillarPageSuggestionRepository:
    async def get(
        self, db: AsyncSession, site_id: str, suggestion_id: str
    ) -> PillarPageSuggestionRecord | None:
        row = await self._row(db, site_id, suggestion_id)
        return None if row is None else PillarPageSuggestionRecord.model_validate(row)

    async def create_many(
        self, db: AsyncSession, user_id: str, site_id: str, rows: list[NewPillarPageSuggestion]
    ) -> int:
        if not rows:
            return 0
        db.add_all(PillarPageSuggestion(**self._values(user_id, site_id, r)) for r in rows)
        await db.flush()
        return len(rows)

    async def update(
        self, db: AsyncSession, site_id: str, suggestion_id: str, patch: PillarPageSuggestionChanges
    ) -> PillarPageSuggestionRecord | None:
        row = await self._row(db, site_id, suggestion_id)
        if row is None:
            return None
        for key, value in patch.changes().items():
            setattr(row, key, value)
        row.updated_at = _now()
        await db.flush()
        return PillarPageSuggestionRecord.model_validate(row)

    async def update_scores(
        self, db: AsyncSession, site_id: str, scores: dict[str, float], cut: set[str]
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

    async def delete(self, db: AsyncSession, site_id: str, suggestion_id: str) -> None:
        row = await self._row(db, site_id, suggestion_id)
        if row is not None:
            await db.delete(row)
            await db.flush()

    async def summary(self, db: AsyncSession, site_id: str) -> PillarPageSuggestionSummaryResponse:
        rows = (
            await db.execute(
                select(PillarPageSuggestion.state, func.count())
                .where(PillarPageSuggestion.site_id == site_id)
                .group_by(PillarPageSuggestion.state)
            )
        ).all()
        return PillarPageSuggestionSummaryResponse(**{state: n for state, n in rows})

    async def member_sets(
        self, db: AsyncSession, site_id: str, states: tuple[str, ...]
    ) -> list[tuple[str, list[str]]]:
        rows = (
            await db.execute(
                select(PillarPageSuggestion.id, PillarPageSuggestion.member_page_ids).where(
                    PillarPageSuggestion.site_id == site_id, PillarPageSuggestion.state.in_(states)
                )
            )
        ).all()
        return [(r[0], list(r[1])) for r in rows]

    async def open_rows(self, db: AsyncSession, site_id: str) -> list[PillarPageSuggestion]:
        rows = (
            await db.execute(
                select(PillarPageSuggestion).where(
                    PillarPageSuggestion.site_id == site_id,
                    PillarPageSuggestion.state.in_(OPEN_STATES),
                )
            )
        ).scalars()
        return list(rows)

    async def set_states(self, db: AsyncSession, site_id: str, ids: list[str], state: str) -> int:
        if not ids:
            return 0
        result = await db.execute(
            update(PillarPageSuggestion)
            .where(PillarPageSuggestion.site_id == site_id, PillarPageSuggestion.id.in_(ids))
            .values(state=state, updated_at=_now())
        )
        return result.rowcount or 0

    async def list_for_review(
        self,
        db: AsyncSession,
        site_id: str,
        job_id: str | None,
        ids: list[str] | None,
        limit: int,
        unscreened_only: bool,
    ) -> list[PillarPageSuggestionRecord]:
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
                select(PillarPageSuggestion)
                .where(*conds)
                .order_by(PillarPageSuggestion.seq)
                .limit(limit)
            )
        ).scalars()
        return [PillarPageSuggestionRecord.model_validate(r) for r in rows]

    async def _row(
        self, db: AsyncSession, site_id: str, suggestion_id: str
    ) -> PillarPageSuggestion | None:
        return (
            await db.execute(
                select(PillarPageSuggestion).where(
                    PillarPageSuggestion.site_id == site_id,
                    PillarPageSuggestion.id == suggestion_id,
                )
            )
        ).scalar_one_or_none()

    def _values(self, user_id: str, site_id: str, new: NewPillarPageSuggestion) -> dict[str, Any]:
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

    def _order(self, filters: PillarPageSuggestionFilter) -> tuple[Any, Any]:
        column = {
            "score": PillarPageSuggestion.score,
            "searchScore": PillarPageSuggestion.search_score,
            "confidence": PillarPageSuggestion.confidence,
            "createdAt": PillarPageSuggestion.created_at,
            "updatedAt": PillarPageSuggestion.updated_at,
        }[filters.sort_by]
        if filters.sort_order == "asc":
            return column.asc().nulls_last(), PillarPageSuggestion.seq.asc()
        return column.desc().nulls_last(), PillarPageSuggestion.seq.desc()

    def _query(self, site_id: str, filters: PillarPageSuggestionFilter) -> Select:
        conds: list[Any] = []
        if filters.state:
            conds.append(PillarPageSuggestion.state == filters.state)
        if filters.action:
            conds.append(PillarPageSuggestion.action == filters.action)
        if filters.job_id:
            conds.append(PillarPageSuggestion.job_id == filters.job_id)
        return (
            select(PillarPageSuggestion)
            .where(PillarPageSuggestion.site_id == site_id, *conds)
            .order_by(*self._order(filters))
        )

    async def _count(self, db: AsyncSession, query: Select) -> int:
        return (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()

    async def list(
        self,
        db: AsyncSession,
        site_id: str,
        filters: PillarPageSuggestionFilter,
        paging: PaginationParams,
    ) -> PaginatedApiResponse[PillarPageSuggestionRecord]:
        query = self._query(site_id, filters)
        rows = (
            (await db.execute(query.offset(paging.offset).limit(paging.page_size))).scalars().all()
        )
        total = await self._count(db, query)
        return PaginatedApiResponse[PillarPageSuggestionRecord](
            data=[PillarPageSuggestionRecord.model_validate(r) for r in rows],
            pagination=PaginationService.build_pagination_meta(
                total, paging.page, paging.page_size
            ),
        )


pillar_page_suggestions = PillarPageSuggestionRepository()
