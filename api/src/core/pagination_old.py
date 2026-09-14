"""
⚠️ DEPRECATED: This module is deprecated and will be removed.

Use `src.core.pagination` instead for pagination utilities.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException
from starlette.datastructures import QueryParams
from starlette.requests import Request

from src.core.schemas import parse_datetime


class QueryReader:
    def __init__(self, params: QueryParams):
        self.raw = params

    def str(self, key: str) -> str | None:
        value = self.raw.get(key)
        if value is None:
            return None
        value = value.strip()
        return value or None

    def num(self, key: str) -> float | None:
        value = self.str(key)
        if value is None:
            return None
        try:
            n = float(value)
        except ValueError:
            raise HTTPException(400, f"{key} must be a number.")
        if not math.isfinite(n):
            raise HTTPException(400, f"{key} must be a number.")
        return n

    def int(self, key: str) -> int | None:
        n = self.num(key)
        return None if n is None else math.trunc(n)

    def bool(self, key: str) -> bool | None:
        value = self.str(key)
        if value is None:
            return None
        value = value.lower()
        if value in ("true", "1"):
            return True
        if value in ("false", "0"):
            return False
        raise HTTPException(400, f"{key} must be true or false.")

    def list(self, key: str) -> list[str] | None:
        parts = [p.strip() for v in self.raw.getlist(key) for p in v.split(",")]
        parts = [p for p in parts if p]
        return parts or None

    def date(self, key: str) -> datetime | None:
        value = self.str(key)
        if value is None:
            return None
        try:
            return parse_datetime(value, key)
        except HTTPException:
            raise HTTPException(400, f"{key} must be a date or ISO timestamp.")

    def one(self, key: str, allowed: Sequence[str]) -> str | None:
        value = self.str(key)
        if value is None:
            return None
        if value not in allowed:
            raise HTTPException(400, f"{key} must be one of {', '.join(allowed)}.")
        return value


def query(request: Request) -> QueryReader:
    return QueryReader(request.query_params)


@dataclass
class Pagination:
    limit: int | None
    offset: int | None


def pagination(request: Request) -> Pagination:
    q = query(request)
    return Pagination(limit=q.int("limit"), offset=q.int("offset"))
