from typing import Any, TypeVar

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from .models import PaginatedApiResponse, PaginationMeta
from .params import PaginationParams

T = TypeVar("T", bound=BaseModel)
ModelT = TypeVar("ModelT", bound=DeclarativeBase)


class PaginationService:
    """Handles pagination logic for list endpoints."""

    @staticmethod
    async def paginate_query(
        db: AsyncSession,
        query,
        page: int = 1,
        page_size: int = 10,
        response_model: type[T] | None = None,
    ) -> PaginatedApiResponse[T]:
        """
                Paginate a SQLAlchemy async query and return paginated response.

                Args:
                    db: SQLAlchemy async session
                    query: SQLAlchemy query object (select statement)
                    page: Page number (1-indexed)
                    page_size: Items per page
                    response_model: Pydantic model for response transformation

                Returns:
                    PaginatedApiResponse with data and pagination metadata

                Example:
        ```python
                    query = select(AgentPlan).where(AgentPlan.user_id == user_id)
                    result = await PaginationService.paginate_query(
                        db,
                        query,
                        page=1,
                        page_size=10,
                        response_model=AgentPlanApiResponse,
                    )
        ```
        """
        # Validate inputs
        params = PaginationParams(page=page, page_size=page_size).validate()

        # Get total count
        count_query = select(func.count()).select_from(query.order_by(None).subquery())
        total = (await db.execute(count_query)).scalar_one()

        # Calculate pagination metadata
        total_pages = (total + params.page_size - 1) // params.page_size

        # Fetch paginated data
        paginated_query = query.offset(params.offset).limit(params.page_size)
        result = await db.execute(paginated_query)
        items = result.scalars().all()

        # Transform to response model if provided
        data = []
        if response_model:
            for item in items:
                data.append(response_model.model_validate(item))
        else:
            data = items

        pagination = PaginationMeta(
            page=params.page,
            page_size=params.page_size,
            total=total,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_prev=params.page > 1,
        )

        return PaginatedApiResponse(data=data, pagination=pagination)

    @staticmethod
    async def paginate_raw(
        db: AsyncSession,
        query,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[Any], PaginationMeta]:
        """
        Paginate raw query results without transformation.

        Args:
            db: SQLAlchemy async session
            query: SQLAlchemy query object
            page: Page number (1-indexed)
            page_size: Items per page

        Returns:
            Tuple of (items, pagination_meta)
        """
        params = PaginationParams(page=page, page_size=page_size).validate()

        # Get total count
        count_query = select(func.count()).select_from(query.order_by(None).subquery())
        total = (await db.execute(count_query)).scalar_one()

        # Calculate metadata
        total_pages = (total + params.page_size - 1) // params.page_size

        # Fetch paginated data
        paginated_query = query.offset(params.offset).limit(params.page_size)
        result = await db.execute(paginated_query)
        items = result.scalars().all()

        pagination = PaginationMeta(
            page=params.page,
            page_size=params.page_size,
            total=total,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_prev=params.page > 1,
        )

        return items, pagination

    @staticmethod
    def build_pagination_meta(
        total: int,
        page: int,
        page_size: int,
    ) -> PaginationMeta:
        """
        Build pagination metadata from totals.

        Useful when you already have total count from another source.

        Args:
            total: Total number of items
            page: Current page (1-indexed)
            page_size: Items per page

        Returns:
            PaginationMeta object
        """
        params = PaginationParams(page=page, page_size=page_size).validate()
        total_pages = (total + params.page_size - 1) // params.page_size

        return PaginationMeta(
            page=params.page,
            page_size=params.page_size,
            total=total,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_prev=params.page > 1,
        )
