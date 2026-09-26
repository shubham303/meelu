from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.providers.repository import provider_calls
from src.providers.schemas import ProviderCallResponse


class ProviderCallService:
    async def list(
        self, db: AsyncSession, user_id: str, paging: PaginationParams, domain: str | None
    ) -> PaginatedApiResponse[ProviderCallResponse]:
        return await provider_calls.list_for_user(db, user_id, paging, domain)


provider_call_service = ProviderCallService()
