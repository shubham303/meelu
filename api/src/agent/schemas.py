from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    ok: bool


class BootstrapResult(BaseModel):
    granted: list[str]
    rls: list[str]


class SqlRowsResponse(BaseModel):
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool


class SqlWriteResponse(BaseModel):
    row_count: int
    status: str
