from src.agent.context import require_site
from src.agent.server import tool
from src.content.channels import service as channels_service
from src.content.pieces import service as pieces_service
from src.content.schemas import (
    ContentFreeSlotsResponse,
    ContentPieceCreateRequest,
    ContentPieceSummaryResponse,
    ContentPieceUpdateRequest,
    SiteChannelResponse,
    SiteChannelUpdateRequest,
)
from src.core.database import unit_of_work


@tool(writes=True, desk="content")
async def content_create_piece(piece: ContentPieceCreateRequest) -> ContentPieceSummaryResponse:
    """Create one piece for one channel as a draft: {title, bodyMarkdown, channelKey,
    scheduledAt?, media fields?, cloneFromPieceId?}. scheduledAt must come from
    content_free_slots. The channel's hard checks run on save; a piece that breaks one lands
    as blocked with the reason. Call it once, with the full text, only after the user agrees."""
    if not (piece.title or "").strip() and not piece.clone_from_piece_id:
        raise ValueError("title is required.")
    if not (piece.body_markdown or "").strip() and not piece.clone_from_piece_id:
        raise ValueError("bodyMarkdown is required.")
    ctx = require_site()
    async with unit_of_work() as db:
        row = await pieces_service.create_piece(db, ctx.user_id, ctx.site_id, piece, actor="agent")
    return ContentPieceSummaryResponse.model_validate(row)


@tool(writes=True, desk="content")
async def content_update_piece(
    piece_id: str, patch: ContentPieceUpdateRequest
) -> ContentPieceSummaryResponse:
    """Change one piece: any of title, bodyMarkdown, scheduledAt (from content_free_slots, or
    null to unschedule) and the media fields. Publishing and status changes happen from the
    editor; a scheduled or posted piece cannot be edited here."""
    if not patch.model_fields_set:
        raise ValueError("patch must not be empty.")
    ctx = require_site()
    async with unit_of_work() as db:
        row = await pieces_service.update_piece(
            db, ctx.user_id, ctx.site_id, piece_id, patch, actor="agent"
        )
    return ContentPieceSummaryResponse.model_validate(row)


@tool(desk="content")
async def content_free_slots(
    channel_key: str, since: str | None = None, until: str | None = None
) -> ContentFreeSlotsResponse:
    """Open hourly slots on one channel between two ISO instants (default: the next 14 days),
    honouring its posting windows and the gap it keeps between posts. Every scheduledAt you
    set must come from the returned free list."""
    ctx = require_site()
    async with unit_of_work() as db:
        return await pieces_service.free_slots(
            db, ctx.user_id, ctx.site_id, channel_key, since, until
        )


@tool(writes=True, desk="content")
async def content_update_channel(
    channel_key: str, patch: SiteChannelUpdateRequest
) -> SiteChannelResponse:
    """Change one channel for this website: rules (the FULL replacement list of short
    instruction strings), enabled, timezone, postingWindows ([{days: [0-6], time: "09:00"}]),
    minGapHours. Save only the user's own words for the rules."""
    if not patch.changes():
        raise ValueError("patch must not be empty.")
    ctx = require_site()
    async with unit_of_work() as db:
        channel = await channels_service.update_channel(
            db, ctx.user_id, ctx.site_id, channel_key, patch
        )
    return SiteChannelResponse.model_validate(channel)


@tool(writes=True, desk="content")
async def content_reset_channel_rules(channel_key: str) -> SiteChannelResponse:
    """Put one channel's rules back to the shipped default, discarding the user's edits.
    Confirm first."""
    ctx = require_site()
    async with unit_of_work() as db:
        channel = await channels_service.reset_rules(db, ctx.user_id, ctx.site_id, channel_key)
    return SiteChannelResponse.model_validate(channel)
