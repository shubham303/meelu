from src.agent.context import require_site
from src.agent.server import tool
from src.content.pieces.service import content_piece_service
from src.content.schemas import (
    ContentPieceCreateRequest,
    ContentPieceSummaryResponse,
    ContentPieceUpdateRequest,
)
from src.core.database import unit_of_work


@tool(writes=True, desk="content")
async def content_create_piece(piece: ContentPieceCreateRequest) -> ContentPieceSummaryResponse:
    """Save one web page as a draft: {title, h1, metaDescription, slug, targetKeyword,
    bodyMarkdown, media fields?}. The body starts after the H1 and uses H2/H3. Page checks run on
    save and come back as warnings. Call it once, with the full text."""
    if not (piece.body_markdown or "").strip():
        raise ValueError("bodyMarkdown is required.")
    ctx = require_site()
    async with unit_of_work() as db:
        row = await content_piece_service.create(db, ctx.user_id, ctx.site_id, piece, actor="agent")
    return ContentPieceSummaryResponse.model_validate(row)


@tool(writes=True, desk="content")
async def content_update_piece(
    piece_id: str, patch: ContentPieceUpdateRequest
) -> ContentPieceSummaryResponse:
    """Change one piece: any of title, h1, metaDescription, slug, targetKeyword, bodyMarkdown
    and the media fields. The page checks rerun on save."""
    if not patch.model_fields_set:
        raise ValueError("patch must not be empty.")
    ctx = require_site()
    async with unit_of_work() as db:
        row = await content_piece_service.update(db, ctx.user_id, ctx.site_id, piece_id, patch)
    return ContentPieceSummaryResponse.model_validate(row)
