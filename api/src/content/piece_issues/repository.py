from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.content.models.content_piece_issues import ContentPieceIssue
from src.content.schemas.piece_issues import ContentPieceIssueRecord
from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService


async def list_issues(
    db: AsyncSession,
    piece_id: str,
    paging: PaginationParams,
    *,
    state: str | None,
    tool: str | None,
) -> PaginatedApiResponse[ContentPieceIssueRecord]:
    where = [ContentPieceIssue.piece_id == piece_id]
    if state:
        where.append(ContentPieceIssue.state == state)
    if tool:
        where.append(ContentPieceIssue.tool == tool)
    query = select(ContentPieceIssue).where(*where).order_by(ContentPieceIssue.seq.asc())
    return await PaginationService.paginate_query(
        db, query, paging.page, paging.page_size, ContentPieceIssueRecord
    )


async def get_issue(
    db: AsyncSession, piece_id: str, issue_id: str
) -> ContentPieceIssueRecord | None:
    row = (
        await db.execute(
            select(ContentPieceIssue).where(
                ContentPieceIssue.piece_id == piece_id, ContentPieceIssue.id == issue_id
            )
        )
    ).scalar_one_or_none()
    return None if row is None else ContentPieceIssueRecord.model_validate(row)


async def replace_tool_issues(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    piece_id: str,
    tool: str,
    run_id: str,
    issues: list[dict[str, Any]],
) -> list[ContentPieceIssueRecord]:
    await db.execute(
        delete(ContentPieceIssue).where(
            ContentPieceIssue.piece_id == piece_id, ContentPieceIssue.tool == tool
        )
    )
    now = datetime.now(UTC)
    rows = [
        ContentPieceIssue(
            id=uid("cpi"),
            user_id=user_id,
            site_id=site_id,
            piece_id=piece_id,
            tool=tool,
            run_id=run_id,
            state="open",
            created_at=now,
            updated_at=now,
            **values,
        )
        for values in issues
    ]
    db.add_all(rows)
    await db.flush()
    return [ContentPieceIssueRecord.model_validate(row) for row in rows]


async def update_issue(
    db: AsyncSession, issue_id: str, values: dict[str, Any]
) -> ContentPieceIssueRecord:
    row = (
        await db.execute(
            update(ContentPieceIssue)
            .where(ContentPieceIssue.id == issue_id)
            .values(**values, updated_at=datetime.now(UTC))
            .returning(ContentPieceIssue)
        )
    ).scalar_one()
    return ContentPieceIssueRecord.model_validate(row)
