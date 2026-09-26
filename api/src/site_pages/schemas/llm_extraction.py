from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.schemas import EntityModel, RequestModel

PAGE_TYPES = ("money", "hub", "informational", "support", "company", "legal", "utility")

PageType = Literal[PAGE_TYPES]


class PageLlmExtractionFields(RequestModel):
    page_type: PageType | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)


class PageLlmExtractionCreateRequest(PageLlmExtractionFields):
    page_id: str
    extracted_from_hash: str | None = None
    model: str | None = None
    error: str | None = None

    def values(self) -> dict[str, Any]:
        return self.model_dump(exclude={"page_id"})


class PageLlmExtractionPageTypeRequest(RequestModel):
    page_type: PageType


class PageLlmExtractionListQuery(RequestModel):
    page_type: PageType | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    def paging(self) -> PaginationParams:
        return PaginationParams(page=self.page, page_size=self.page_size).validate()


class PageLlmExtractionRecord(EntityModel):
    id: str
    site_id: str
    page_id: str
    page_type: str | None
    confidence: float | None
    extracted_from_hash: str | None
    model: str | None
    error: str | None
    extracted_at: datetime
    created_at: datetime
    updated_at: datetime


class PendingPageRecord(EntityModel):
    id: str
    url: str
    title: str | None
    meta_description: str | None
    content_hash: str | None
    body_text: str | None


class ExtractionState(EntityModel):
    page_type: str | None
    extracted_from_hash: str | None
    error: str | None
    extract_attempts: int


class PageLlmExtractionStatsRecord(EntityModel):
    eligible: int
    extracted: int
    pending: int


class PageLlmExtractionResponse(PageLlmExtractionRecord):
    pass


class PageLlmExtractionListResponse(PaginatedApiResponse[PageLlmExtractionResponse]):
    pass


class PageLlmExtractionStatsResponse(EntityModel):
    stats: PageLlmExtractionStatsRecord


class PageLlmExtractionDeleteResponse(EntityModel):
    id: str
