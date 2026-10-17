from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.analytics.repositories.chats import analytics_chat_messages, analytics_chats
from src.analytics.schemas import (
    AnalyticsChatCreateRequest,
    AnalyticsChatMessageRecord,
    AnalyticsChatMessagesCreateRequest,
    AnalyticsChatRecord,
    AnalyticsChatSummaryRecord,
    AnalyticsChatUpdateRequest,
)
from src.core.pagination import PaginatedApiResponse, PaginationParams


class AnalyticsService:
    async def list_chats(
        self, db: AsyncSession, user_id: str, site_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[AnalyticsChatSummaryRecord]:
        return await analytics_chats.page_summaries(db, user_id, site_id, paging)

    async def create_chat(
        self, db: AsyncSession, user_id: str, site_id: str, body: AnalyticsChatCreateRequest
    ) -> AnalyticsChatRecord:
        return await analytics_chats.create(db, user_id, site_id, body.title)

    async def get_chat(
        self, db: AsyncSession, user_id: str, site_id: str, chat_id: str
    ) -> AnalyticsChatRecord:
        record = await analytics_chats.get(db, user_id, site_id, chat_id)
        if record is None:
            raise HTTPException(404, "Not found")
        return record

    async def update_chat(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        chat_id: str,
        body: AnalyticsChatUpdateRequest,
    ) -> AnalyticsChatRecord:
        values = body.changes()
        if not values:
            raise HTTPException(400, "Nothing to update — send `title` and/or `sdkSessionId`.")
        record = await self.get_chat(db, user_id, site_id, chat_id)
        return await analytics_chats.update(db, record.id, values)

    async def delete_chat(
        self, db: AsyncSession, user_id: str, site_id: str, chat_id: str
    ) -> AnalyticsChatRecord:
        record = await self.get_chat(db, user_id, site_id, chat_id)
        await analytics_chats.delete(db, record.id)
        return record

    async def list_messages(
        self, db: AsyncSession, user_id: str, site_id: str, chat_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[AnalyticsChatMessageRecord]:
        record = await self.get_chat(db, user_id, site_id, chat_id)
        return await analytics_chat_messages.page(db, record.id, paging)

    async def add_messages(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        chat_id: str,
        body: AnalyticsChatMessagesCreateRequest,
    ) -> list[AnalyticsChatMessageRecord]:
        record = await self.get_chat(db, user_id, site_id, chat_id)
        added = await analytics_chat_messages.add_many(
            db, record.id, [(m.role, m.text) for m in body.messages]
        )
        await analytics_chats.update(db, record.id, {})
        return added


analytics_service = AnalyticsService()
