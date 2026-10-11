from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics.models.analytics_chat_messages import AnalyticsChatMessage
from src.analytics.models.analytics_chats import AnalyticsChat
from src.analytics.schemas import (
    AnalyticsChatMessageRecord,
    AnalyticsChatRecord,
    AnalyticsChatSummaryRecord,
)
from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService


class AnalyticsChatRepository:
    async def page_summaries(
        self, db: AsyncSession, user_id: str, site_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[AnalyticsChatSummaryRecord]:
        conds = [AnalyticsChat.user_id == user_id, AnalyticsChat.site_id == site_id]
        total = (
            await db.execute(select(func.count()).select_from(AnalyticsChat).where(*conds))
        ).scalar_one()
        result = await db.execute(
            select(AnalyticsChat.id, AnalyticsChat.title, AnalyticsChat.updated_at)
            .where(*conds)
            .order_by(AnalyticsChat.updated_at.desc(), AnalyticsChat.seq.desc())
            .offset(paging.offset)
            .limit(paging.page_size)
        )
        return PaginatedApiResponse[AnalyticsChatSummaryRecord](
            data=[AnalyticsChatSummaryRecord.model_validate(r) for r in result.mappings().all()],
            pagination=PaginationService.build_pagination_meta(
                total, paging.page, paging.page_size
            ),
        )

    async def get(
        self, db: AsyncSession, user_id: str, site_id: str, chat_id: str
    ) -> AnalyticsChatRecord | None:
        row = (
            await db.execute(
                select(AnalyticsChat).where(
                    AnalyticsChat.user_id == user_id,
                    AnalyticsChat.site_id == site_id,
                    AnalyticsChat.id == chat_id,
                )
            )
        ).scalar_one_or_none()
        return None if row is None else AnalyticsChatRecord.model_validate(row)

    async def create(
        self, db: AsyncSession, user_id: str, site_id: str, title: str
    ) -> AnalyticsChatRecord:
        now = datetime.now(UTC)
        row = AnalyticsChat(
            id=uid("chat"),
            user_id=user_id,
            site_id=site_id,
            title=title,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        await db.flush()
        return AnalyticsChatRecord.model_validate(row)

    async def update(
        self, db: AsyncSession, chat_id: str, values: dict[str, Any]
    ) -> AnalyticsChatRecord:
        row = (
            await db.execute(
                update(AnalyticsChat)
                .where(AnalyticsChat.id == chat_id)
                .values(**values, updated_at=datetime.now(UTC))
                .returning(AnalyticsChat)
            )
        ).scalar_one()
        return AnalyticsChatRecord.model_validate(row)

    async def delete(self, db: AsyncSession, chat_id: str) -> None:
        await db.execute(delete(AnalyticsChat).where(AnalyticsChat.id == chat_id))
        await db.flush()


class AnalyticsChatMessageRepository:
    async def page(
        self, db: AsyncSession, chat_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[AnalyticsChatMessageRecord]:
        cond = AnalyticsChatMessage.chat_id == chat_id
        total = (
            await db.execute(select(func.count()).select_from(AnalyticsChatMessage).where(cond))
        ).scalar_one()
        result = await db.execute(
            select(
                AnalyticsChatMessage.id,
                AnalyticsChatMessage.chat_id,
                AnalyticsChatMessage.role,
                AnalyticsChatMessage.text,
                AnalyticsChatMessage.created_at,
            )
            .where(cond)
            .order_by(AnalyticsChatMessage.seq.desc())
            .offset(paging.offset)
            .limit(paging.page_size)
        )
        return PaginatedApiResponse[AnalyticsChatMessageRecord](
            data=[AnalyticsChatMessageRecord.model_validate(r) for r in result.mappings().all()],
            pagination=PaginationService.build_pagination_meta(
                total, paging.page, paging.page_size
            ),
        )

    async def add_many(
        self, db: AsyncSession, chat_id: str, messages: list[tuple[str, str]]
    ) -> list[AnalyticsChatMessageRecord]:
        now = datetime.now(UTC)
        rows = [
            AnalyticsChatMessage(
                id=uid("msg"), chat_id=chat_id, role=role, text=text, created_at=now, updated_at=now
            )
            for role, text in messages
        ]
        for row in rows:
            db.add(row)
            await db.flush()
        return [AnalyticsChatMessageRecord.model_validate(r) for r in rows]


analytics_chats = AnalyticsChatRepository()
analytics_chat_messages = AnalyticsChatMessageRepository()
