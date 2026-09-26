from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, bindparam, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.site_structure.constants import SuggestionState
from src.site_structure.models.pillar_page_suggestion import PillarPageSuggestion
from src.site_structure.pillars.schemas import (
    NewPillarPageSuggestion,
    PillarPageSuggestionChanges,
    PillarPageSuggestionFilter,
    PillarPageSuggestionRecord,
    PillarPageSuggestionSummaryResponse,
    PillarSortBy,
    SortOrder,
)


def member_key(page_ids: list[str]) -> str:
    return hashlib.sha256(",".join(sorted(set(page_ids))).encode()).hexdigest()


class PillarPageSuggestionRepository:
    ID_PREFIX = "plr"

    async def create(
        self, db: AsyncSession, user_id: str, site_id: str, new: NewPillarPageSuggestion
    ) -> PillarPageSuggestionRecord:
        values = self._values(user_id, site_id, new)
        db.add(PillarPageSuggestion(**values))
        await db.flush()
        created = await self.get(db, site_id, values["id"])
        assert created is not None
        return created

    async def create_many(
        self, db: AsyncSession, user_id: str, site_id: str, rows: list[NewPillarPageSuggestion]
    ) -> int:
        if not rows:
            return 0
        stmt = (
            insert(PillarPageSuggestion)
            .values([self._values(user_id, site_id, r) for r in rows])
            .on_conflict_do_nothing(constraint="pillar_page_suggestions_members_idx")
            .returning(PillarPageSuggestion.id)
        )
        return len((await db.execute(stmt)).all())

    async def get(
        self, db: AsyncSession, site_id: str, suggestion_id: str
    ) -> PillarPageSuggestionRecord | None:
        row = await self._row(db, site_id, suggestion_id)
        return None if row is None else PillarPageSuggestionRecord.model_validate(row)

    async def find_by_members(
        self, db: AsyncSession, site_id: str, member_page_ids: list[str]
    ) -> PillarPageSuggestionRecord | None:
        row = (
            await db.execute(
                select(PillarPageSuggestion)
                .where(
                    PillarPageSuggestion.site_id == site_id,
                    PillarPageSuggestion.member_key == member_key(member_page_ids),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        return None if row is None else PillarPageSuggestionRecord.model_validate(row)

    async def list(
        self,
        db: AsyncSession,
        site_id: str,
        filters: PillarPageSuggestionFilter,
        paging: PaginationParams,
    ) -> PaginatedApiResponse[PillarPageSuggestionRecord]:
        query = self._filtered(site_id, filters)
        total = (
            await db.execute(select(func.count()).select_from(query.order_by(None).subquery()))
        ).scalar_one()
        rows = (await db.execute(query.offset(paging.offset).limit(paging.page_size))).scalars()
        return PaginatedApiResponse[PillarPageSuggestionRecord](
            data=[PillarPageSuggestionRecord.model_validate(row) for row in rows],
            pagination=PaginationService.build_pagination_meta(
                total, paging.page, paging.page_size
            ),
        )

    async def list_for_site(
        self, db: AsyncSession, site_id: str
    ) -> list[PillarPageSuggestionRecord]:
        rows = (
            await db.execute(
                select(PillarPageSuggestion).where(PillarPageSuggestion.site_id == site_id)
            )
        ).scalars()
        return [PillarPageSuggestionRecord.model_validate(row) for row in rows]

    async def update(
        self,
        db: AsyncSession,
        site_id: str,
        suggestion_id: str,
        patch: PillarPageSuggestionChanges,
    ) -> PillarPageSuggestionRecord | None:
        row = await self._row(db, site_id, suggestion_id)
        if row is None:
            return None
        for key, value in patch.changes().items():
            setattr(row, key, value)
        row.updated_at = datetime.now(UTC)
        await db.flush()
        return PillarPageSuggestionRecord.model_validate(row)

    async def list_in_state(
        self,
        db: AsyncSession,
        site_id: str,
        state: SuggestionState,
        job_id: str | None = None,
        ids: list[str] | None = None,
        limit: int | None = None,
    ) -> list[PillarPageSuggestionRecord]:
        conditions: list[Any] = [
            PillarPageSuggestion.site_id == site_id,
            PillarPageSuggestion.state == state,
        ]
        if job_id:
            conditions.append(PillarPageSuggestion.job_id == job_id)
        if ids:
            conditions.append(PillarPageSuggestion.id.in_(set(ids)))
        query = select(PillarPageSuggestion).where(*conditions).order_by(PillarPageSuggestion.seq)
        if limit is not None:
            query = query.limit(limit)
        rows = (await db.execute(query)).scalars()
        return [PillarPageSuggestionRecord.model_validate(row) for row in rows]

    async def member_sets(
        self, db: AsyncSession, site_id: str
    ) -> list[tuple[SuggestionState, list[str]]]:
        rows = await db.execute(
            select(PillarPageSuggestion.state, PillarPageSuggestion.member_page_ids).where(
                PillarPageSuggestion.site_id == site_id
            )
        )
        return [(SuggestionState(state), list(members)) for state, members in rows.all()]

    async def update_scores(self, db: AsyncSession, site_id: str, scores: dict[str, float]) -> None:
        if not scores:
            return
        table = PillarPageSuggestion.__table__
        await db.execute(
            update(table)
            .where(table.c.site_id == bindparam("b_site"), table.c.id == bindparam("b_id"))
            .values(score=bindparam("b_score"), updated_at=datetime.now(UTC)),
            [{"b_site": site_id, "b_id": sid, "b_score": score} for sid, score in scores.items()],
        )

    async def delete_many(self, db: AsyncSession, site_id: str, ids: set[str]) -> int:
        if not ids:
            return 0
        result = await db.execute(
            delete(PillarPageSuggestion).where(
                PillarPageSuggestion.site_id == site_id, PillarPageSuggestion.id.in_(ids)
            )
        )
        return result.rowcount or 0

    async def delete(self, db: AsyncSession, site_id: str, suggestion_id: str) -> bool:
        result = await db.execute(
            delete(PillarPageSuggestion).where(
                PillarPageSuggestion.site_id == site_id,
                PillarPageSuggestion.id == suggestion_id,
            )
        )
        await db.flush()
        return bool(result.rowcount)

    async def summary(self, db: AsyncSession, site_id: str) -> PillarPageSuggestionSummaryResponse:
        rows = (
            await db.execute(
                select(PillarPageSuggestion.state, func.count())
                .where(PillarPageSuggestion.site_id == site_id)
                .group_by(PillarPageSuggestion.state)
            )
        ).all()
        return PillarPageSuggestionSummaryResponse(**{state: count for state, count in rows})

    def _values(self, user_id: str, site_id: str, new: NewPillarPageSuggestion) -> dict[str, Any]:
        now = datetime.now(UTC)
        members = sorted(set(new.member_page_ids))
        return {
            "id": uid(self.ID_PREFIX),
            "user_id": user_id,
            "site_id": site_id,
            "job_id": new.job_id,
            "action": new.action,
            "topic": new.topic,
            "member_page_ids": members,
            "member_key": member_key(members),
            "covering_page_id": new.covering_page_id,
            "suggestion": new.suggestion,
            "search_score": new.search_score,
            "state": new.state,
            "created_at": now,
            "updated_at": now,
        }

    def _filtered(self, site_id: str, filters: PillarPageSuggestionFilter) -> Select:
        conditions: list[Any] = [PillarPageSuggestion.site_id == site_id]
        if filters.states:
            conditions.append(PillarPageSuggestion.state.in_(filters.states))
        if filters.action:
            conditions.append(PillarPageSuggestion.action == filters.action)
        if filters.job_id:
            conditions.append(PillarPageSuggestion.job_id == filters.job_id)
        if filters.page_id:
            conditions.append(
                or_(
                    PillarPageSuggestion.member_page_ids.contains([filters.page_id]),
                    PillarPageSuggestion.covering_page_id == filters.page_id,
                )
            )
        return select(PillarPageSuggestion).where(*conditions).order_by(*self._order(filters))

    def _order(self, filters: PillarPageSuggestionFilter) -> tuple[Any, Any]:
        column = {
            PillarSortBy.SCORE: PillarPageSuggestion.score,
            PillarSortBy.SEARCH_SCORE: PillarPageSuggestion.search_score,
            PillarSortBy.CONFIDENCE: PillarPageSuggestion.confidence,
            PillarSortBy.CREATED_AT: PillarPageSuggestion.created_at,
            PillarSortBy.UPDATED_AT: PillarPageSuggestion.updated_at,
        }[filters.sort_by]
        if filters.sort_order is SortOrder.ASC:
            return column.asc().nulls_last(), PillarPageSuggestion.seq.asc()
        return column.desc().nulls_last(), PillarPageSuggestion.seq.desc()

    async def _row(
        self, db: AsyncSession, site_id: str, suggestion_id: str
    ) -> PillarPageSuggestion | None:
        return (
            await db.execute(
                select(PillarPageSuggestion)
                .where(
                    PillarPageSuggestion.site_id == site_id,
                    PillarPageSuggestion.id == suggestion_id,
                )
                .limit(1)
            )
        ).scalar_one_or_none()


pillar_page_suggestions = PillarPageSuggestionRepository()
