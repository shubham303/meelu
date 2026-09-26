from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.content.piece_issues.repository import content_piece_issues
from src.content.pieces.service import content_piece_service
from src.content.schemas.piece_issues import (
    ISSUE_STATES,
    ContentPieceIssueRecord,
    ContentPieceIssuesReplaceRequest,
    ContentPieceIssuesReplaceResult,
    ContentPieceIssueUpdateRequest,
)
from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams


class ContentPieceIssueService:
    async def list(
        self,
        db: AsyncSession,
        site_id: str,
        piece_id: str,
        paging: PaginationParams,
        *,
        state: str | None = None,
        tool: str | None = None,
    ) -> PaginatedApiResponse[ContentPieceIssueRecord]:
        if state is not None and state not in ISSUE_STATES:
            raise HTTPException(400, f"state must be one of {', '.join(ISSUE_STATES)}.")
        await content_piece_service.get(db, site_id, piece_id)
        return await content_piece_issues.list(db, piece_id, paging, state=state, tool=tool)

    async def replace_for_tool(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        piece_id: str,
        body: ContentPieceIssuesReplaceRequest,
    ) -> ContentPieceIssuesReplaceResult:
        piece = await content_piece_service.get(db, site_id, piece_id)
        body_text = piece.body_markdown or ""
        values = []
        for issue in body.issues:
            item = issue.model_dump()
            if item["anchor_text"] and item["anchor_text"] not in body_text:
                item["anchor_text"] = None
            values.append(item)
        run_id = uid("run")
        created = await content_piece_issues.replace_for_tool(
            db, user_id, site_id, piece_id, body.tool, run_id, values
        )
        return ContentPieceIssuesReplaceResult(run_id=run_id, tool=body.tool, issues=created)

    async def update(
        self,
        db: AsyncSession,
        site_id: str,
        piece_id: str,
        issue_id: str,
        body: ContentPieceIssueUpdateRequest,
    ) -> ContentPieceIssueRecord:
        await content_piece_service.get(db, site_id, piece_id)
        issue = await content_piece_issues.get(db, piece_id, issue_id)
        if issue is None:
            raise HTTPException(404, "Not found")
        return await content_piece_issues.update(db, issue.id, {"state": body.state})


content_piece_issue_service = ContentPieceIssueService()
