from src.agent.context import require_site
from src.agent.server import tool
from src.content.channels import service as channels_service
from src.content.pieces import service as pieces_service
from src.content.schemas import (
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
    media fields?, cloneFromPieceId?}. The channel's hard checks run on save; a piece that
    breaks one lands as blocked with the reason. Call it once, with the full text, only after
    the user agrees."""
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
    """Change one piece: any of title, bodyMarkdown and the media fields. The channel's hard
    checks rerun on save and set the status."""
    if not patch.model_fields_set:
        raise ValueError("patch must not be empty.")
    ctx = require_site()
    async with unit_of_work() as db:
        row = await pieces_service.update_piece(db, ctx.user_id, ctx.site_id, piece_id, patch)
    return ContentPieceSummaryResponse.model_validate(row)


@tool(writes=True, desk="content")
async def content_update_channel(
    channel_key: str, patch: SiteChannelUpdateRequest
) -> SiteChannelResponse:
    """Change one channel for this website: rules (the FULL replacement list of short
    instruction strings) or enabled. Save only the user's own words for the rules."""
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
