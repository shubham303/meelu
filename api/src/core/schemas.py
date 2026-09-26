from datetime import UTC, datetime
from typing import Annotated, Any, ClassVar

from fastapi import HTTPException
from pydantic import (
    BaseModel,
    ConfigDict,
    PlainSerializer,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    model_serializer,
)
from pydantic.alias_generators import to_camel
from sqlalchemy import DateTime, inspect

INTERNAL = frozenset({"user_id", "seq", "key_hash"})


def js_iso(dt: datetime) -> str:
    dt = dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)
    return f"{dt:%Y-%m-%dT%H:%M:%S}.{dt.microsecond // 1000:03d}Z"


def parse_datetime(value: str, key: str) -> datetime:
    raw = value.strip()
    if raw.endswith(("Z", "z")):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        raise HTTPException(400, f"{key} must be a date or ISO timestamp.")
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


JsDateTime = Annotated[datetime, PlainSerializer(js_iso, return_type=str)]


class RequestModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="ignore")


class EntityModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

    keep_null: ClassVar[frozenset[str]] = frozenset()

    @model_serializer(mode="wrap")
    def _serialize(
        self, handler: SerializerFunctionWrapHandler, info: SerializationInfo
    ) -> dict[str, Any]:
        data = handler(self)
        if info.mode != "json":
            return data
        return {
            k: v
            for k, v in data.items()
            if v is not None or k in self.keep_null or to_camel(k) in self.keep_null
        }


def to_row(model: type, data: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for column in inspect(model).columns:
        key = column.key
        if key in INTERNAL:
            continue
        camel = to_camel(key)
        if camel not in data:
            continue
        value = data[camel]
        if isinstance(column.type, DateTime) and isinstance(value, str):
            value = parse_datetime(value, camel)
        out[key] = value
    return out
