from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, bindparam, delete, func, or_, select, tuple_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.site_structure.constants import SuggestionState
from src.site_structure.links.schemas import (
    LinkAction,
    LinkSortBy,
    LinkSuggestionChanges,
    LinkSuggestionFilter,
    LinkSuggestionRecord,
    LinkSuggestionSummaryResponse,
    NewLinkSuggestion,
    SortOrder,
)
from src.site_structure.models.link_suggestion import LinkSuggestion


class LinkSuggestionRepository:
    ID_PREFIX = "lks"

    async def create(
        self, db: AsyncSession, user_id: str, site_id: str, new: NewLinkSuggestion
    ) -> LinkSuggestionRecord:
        values = self._values(user_id, site_id, new)
        db.add(LinkSuggestion(**values))
        await db.flush()
        created = await self.get(db, site_id, values["id"])
        assert created is not None
        return created

    async def create_many(
        self, db: AsyncSession, user_id: str, site_id: str, rows: list[NewLinkSuggestion]
    ) -> int:
        if not rows:
            return 0
        stmt = (
            insert(LinkSuggestion)
            .values([self._values(user_id, site_id, r) for r in rows])
            .on_conflict_do_nothing(constraint="link_suggestions_edge_idx")
            .returning(LinkSuggestion.id)
        )
        return len((await db.execute(stmt)).all())

    async def get(
        self, db: AsyncSession, site_id: str, suggestion_id: str
    ) -> LinkSuggestionRecord | None:
        row = await self._row(db, site_id, suggestion_id)
        return None if row is None else LinkSuggestionRecord.model_validate(row)

    async def find_edge(
        self,
        db: AsyncSession,
        site_id: str,
        from_page_id: str,
        from_chunk_id: str | None,
        to_page_id: str,
        action: LinkAction,
        exclude_id: str | None = None,
    ) -> LinkSuggestionRecord | None:
        conditions: list[Any] = [
            LinkSuggestion.site_id == site_id,
            LinkSuggestion.from_page_id == from_page_id,
            LinkSuggestion.to_page_id == to_page_id,
            LinkSuggestion.action == action,
        ]
        if from_chunk_id is not None:
            conditions.append(LinkSuggestion.from_chunk_id == from_chunk_id)
        if exclude_id is not None:
            conditions.append(LinkSuggestion.id != exclude_id)
        row = (
            await db.execute(select(LinkSuggestion).where(*conditions).limit(1))
        ).scalar_one_or_none()
        return None if row is None else LinkSuggestionRecord.model_validate(row)

    async def edge_keys(
        self, db: AsyncSession, site_id: str, pairs: list[tuple[str, str]]
    ) -> set[tuple[str, str, LinkAction, str | None]]:
        if not pairs:
            return set()
        rows = await db.execute(
            select(
                LinkSuggestion.from_page_id,
                LinkSuggestion.to_page_id,
                LinkSuggestion.action,
                LinkSuggestion.from_chunk_id,
            ).where(
                LinkSuggestion.site_id == site_id,
                tuple_(LinkSuggestion.from_page_id, LinkSuggestion.to_page_id).in_(set(pairs)),
            )
        )
        return {(r[0], r[1], LinkAction(r[2]), r[3]) for r in rows}

    async def list(
        self,
        db: AsyncSession,
        site_id: str,
        filters: LinkSuggestionFilter,
        paging: PaginationParams,
        from_page_ids: set[str] | None = None,
        to_page_ids: set[str] | None = None,
        either_page_ids: set[str] | None = None,
    ) -> PaginatedApiResponse[LinkSuggestionRecord]:
        query = self._filtered(site_id, filters, from_page_ids, to_page_ids, either_page_ids)
        total = (
            await db.execute(select(func.count()).select_from(query.order_by(None).subquery()))
        ).scalar_one()
        rows = (await db.execute(query.offset(paging.offset).limit(paging.page_size))).scalars()
        return PaginatedApiResponse[LinkSuggestionRecord](
            data=[LinkSuggestionRecord.model_validate(row) for row in rows],
            pagination=PaginationService.build_pagination_meta(
                total, paging.page, paging.page_size
            ),
        )

    async def list_for_site(self, db: AsyncSession, site_id: str) -> list[LinkSuggestionRecord]:
        rows = (
            await db.execute(select(LinkSuggestion).where(LinkSuggestion.site_id == site_id))
        ).scalars()
        return [LinkSuggestionRecord.model_validate(row) for row in rows]

    async def update(
        self,
        db: AsyncSession,
        site_id: str,
        suggestion_id: str,
        patch: LinkSuggestionChanges,
    ) -> LinkSuggestionRecord | None:
        row = await self._row(db, site_id, suggestion_id)
        if row is None:
            return None
        for key, value in patch.changes().items():
            setattr(row, key, value)
        row.updated_at = datetime.now(UTC)
        await db.flush()
        return await self.get(db, site_id, suggestion_id)

    async def list_in_state(
        self,
        db: AsyncSession,
        site_id: str,
        state: SuggestionState,
        job_id: str | None = None,
        ids: list[str] | None = None,
        limit: int | None = None,
    ) -> list[LinkSuggestionRecord]:
        conditions: list[Any] = [LinkSuggestion.site_id == site_id, LinkSuggestion.state == state]
        if job_id:
            conditions.append(LinkSuggestion.job_id == job_id)
        if ids:
            conditions.append(LinkSuggestion.id.in_(set(ids)))
        query = select(LinkSuggestion).where(*conditions).order_by(LinkSuggestion.seq)
        if limit is not None:
            query = query.limit(limit)
        rows = (await db.execute(query)).scalars()
        return [LinkSuggestionRecord.model_validate(row) for row in rows]

    async def ids_in_state(
        self, db: AsyncSession, site_id: str, ids: list[str], state: SuggestionState
    ) -> set[str]:
        if not ids:
            return set()
        rows = await db.execute(
            select(LinkSuggestion.id).where(
                LinkSuggestion.site_id == site_id,
                LinkSuggestion.id.in_(set(ids)),
                LinkSuggestion.state == state,
            )
        )
        return set(rows.scalars().all())

    async def transition(
        self,
        db: AsyncSession,
        site_id: str,
        ids: set[str],
        from_state: SuggestionState,
        to_state: SuggestionState,
    ) -> int:
        if not ids:
            return 0
        result = await db.execute(
            update(LinkSuggestion)
            .where(
                LinkSuggestion.site_id == site_id,
                LinkSuggestion.id.in_(ids),
                LinkSuggestion.state == from_state,
            )
            .values(state=to_state, updated_at=datetime.now(UTC))
        )
        return result.rowcount or 0

    async def update_scores(self, db: AsyncSession, site_id: str, scores: dict[str, float]) -> None:
        if not scores:
            return
        table = LinkSuggestion.__table__
        await db.execute(
            update(table)
            .where(table.c.site_id == bindparam("b_site"), table.c.id == bindparam("b_id"))
            .values(score=bindparam("b_score"), updated_at=datetime.now(UTC)),
            [{"b_site": site_id, "b_id": sid, "b_score": score} for sid, score in scores.items()],
        )

    async def approved_create_counts(
        self, db: AsyncSession, site_id: str, page_ids: list[str]
    ) -> dict[str, int]:
        if not page_ids:
            return {}
        rows = await db.execute(
            select(LinkSuggestion.from_page_id, func.count())
            .where(
                LinkSuggestion.site_id == site_id,
                LinkSuggestion.from_page_id.in_(set(page_ids)),
                LinkSuggestion.action == LinkAction.CREATE,
                LinkSuggestion.state == SuggestionState.REVIEW_APPROVED,
            )
            .group_by(LinkSuggestion.from_page_id)
        )
        return {page_id: count for page_id, count in rows.all()}

    async def delete_many(self, db: AsyncSession, site_id: str, ids: set[str]) -> int:
        if not ids:
            return 0
        result = await db.execute(
            delete(LinkSuggestion).where(
                LinkSuggestion.site_id == site_id, LinkSuggestion.id.in_(ids)
            )
        )
        return result.rowcount or 0

    async def delete(self, db: AsyncSession, site_id: str, suggestion_id: str) -> bool:
        result = await db.execute(
            delete(LinkSuggestion).where(
                LinkSuggestion.site_id == site_id, LinkSuggestion.id == suggestion_id
            )
        )
        await db.flush()
        return bool(result.rowcount)

    async def summary(self, db: AsyncSession, site_id: str) -> LinkSuggestionSummaryResponse:
        rows = (
            await db.execute(
                select(LinkSuggestion.state, func.count())
                .where(LinkSuggestion.site_id == site_id)
                .group_by(LinkSuggestion.state)
            )
        ).all()
        return LinkSuggestionSummaryResponse(**{state: count for state, count in rows})

    def _values(self, user_id: str, site_id: str, new: NewLinkSuggestion) -> dict[str, Any]:
        now = datetime.now(UTC)
        return {
            "id": uid(self.ID_PREFIX),
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

    def _filtered(
        self,
        site_id: str,
        filters: LinkSuggestionFilter,
        from_page_ids: set[str] | None,
        to_page_ids: set[str] | None,
        either_page_ids: set[str] | None,
    ) -> Select:
        conditions: list[Any] = [LinkSuggestion.site_id == site_id]
        if filters.states:
            conditions.append(LinkSuggestion.state.in_(filters.states))
        if filters.action:
            conditions.append(LinkSuggestion.action == filters.action)
        if filters.job_id:
            conditions.append(LinkSuggestion.job_id == filters.job_id)
        if filters.from_page_id:
            conditions.append(LinkSuggestion.from_page_id == filters.from_page_id)
        if filters.to_page_id:
            conditions.append(LinkSuggestion.to_page_id == filters.to_page_id)
        if filters.page_id:
            conditions.append(
                or_(
                    LinkSuggestion.from_page_id == filters.page_id,
                    LinkSuggestion.to_page_id == filters.page_id,
                )
            )
        if from_page_ids is not None:
            conditions.append(LinkSuggestion.from_page_id.in_(from_page_ids))
        if to_page_ids is not None:
            conditions.append(LinkSuggestion.to_page_id.in_(to_page_ids))
        if either_page_ids is not None:
            conditions.append(
                or_(
                    LinkSuggestion.from_page_id.in_(either_page_ids),
                    LinkSuggestion.to_page_id.in_(either_page_ids),
                )
            )
        return select(LinkSuggestion).where(*conditions).order_by(*self._order(filters))

    def _order(self, filters: LinkSuggestionFilter) -> tuple[Any, Any]:
        column = {
            LinkSortBy.SCORE: LinkSuggestion.score,
            LinkSortBy.SEARCH_SCORE: LinkSuggestion.search_score,
            LinkSortBy.CONFIDENCE: LinkSuggestion.confidence,
            LinkSortBy.CREATED_AT: LinkSuggestion.created_at,
            LinkSortBy.UPDATED_AT: LinkSuggestion.updated_at,
        }[filters.sort_by]
        if filters.sort_order is SortOrder.ASC:
            return column.asc().nulls_last(), LinkSuggestion.seq.asc()
        return column.desc().nulls_last(), LinkSuggestion.seq.desc()

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


link_suggestions = LinkSuggestionRepository()
