from typing import Any

from sqlalchemy import Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.seo.constants import OPEN_STATES
from src.seo.models.page_suggestion import SeoPageSuggestion
from src.seo.repositories.base import now, page
from src.seo.schemas import PageSuggestionFilter, PageSuggestionRecord, PageSuggestionSummary

class SeoPageSuggestionRepository:
    ID_PREFIX = "psg"

    def _filtered(self, site_id: str, f: PageSuggestionFilter) -> Select:
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

    def _where_id(self, site_id: str, suggestion_id: str):
        return (SeoPageSuggestion.site_id == site_id, SeoPageSuggestion.id == suggestion_id)

    async def get(
        self, db: AsyncSession, site_id: str, suggestion_id: str
    ) -> PageSuggestionRecord | None:
        row = (
            await db.execute(
                select(SeoPageSuggestion).where(*self._where_id(site_id, suggestion_id))
            )
        ).scalar_one_or_none()
        return None if row is None else PageSuggestionRecord.model_validate(row)

    async def find(
        self, db: AsyncSession, site_id: str, action: str, page_id: str | None, topic_key: str
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

    async def create(
        self, db: AsyncSession, user_id: str, site_id: str, job_id: str, values: dict[str, Any]
    ) -> str:
        at = now()
        row = SeoPageSuggestion(
            id=uid(self.ID_PREFIX),
            user_id=user_id,
            site_id=site_id,
            job_id=job_id,
            created_at=at,
            updated_at=at,
            **values,
        )
        db.add(row)
        await db.flush()
        return row.id

    async def update(
        self, db: AsyncSession, site_id: str, suggestion_id: str, patch: dict[str, Any]
    ) -> None:
        await db.execute(
            update(SeoPageSuggestion)
            .where(*self._where_id(site_id, suggestion_id))
            .values(**patch, updated_at=now())
        )

    async def revive(
        self,
        db: AsyncSession,
        site_id: str,
        suggestion_id: str,
        job_id: str,
        values: dict[str, Any],
    ) -> None:
        await db.execute(
            update(SeoPageSuggestion)
            .where(*self._where_id(site_id, suggestion_id))
            .values(
                **{**values, "state": "draft"},
                job_id=job_id,
                confidence=None,
                score=None,
                pair_id=None,
                verified_at=None,
                updated_at=now(),
            )
        )

    async def touch(
        self,
        db: AsyncSession,
        site_id: str,
        suggestion_id: str,
        strategy: str,
        evidence: dict[str, Any],
    ) -> None:
        await db.execute(
            update(SeoPageSuggestion)
            .where(*self._where_id(site_id, suggestion_id))
            .values(
                strategies=func.array_append(
                    func.array_remove(SeoPageSuggestion.strategies, strategy), strategy
                ),
                evidence=evidence,
                updated_at=now(),
            )
        )

    async def link_pair(
        self, db: AsyncSession, site_id: str, first_id: str, second_id: str
    ) -> None:
        await db.execute(
            update(SeoPageSuggestion)
            .where(*self._where_id(site_id, first_id))
            .values(pair_id=second_id)
        )
        await db.execute(
            update(SeoPageSuggestion)
            .where(*self._where_id(site_id, second_id))
            .values(pair_id=first_id)
        )

    async def pair_ids(self, db: AsyncSession, site_id: str, suggestion_id: str) -> list[str]:
        rows = await db.execute(
            select(SeoPageSuggestion.id).where(
                SeoPageSuggestion.site_id == site_id,
                (SeoPageSuggestion.id == suggestion_id)
                | (SeoPageSuggestion.pair_id == suggestion_id),
            )
        )
        ids = set(rows.scalars().all())
        found = await self.get(db, site_id, suggestion_id)
        if found is not None and found.pair_id:
            ids.add(found.pair_id)
        return list(ids)

    async def set_state(
        self,
        db: AsyncSession,
        site_id: str,
        ids: list[str],
        state: str,
        only_from: tuple[str, ...],
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
            .values(state=state, updated_at=now())
        )
        return result.rowcount or 0

    async def close(self, db: AsyncSession, site_id: str, ids: list[str], state: str) -> int:
        if not ids:
            return 0
        at = now()
        result = await db.execute(
            update(SeoPageSuggestion)
            .where(
                SeoPageSuggestion.site_id == site_id,
                SeoPageSuggestion.id.in_(ids),
                SeoPageSuggestion.state.in_(OPEN_STATES),
            )
            .values(state=state, verified_at=at, updated_at=at)
        )
        return result.rowcount or 0

    async def summary(self, db: AsyncSession, site_id: str) -> PageSuggestionSummary:
        rows = await db.execute(
            select(SeoPageSuggestion.action, SeoPageSuggestion.state, func.count())
            .where(SeoPageSuggestion.site_id == site_id)
            .group_by(SeoPageSuggestion.action, SeoPageSuggestion.state)
        )
        summary = PageSuggestionSummary()
        for action, state, total in rows.tuples():
            getattr(summary, action)[state] = int(total)
        return summary

    async def list_open(self, db: AsyncSession, site_id: str) -> list[PageSuggestionRecord]:
        rows = (
            await db.execute(
                select(SeoPageSuggestion).where(
                    SeoPageSuggestion.site_id == site_id,
                    SeoPageSuggestion.state.in_(OPEN_STATES),
                )
            )
        ).scalars()
        return [PageSuggestionRecord.model_validate(r) for r in rows]

    async def list_for_job(
        self,
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

    async def topic_keys(self, db: AsyncSession, site_id: str, ids: list[str]) -> list[str]:
        if not ids:
            return []
        rows = await db.execute(
            select(SeoPageSuggestion.topic_key)
            .distinct()
            .where(SeoPageSuggestion.site_id == site_id, SeoPageSuggestion.id.in_(ids))
        )
        return list(rows.scalars().all())

    async def job_topic_keys(
        self, db: AsyncSession, site_id: str, job_id: str, states: tuple[str, ...]
    ) -> list[str]:
        rows = await db.execute(
            select(SeoPageSuggestion.topic_key)
            .where(
                SeoPageSuggestion.site_id == site_id,
                SeoPageSuggestion.job_id == job_id,
                SeoPageSuggestion.state.in_(states),
            )
            .order_by(SeoPageSuggestion.search_score.desc().nulls_last())
        )
        return list(rows.scalars().all())

    async def list_for_site(self, db: AsyncSession, site_id: str) -> list[PageSuggestionRecord]:
        rows = (
            await db.execute(
                select(SeoPageSuggestion)
                .where(SeoPageSuggestion.site_id == site_id)
                .order_by(SeoPageSuggestion.created_at.desc())
            )
        ).scalars()
        return [PageSuggestionRecord.model_validate(r) for r in rows]

    async def list(
        self, db: AsyncSession, site_id: str, f: PageSuggestionFilter, paging: PaginationParams
    ) -> PaginatedApiResponse[PageSuggestionRecord]:
        return await page(
            db,
            self._filtered(site_id, f),
            (SeoPageSuggestion.score.desc().nulls_last(), SeoPageSuggestion.seq.desc()),
            paging,
            PageSuggestionRecord,
        )


seo_page_suggestions = SeoPageSuggestionRepository()
