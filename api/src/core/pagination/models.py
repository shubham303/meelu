from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(..., ge=1, le=100, description="Items per page")
    total: int = Field(..., ge=0, description="Total number of items")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    has_next: bool = Field(..., description="Whether there's a next page")
    has_prev: bool = Field(..., description="Whether there's a previous page")

    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "page_size": 10,
                "total": 100,
                "total_pages": 10,
                "has_next": True,
                "has_prev": False,
            }
        }


class PaginatedApiResponse(BaseModel, Generic[T]):
    """Generic paginated API response wrapper."""

    data: list[T] = Field(..., description="List of items")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "data": [],
                "pagination": {
                    "page": 1,
                    "page_size": 10,
                    "total": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_prev": False,
                },
            }
        }
