from collections.abc import Sequence
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src.content.schemas.channels import SiteChannelRecord
from src.content.schemas.pieces import ContentPieceRecord
from src.core.schemas import EntityModel

HOUR = timedelta(hours=1)
OCCUPYING = ("draft", "blocked", "scheduled", "posted")


class Conflict(EntityModel):
    piece: ContentPieceRecord
    reason: str


def occupying(
    pieces: Sequence[ContentPieceRecord], except_id: str | None = None
) -> list[ContentPieceRecord]:
    return [
        p
        for p in pieces
        if p.scheduled_at is not None and p.status in OCCUPYING and p.id != except_id
    ]


def find_conflict(
    siblings: Sequence[ContentPieceRecord], channel: SiteChannelRecord, at: datetime
) -> Conflict | None:
    for p in siblings:
        if p.scheduled_at == at:
            return Conflict(piece=p, reason="slot")
    if channel.min_gap_hours > 0:
        gap = timedelta(hours=channel.min_gap_hours)
        for p in siblings:
            if abs(p.scheduled_at - at) < gap:
                return Conflict(piece=p, reason="gap")
    return None


def in_window(channel: SiteChannelRecord, at: datetime) -> bool:
    windows = channel.posting_windows
    if not windows:
        return True
    local = at.astimezone(ZoneInfo(channel.timezone))
    return any(local.weekday() in w.days and int(w.time[:2]) == local.hour for w in windows)


def open_slots(
    siblings: Sequence[ContentPieceRecord],
    channel: SiteChannelRecord,
    start: datetime,
    end: datetime,
) -> list[datetime]:
    free: list[datetime] = []
    moment = start
    while moment < end:
        if in_window(channel, moment) and find_conflict(siblings, channel, moment) is None:
            free.append(moment)
        moment += HOUR
    return free
