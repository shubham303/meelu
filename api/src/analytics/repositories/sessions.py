from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics.models.analytics_sessions import AnalyticsSession
from src.analytics.schemas import AnalyticsSessionRecord
from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService


class AnalyticsSessionRepository:
    async def list_all(
        self, db: AsyncSession, user_id: str, site_id: str
    ) -> list[AnalyticsSessionRecord]:
        rows = (await db.execute(self._query(user_id, site_id))).scalars().all()
        return [AnalyticsSessionRecord.model_validate(r) for r in rows]

    async def page(
        self, db: AsyncSession, user_id: str, site_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[AnalyticsSessionRecord]:
        return await PaginationService.paginate_query(
            db, self._query(user_id, site_id), paging.page, paging.page_size, AnalyticsSessionRecord
        )

    async def count(self, db: AsyncSession, user_id: str, site_id: str) -> int:
        return (
            await db.execute(
                select(func.count())
                .select_from(AnalyticsSession)
                .where(AnalyticsSession.user_id == user_id, AnalyticsSession.site_id == site_id)
            )
        ).scalar_one()

    async def get(
        self, db: AsyncSession, user_id: str, site_id: str, session_id: str
    ) -> AnalyticsSessionRecord | None:
        row = (
            await db.execute(
                select(AnalyticsSession).where(
                    AnalyticsSession.user_id == user_id,
                    AnalyticsSession.site_id == site_id,
                    AnalyticsSession.id == session_id,
                )
            )
        ).scalar_one_or_none()
        return None if row is None else AnalyticsSessionRecord.model_validate(row)

    async def create(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        title: str,
        about: str,
        session_key: str | None,
    ) -> AnalyticsSessionRecord:
        now = datetime.now(UTC)
        row = AnalyticsSession(
            id=uid("ssn"),
            user_id=user_id,
            site_id=site_id,
            title=title,
            about=about,
            session_key=session_key,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.flush()
        return AnalyticsSessionRecord.model_validate(row)

    async def update(
        self, db: AsyncSession, session_id: str, values: dict[str, Any]
    ) -> AnalyticsSessionRecord:
        row = (
            await db.execute(
                update(AnalyticsSession)
                .where(AnalyticsSession.id == session_id)
                .values(**values, updated_at=datetime.now(UTC))
                .returning(AnalyticsSession)
            )
        ).scalar_one()
        return AnalyticsSessionRecord.model_validate(row)

    async def delete(self, db: AsyncSession, session_id: str) -> None:
        await db.execute(delete(AnalyticsSession).where(AnalyticsSession.id == session_id))
        await db.flush()

    def _query(self, user_id: str, site_id: str) -> Select:
        return (
            select(AnalyticsSession)
            .where(AnalyticsSession.user_id == user_id, AnalyticsSession.site_id == site_id)
            .order_by(AnalyticsSession.seq.desc())
        )


analytics_sessions = AnalyticsSessionRepository()
