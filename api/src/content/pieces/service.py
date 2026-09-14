import re
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.content.channels import service as channels_service
from src.content.checks import is_blocked, run_checks
from src.content.pieces import repository as repo
from src.content.pieces.media import resolve_media
from src.content.pieces.scheduling import find_conflict, occupying, open_slots
from src.content.platform_seeds import SEEDS_BY_KEY
from src.content.schemas.channels import SiteChannelRecord
from src.content.schemas.pieces import (
    PIECE_STATUSES,
    ContentFreeSlotsResponse,
    ContentPieceCountsResponse,
    ContentPieceCreateRequest,
    ContentPieceMarkdownResult,
    ContentPieceRecord,
    ContentPieceUpdateRequest,
    PieceCheck,
    PieceMediaResult,
    TakenSlot,
)
from src.content.zoned import hour_floor, short_when
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.core.schemas import js_iso

POSTED_IS_HUMAN = (
    "Only a person can mark a piece as posted — nobody but them can see what the "
    "channel did with it. Leave it as a draft for them, or publish it through "
    "the Publish step and let the status follow."
)
SCHEDULED_IS_SYSTEM = (
    "`scheduled` isn't a status you set — it means the publisher holds the post until its "
    "slot. Publish it through the Publish step and the status follows by itself."
)
SCHEDULED_IS_LOCKED = (
    "This piece is scheduled with the publisher. Cancel the schedule first — that "
    "pulls it back and returns it to `draft`."
)
POSTED_IS_FINAL = "A posted piece is final. Clone it into a new piece instead."


def word_count(markdown: str | None) -> int:
    return len(re.findall(r"\S+", markdown or ""))


def truncate(value: str, limit: int = 60) -> str:
    return f"{value[:limit]}…" if len(value) > limit else value


def valid_status(value: str) -> str:
    if value not in PIECE_STATUSES:
        raise HTTPException(400, f"Invalid status. Allowed values: {', '.join(PIECE_STATUSES)}.")
    return value


def media_count(media_source: str) -> int:
    return 0 if media_source == "none" else 1


def checks_for(channel_key: str, body: str, media_source: str) -> list[PieceCheck]:
    return run_checks(
        SEEDS_BY_KEY[channel_key], body, media_count=media_count(media_source), site_host=None
    )


def _checks_values(checks: list[PieceCheck]) -> list[dict[str, Any]]:
    return [c.model_dump() for c in checks]


def _status_after_checks(status: str, checks: list[PieceCheck], *, requested: bool) -> str:
    blocked = is_blocked(checks)
    if status == "scheduled" and blocked:
        if requested:
            raise HTTPException(400, next(c.message for c in checks if c.level == "block"))
        return "blocked"
    if status in ("draft", "blocked"):
        return "blocked" if blocked else "draft"
    return status


async def assert_schedulable(
    db: AsyncSession,
    site_id: str,
    channel: SiteChannelRecord,
    scheduled_at: datetime,
    except_id: str | None = None,
) -> None:
    siblings = occupying(await repo.list_on_channel(db, site_id, channel.channel_key), except_id)
    conflict = find_conflict(siblings, channel, scheduled_at)
    if conflict is None:
        return
    label = SEEDS_BY_KEY[channel.channel_key].label
    if conflict.reason == "slot":
        raise HTTPException(409, f'That slot already holds "{conflict.piece.title}".')
    when = short_when(conflict.piece.scheduled_at, channel.timezone)
    raise HTTPException(
        409,
        f'Too close to "{conflict.piece.title}" ({when}). This site keeps '
        f"{channel.min_gap_hours}h between {label} posts.",
    )


async def free_slots(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    channel_key: str,
    since: str | None,
    until: str | None,
) -> ContentFreeSlotsResponse:
    channel = await channels_service.require_enabled(db, user_id, site_id, channel_key)
    start = hour_floor(since or datetime.now(UTC), channel.timezone)
    end = hour_floor(until, channel.timezone) if until else start + timedelta(days=14)
    if end <= start:
        raise HTTPException(400, "`to` must be after `from`.")
    if end - start > timedelta(days=60):
        raise HTTPException(400, "Range too wide — ask for 60 days or less.")

    siblings = occupying(await repo.list_on_channel(db, site_id, channel_key))
    free = open_slots(siblings, channel, start, end)
    taken = [
        TakenSlot(scheduled_at=p.scheduled_at, title=p.title, status=p.status)
        for p in siblings
        if start <= p.scheduled_at < end
    ]
    return ContentFreeSlotsResponse(
        channel_key=channel_key,
        timezone=channel.timezone,
        min_gap_hours=channel.min_gap_hours,
        posting_windows=channel.posting_windows,
        from_=start,
        to=end,
        free=free,
        taken=taken,
    )


async def list_pieces(
    db: AsyncSession,
    site_id: str,
    paging: PaginationParams,
    *,
    status: str | None = None,
    channel_key: str | None = None,
    search: str | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
) -> PaginatedApiResponse[ContentPieceRecord]:
    if status is not None:
        valid_status(status)
    if channel_key is not None and channel_key not in SEEDS_BY_KEY:
        raise HTTPException(400, f'Unknown channel "{channel_key}".')
    return await repo.list_pieces(
        db,
        site_id,
        paging,
        status=status,
        channel_key=channel_key,
        search=search,
        since=since,
        until=until,
    )


async def counts(db: AsyncSession, site_id: str) -> ContentPieceCountsResponse:
    found = await repo.counts_by_status(db, site_id)
    return ContentPieceCountsResponse(
        by_status={s: found.by_status.get(s, 0) for s in PIECE_STATUSES}
    )


async def get_piece(db: AsyncSession, site_id: str, piece_id: str) -> ContentPieceRecord:
    piece = await repo.get_piece(db, site_id, piece_id)
    if piece is None:
        raise HTTPException(404, "Not found")
    return piece


async def create_piece(
    db: AsyncSession, user_id: str, site_id: str, body: ContentPieceCreateRequest, *, actor: str
) -> ContentPieceRecord:
    source: ContentPieceRecord | None = None
    if body.clone_from_piece_id:
        source = await repo.get_piece(db, site_id, body.clone_from_piece_id)
        if source is None:
            raise HTTPException(404, "The piece to clone from doesn't exist.")

    channel_key = body.channel_key or (source.channel_key if source else None)
    if not channel_key:
        raise HTTPException(400, "channelKey is required.")
    if channel_key not in SEEDS_BY_KEY:
        raise HTTPException(400, f'Unknown channel "{channel_key}".')
    channel = await channels_service.require_enabled(db, user_id, site_id, channel_key)

    title = body.title or (f"{source.title} (copy)" if source else None)
    if not title:
        raise HTTPException(400, "title is required.")
    text = (
        body.body_markdown
        if body.body_markdown is not None
        else (source.body_markdown if source else "")
    )

    status = body.status or "draft"
    if status == "posted" and actor == "agent":
        raise HTTPException(400, POSTED_IS_HUMAN)
    if status in ("scheduled", "failed") and actor != "system":
        raise HTTPException(400, SCHEDULED_IS_SYSTEM)

    media = await resolve_media(db, user_id, body)
    if media is None:
        media = (
            PieceMediaResult.model_validate(source.model_dump())
            if source and source.channel_key == channel_key
            else PieceMediaResult()
        )
    checks = checks_for(channel_key, text, media.media_source)
    status = _status_after_checks(status, checks, requested=body.status is not None)

    scheduled_at = None
    if body.scheduled_at is not None:
        scheduled_at = hour_floor(body.scheduled_at, channel.timezone)
        await assert_schedulable(db, site_id, channel, scheduled_at)

    return await repo.create_piece(
        db,
        user_id,
        site_id,
        {
            **media.model_dump(),
            "title": title,
            "body_markdown": text,
            "channel_key": channel_key,
            "status": status,
            "word_count": word_count(text),
            "checks": _checks_values(checks),
            "scheduled_at": scheduled_at,
            "posted_at": datetime.now(UTC) if status == "posted" else None,
            "posted_url": body.posted_url or None,
            "created_by": actor,
            "source_page_id": body.source_page_id or (source.source_page_id if source else None),
            "parent_piece_id": source.id if source else None,
        },
    )


def assert_transition(existing: str, next_status: str, actor: str) -> None:
    if existing == next_status:
        return
    if existing == "posted" and actor != "system":
        raise HTTPException(400, POSTED_IS_FINAL)
    if next_status == "posted" and actor == "agent":
        raise HTTPException(400, POSTED_IS_HUMAN)
    if next_status in ("scheduled", "failed") and actor != "system":
        raise HTTPException(400, SCHEDULED_IS_SYSTEM)
    if existing == "scheduled" and actor != "system":
        raise HTTPException(400, SCHEDULED_IS_LOCKED)


def summarize(before: ContentPieceRecord, after: ContentPieceRecord) -> str:
    title = truncate(after.title)
    label = SEEDS_BY_KEY[after.channel_key].label
    if before.status != after.status:
        if after.status == "posted":
            return f'Posted "{title}" to {label}'
        if after.status == "scheduled":
            return f'Scheduled "{title}" for {label} at {js_iso(after.scheduled_at)}'
        if after.status == "failed":
            return f'Publishing "{title}" to {label} failed'
        return f'"{title}" ({label}) {before.status} → {after.status}'
    if before.scheduled_at != after.scheduled_at:
        when = js_iso(after.scheduled_at) if after.scheduled_at else "unscheduled"
        return f'Moved "{title}" ({label}) to {when}'
    if before.body_markdown != after.body_markdown or before.title != after.title:
        return f'Edited "{title}" for {label}'
    return f'Updated "{title}" for {label}'


async def update_piece(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    piece_id: str,
    body: ContentPieceUpdateRequest,
    *,
    actor: str,
) -> ContentPieceRecord:
    existing = await get_piece(db, site_id, piece_id)
    channel = await channels_service.get_channel(db, user_id, site_id, existing.channel_key)

    values: dict[str, Any] = {}
    if body.title is not None:
        values["title"] = body.title
    if body.body_markdown is not None:
        values["body_markdown"] = body.body_markdown
        values["word_count"] = word_count(body.body_markdown)
    if body.has("source_page_id"):
        values["source_page_id"] = body.source_page_id or None
    media = await resolve_media(db, user_id, body)
    if media:
        values.update(media.model_dump())
    if body.has("posted_url"):
        values["posted_url"] = body.posted_url
    if actor == "system":
        for key in ("external_post_id", "failure", "posted_at"):
            if body.has(key):
                values[key] = getattr(body, key)

    content_changed = "body_markdown" in values or media is not None
    if content_changed and existing.status in ("scheduled", "posted") and actor != "system":
        raise HTTPException(
            400, SCHEDULED_IS_LOCKED if existing.status == "scheduled" else POSTED_IS_FINAL
        )

    if body.has("scheduled_at"):
        scheduled_at = (
            hour_floor(body.scheduled_at, channel.timezone)
            if body.scheduled_at is not None
            else None
        )
        if scheduled_at != existing.scheduled_at:
            if existing.status == "scheduled" and actor != "system":
                raise HTTPException(
                    409,
                    "This piece is scheduled with the publisher — moving it here would "
                    "leave the calendar saying one time and the post going out at another. "
                    "Reschedule it through the Publish step, which moves both.",
                )
            if scheduled_at is not None:
                await assert_schedulable(db, site_id, channel, scheduled_at, piece_id)
        values["scheduled_at"] = scheduled_at

    next_status = existing.status
    if body.status is not None:
        next_status = body.status
        assert_transition(existing.status, next_status, actor)
        if next_status == "posted":
            values["posted_at"] = body.posted_at or datetime.now(UTC)
        if next_status == "draft":
            values["posted_at"] = None
            if "failure" not in values:
                values["failure"] = None
            if "external_post_id" not in values:
                values["external_post_id"] = None

    if content_changed or next_status in ("draft", "blocked"):
        text = values.get("body_markdown", existing.body_markdown)
        source = str(values.get("media_source", existing.media_source))
        checks = checks_for(existing.channel_key, text, source)
        values["checks"] = _checks_values(checks)
        next_status = _status_after_checks(next_status, checks, requested=body.status is not None)
    values["status"] = next_status

    return await repo.update_piece(db, existing.id, values)


async def delete_piece(
    db: AsyncSession, user_id: str, site_id: str, piece_id: str, *, actor: str
) -> ContentPieceRecord:
    piece = await get_piece(db, site_id, piece_id)
    if piece.status == "scheduled" and actor != "system":
        raise HTTPException(400, SCHEDULED_IS_LOCKED)
    await repo.delete_piece(db, piece.id)
    return piece


def markdown_export(piece: ContentPieceRecord) -> ContentPieceMarkdownResult:
    text = f"---\ntitle: {piece.title}\n---\n\n" + (piece.body_markdown or "").rstrip() + "\n"
    return ContentPieceMarkdownResult(markdown=text)
