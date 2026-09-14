from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.content.piece_issues import repository as repo
from src.content.pieces import service as pieces
from src.content.schemas.piece_issues import (
    ISSUE_STATES,
    ContentPieceIssueRecord,
    ContentPieceIssuesReplaceRequest,
    ContentPieceIssuesReplaceResult,
    ContentPieceIssueUpdateRequest,
)
from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams


async def list_issues(
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
    await pieces.get_piece(db, site_id, piece_id)
    return await repo.list_issues(db, piece_id, paging, state=state, tool=tool)


async def replace_tool_issues(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    piece_id: str,
    body: ContentPieceIssuesReplaceRequest,
) -> ContentPieceIssuesReplaceResult:
    piece = await pieces.get_piece(db, site_id, piece_id)
    body_text = piece.body_markdown or ""
    values = []
    for issue in body.issues:
        item = issue.model_dump()
        if item["anchor_text"] and item["anchor_text"] not in body_text:
            item["anchor_text"] = None
        values.append(item)
    run_id = uid("run")
    created = await repo.replace_tool_issues(
        db, user_id, site_id, piece_id, body.tool, run_id, values
    )
    return ContentPieceIssuesReplaceResult(run_id=run_id, tool=body.tool, issues=created)


async def update_issue(
    db: AsyncSession,
    site_id: str,
    piece_id: str,
    issue_id: str,
    body: ContentPieceIssueUpdateRequest,
) -> ContentPieceIssueRecord:
    await pieces.get_piece(db, site_id, piece_id)
    issue = await repo.get_issue(db, piece_id, issue_id)
    if issue is None:
        raise HTTPException(404, "Not found")
    return await repo.update_issue(db, issue.id, {"state": body.state})
