import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.content.channels.service import site_channel_service
from src.content.checks import is_blocked, run_checks
from src.content.pieces.media import piece_media_service
from src.content.pieces.repository import content_pieces
from src.content.platform_seeds import SEEDS_BY_KEY
from src.content.schemas.pieces import (
    PIECE_STATUSES,
    ContentPieceCountsResponse,
    ContentPieceCreateRequest,
    ContentPieceMarkdownResult,
    ContentPieceRecord,
    ContentPieceUpdateRequest,
    PieceCheck,
    PieceMediaResult,
)
from src.core.pagination import PaginatedApiResponse, PaginationParams


def _word_count(markdown: str | None) -> int:
    return len(re.findall(r"\S+", markdown or ""))


def _valid_status(value: str) -> str:
    if value not in PIECE_STATUSES:
        raise HTTPException(400, f"Invalid status. Allowed values: {', '.join(PIECE_STATUSES)}.")
    return value


def _media_count(media_source: str) -> int:
    return 0 if media_source == "none" else 1


def _checks_for(channel_key: str, body: str, media_source: str) -> list[PieceCheck]:
    return run_checks(
        SEEDS_BY_KEY[channel_key], body, media_count=_media_count(media_source), site_host=None
    )


def _checks_values(checks: list[PieceCheck]) -> list[dict[str, Any]]:
    return [c.model_dump() for c in checks]


def _status_after_checks(checks: list[PieceCheck]) -> str:
    return "blocked" if is_blocked(checks) else "draft"


class ContentPieceService:
    async def list(
        self,
        db: AsyncSession,
        site_id: str,
        paging: PaginationParams,
        *,
        status: str | None = None,
        channel_key: str | None = None,
        search: str | None = None,
    ) -> PaginatedApiResponse[ContentPieceRecord]:
        if status is not None:
            _valid_status(status)
        if channel_key is not None and channel_key not in SEEDS_BY_KEY:
            raise HTTPException(400, f'Unknown channel "{channel_key}".')
        return await content_pieces.list(
            db, site_id, paging, status=status, channel_key=channel_key, search=search
        )

    async def counts(self, db: AsyncSession, site_id: str) -> ContentPieceCountsResponse:
        found = await content_pieces.counts_by_status(db, site_id)
        return ContentPieceCountsResponse(
            by_status={s: found.by_status.get(s, 0) for s in PIECE_STATUSES}
        )

    async def get(self, db: AsyncSession, site_id: str, piece_id: str) -> ContentPieceRecord:
        piece = await content_pieces.get(db, site_id, piece_id)
        if piece is None:
            raise HTTPException(404, "Not found")
        return piece

    async def create(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        body: ContentPieceCreateRequest,
        *,
        actor: str,
    ) -> ContentPieceRecord:
        source: ContentPieceRecord | None = None
        if body.clone_from_piece_id:
            source = await content_pieces.get(db, site_id, body.clone_from_piece_id)
            if source is None:
                raise HTTPException(404, "The piece to clone from doesn't exist.")

        channel_key = body.channel_key or (source.channel_key if source else None)
        if not channel_key:
            raise HTTPException(400, "channelKey is required.")
        if channel_key not in SEEDS_BY_KEY:
            raise HTTPException(400, f'Unknown channel "{channel_key}".')
        await site_channel_service.require_enabled(db, user_id, site_id, channel_key)

        title = body.title or (f"{source.title} (copy)" if source else None)
        if not title:
            raise HTTPException(400, "title is required.")
        text = (
            body.body_markdown
            if body.body_markdown is not None
            else (source.body_markdown if source else "")
        )

        media = await piece_media_service.resolve(db, user_id, body)
        if media is None:
            media = (
                PieceMediaResult.model_validate(source.model_dump())
                if source and source.channel_key == channel_key
                else PieceMediaResult()
            )
        checks = _checks_for(channel_key, text, media.media_source)

        return await content_pieces.create(
            db,
            user_id,
            site_id,
            {
                **media.model_dump(),
                "title": title,
                "body_markdown": text,
                "channel_key": channel_key,
                "status": _status_after_checks(checks),
                "word_count": _word_count(text),
                "checks": _checks_values(checks),
                "created_by": actor,
                "source_page_id": body.source_page_id
                or (source.source_page_id if source else None),
                "parent_piece_id": source.id if source else None,
            },
        )

    async def update(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        piece_id: str,
        body: ContentPieceUpdateRequest,
    ) -> ContentPieceRecord:
        existing = await self.get(db, site_id, piece_id)

        values: dict[str, Any] = {}
        if body.title is not None:
            values["title"] = body.title
        if body.body_markdown is not None:
            values["body_markdown"] = body.body_markdown
            values["word_count"] = _word_count(body.body_markdown)
        if body.has("source_page_id"):
            values["source_page_id"] = body.source_page_id or None
        media = await piece_media_service.resolve(db, user_id, body)
        if media:
            values.update(media.model_dump())

        if "body_markdown" in values or media is not None:
            text = values.get("body_markdown", existing.body_markdown)
            source = str(values.get("media_source", existing.media_source))
            checks = _checks_for(existing.channel_key, text, source)
            values["checks"] = _checks_values(checks)
            values["status"] = _status_after_checks(checks)

        if not values:
            return existing
        return await content_pieces.update(db, existing.id, values)

    async def delete(self, db: AsyncSession, site_id: str, piece_id: str) -> ContentPieceRecord:
        piece = await self.get(db, site_id, piece_id)
        await content_pieces.delete(db, piece.id)
        return piece

    def markdown_export(self, piece: ContentPieceRecord) -> ContentPieceMarkdownResult:
        text = f"---\ntitle: {piece.title}\n---\n\n" + (piece.body_markdown or "").rstrip() + "\n"
        return ContentPieceMarkdownResult(markdown=text)


content_piece_service = ContentPieceService()
