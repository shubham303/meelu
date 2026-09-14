from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from src.core.schemas import parse_datetime

HOUR_SECONDS = 3600


def floor_to_hour(moment: datetime, tz: str) -> datetime:
    local = moment.astimezone(ZoneInfo(tz))
    return local.replace(minute=0, second=0, microsecond=0).astimezone(UTC)


def hour_floor(value: Any, tz: str) -> datetime:
    if isinstance(value, datetime):
        moment = value if value.tzinfo else value.replace(tzinfo=UTC)
    else:
        try:
            moment = parse_datetime(str(value), "scheduledAt")
        except HTTPException:
            raise HTTPException(400, "scheduledAt must be a valid ISO date-time.")
    return floor_to_hour(moment, tz)


WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def short_when(moment: datetime, tz: str) -> str:
    local = moment.astimezone(ZoneInfo(tz))
    hour = local.hour % 12 or 12
    meridiem = "AM" if local.hour < 12 else "PM"
    return f"{WEEKDAYS[local.weekday()]} {hour} {meridiem}"
