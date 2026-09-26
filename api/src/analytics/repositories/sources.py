from datetime import UTC, datetime

from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics.models.analytics_sources import AnalyticsSource
from src.analytics.schemas import AnalyticsSourceRecord
from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService


class AnalyticsSourceRepository:
    async def list_all(
        self, db: AsyncSession, user_id: str, site_id: str
    ) -> list[AnalyticsSourceRecord]:
        rows = (await db.execute(self._query(user_id, site_id))).scalars().all()
        return [AnalyticsSourceRecord.model_validate(r) for r in rows]

    async def page_by_session(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        session_id: str,
        paging: PaginationParams,
    ) -> PaginatedApiResponse[AnalyticsSourceRecord]:
        return await PaginationService.paginate_query(
            db,
            self._query(user_id, site_id, session_id),
            paging.page,
            paging.page_size,
            AnalyticsSourceRecord,
        )

    async def get(
        self, db: AsyncSession, user_id: str, site_id: str, source_id: str
    ) -> AnalyticsSourceRecord | None:
        row = (
            await db.execute(
                select(AnalyticsSource).where(
                    AnalyticsSource.user_id == user_id,
                    AnalyticsSource.site_id == site_id,
                    AnalyticsSource.id == source_id,
                )
            )
        ).scalar_one_or_none()
        return None if row is None else AnalyticsSourceRecord.model_validate(row)

    async def create(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        session_id: str,
        name: str,
        file_path: str | None,
    ) -> AnalyticsSourceRecord:
        now = datetime.now(UTC)
        row = AnalyticsSource(
            id=uid("dsrc"),
            user_id=user_id,
            site_id=site_id,
            session_id=session_id,
            name=name,
            file_path=file_path,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.flush()
        return AnalyticsSourceRecord.model_validate(row)

    async def delete(self, db: AsyncSession, source_id: str) -> None:
        await db.execute(delete(AnalyticsSource).where(AnalyticsSource.id == source_id))
        await db.flush()

    def _query(self, user_id: str, site_id: str, session_id: str | None = None) -> Select:
        query = select(AnalyticsSource).where(
            AnalyticsSource.user_id == user_id, AnalyticsSource.site_id == site_id
        )
        if session_id is not None:
            query = query.where(AnalyticsSource.session_id == session_id)
        return query.order_by(AnalyticsSource.seq.desc())


analytics_sources = AnalyticsSourceRepository()
