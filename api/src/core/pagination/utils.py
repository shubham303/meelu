from fastapi import Query

from .params import PaginationParams


def get_pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
) -> PaginationParams:
    """
    FastAPI dependency for extracting pagination parameters from query string.

    Usage:
        @app.get("/items")
        async def list_items(
            pagination: PaginationParams = Depends(get_pagination_params),
        ):
            ...
    """
    return PaginationParams(page=page, page_size=page_size).validate()
