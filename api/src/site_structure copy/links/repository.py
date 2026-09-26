from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.site_structure.constants import OPEN_STATES, REVIVABLE_STATES, SuggestionState
from src.site_structure.links.schemas import (
    LinkAction,
    LinkSuggestionChanges,
    LinkSuggestionFilter,
    LinkSuggestionRecord,
    LinkSuggestionSummaryResponse,
    NewLinkSuggestion,
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
        stmt = insert(LinkSuggestion).values([self._values(user_id, site_id, r) for r in rows])
        stmt = stmt.on_conflict_do_update(
            constraint="link_suggestions_edge_idx",
            set_={
                "job_id": stmt.excluded.job_id,
                "from_chunk_id": stmt.excluded.from_chunk_id,
                "suggestion": stmt.excluded.suggestion,
                "search_score": stmt.excluded.search_score,
                "state": SuggestionState.DRAFT,
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
        self,
        db: AsyncSession,
        site_id: str,
        from_page_id: str,
        to_page_id: str,
        action: LinkAction,
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

    async def list(
        self,
        db: AsyncSession,
        site_id: str,
        filters: LinkSuggestionFilter,
        paging: PaginationParams,
        from_page_ids: set[str] | None = None,
        to_page_ids: set[str] | None = None,
    ) -> PaginatedApiResponse[LinkSuggestionRecord]:
        query = self._filtered(site_id, filters, from_page_ids, to_page_ids)
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

    async def list_open(self, db: AsyncSession, site_id: str) -> list[LinkSuggestionRecord]:
        rows = (
            await db.execute(
                select(LinkSuggestion).where(
                    LinkSuggestion.site_id == site_id,
                    LinkSuggestion.state.in_(OPEN_STATES),
                )
            )
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

    async def set_state(
        self, db: AsyncSession, site_id: str, ids: set[str], state: SuggestionState
    ) -> int:
        if not ids:
            return 0
        result = await db.execute(
            update(LinkSuggestion)
            .where(LinkSuggestion.site_id == site_id, LinkSuggestion.id.in_(ids))
            .values(state=state, updated_at=datetime.now(UTC))
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
    ) -> Select:
        conditions: list[Any] = [LinkSuggestion.site_id == site_id]
        if filters.state:
            conditions.append(LinkSuggestion.state == filters.state)
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
        return (
            select(LinkSuggestion)
            .where(*conditions)
            .order_by(LinkSuggestion.score.desc().nulls_last(), LinkSuggestion.seq.desc())
        )

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
