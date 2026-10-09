import re
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.content.checks import PageFields, run_checks
from src.content.pieces.media import piece_media_service
from src.content.pieces.repository import content_pieces
from src.content.schemas.pieces import (
    ContentPieceCreateRequest,
    ContentPieceMarkdownResult,
    ContentPieceRecord,
    ContentPieceUpdateRequest,
    PieceMediaResult,
)
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.site_pages.repositories.pages import site_pages

PAGE_FIELDS = ("title", "h1", "meta_description", "slug", "target_keyword", "body_markdown")


def _word_count(markdown: str | None) -> int:
    return len(re.findall(r"\S+", markdown or ""))


def _checks_values(values: dict[str, Any]) -> list[dict[str, Any]]:
    page = PageFields(
        title=values["title"],
        h1=values["h1"],
        meta_description=values["meta_description"],
        target_keyword=values["target_keyword"],
        body_markdown=values["body_markdown"],
    )
    return [c.model_dump() for c in run_checks(page)]


def _yaml_value(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


async def _require_site_page(db: AsyncSession, site_id: str, page_id: str | None) -> None:
    if page_id and not await site_pages.exists(db, site_id, page_id):
        raise HTTPException(422, "source_page_id is not a page of this site")


class ContentPieceService:
    async def list(
        self,
        db: AsyncSession,
        site_id: str,
        paging: PaginationParams,
        *,
        search: str | None = None,
    ) -> PaginatedApiResponse[ContentPieceRecord]:
        return await content_pieces.list(db, site_id, paging, search=search)

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
        await _require_site_page(db, site_id, body.source_page_id)
        media = await piece_media_service.resolve(db, user_id, body) or PieceMediaResult()
        page = {
            "title": body.title,
            "h1": body.h1 or "",
            "meta_description": body.meta_description or "",
            "slug": body.slug,
            "target_keyword": body.target_keyword,
            "body_markdown": body.body_markdown or "",
        }
        return await content_pieces.create(
            db,
            user_id,
            site_id,
            {
                **media.model_dump(),
                **page,
                "word_count": _word_count(page["body_markdown"]),
                "checks": _checks_values(page),
                "created_by": actor,
                "source_page_id": body.source_page_id,
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
        for field in ("h1", "meta_description", "body_markdown"):
            value = getattr(body, field)
            if value is not None:
                values[field] = value
        for field in ("slug", "target_keyword", "source_page_id"):
            if body.has(field):
                values[field] = getattr(body, field) or None
        await _require_site_page(db, site_id, values.get("source_page_id"))
        if "body_markdown" in values:
            values["word_count"] = _word_count(values["body_markdown"])
        media = await piece_media_service.resolve(db, user_id, body)
        if media:
            values.update(media.model_dump())

        if not values:
            return existing
        if any(field in values for field in PAGE_FIELDS):
            page = {field: values.get(field, getattr(existing, field)) for field in PAGE_FIELDS}
            values["checks"] = _checks_values(page)
        return await content_pieces.update(db, existing.id, values)

    async def delete(self, db: AsyncSession, site_id: str, piece_id: str) -> ContentPieceRecord:
        piece = await self.get(db, site_id, piece_id)
        await content_pieces.delete(db, piece.id)
        return piece

    def markdown_export(self, piece: ContentPieceRecord) -> ContentPieceMarkdownResult:
        front = [
            ("title", piece.title),
            ("description", piece.meta_description),
            ("slug", piece.slug),
            ("keyword", piece.target_keyword),
        ]
        header = "\n".join(f"{key}: {_yaml_value(value)}" for key, value in front if value)
        heading = f"# {piece.h1}\n\n" if piece.h1 else ""
        text = f"---\n{header}\n---\n\n{heading}" + (piece.body_markdown or "").rstrip() + "\n"
        return ContentPieceMarkdownResult(markdown=text)


content_piece_service = ContentPieceService()
