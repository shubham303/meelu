from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Pagination query parameters."""

    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=10, ge=1, le=100, description="Items per page")

    def validate(self) -> "PaginationParams":
        """Validate and normalize pagination params."""
        self.page = max(1, self.page)
        self.page_size = min(max(1, self.page_size), 100)
        return self

    @property
    def offset(self) -> int:
        """Calculate offset for database query."""
        return (self.page - 1) * self.page_size
