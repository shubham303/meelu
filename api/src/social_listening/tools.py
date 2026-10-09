import csv
from datetime import UTC, datetime

from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.settings import settings
from src.social_listening.service import social_listening_service
from src.social_listening.schemas import (
    PostFilters,
    PostPatchRequest,
    PostResponse,
    QueryUpsertItem,
    UpsertResponse,
)

EXPORT_COLUMNS = (
    "id",
    "url",
    "platform",
    "title",
    "text",
    "author_handle",
    "posted_at",
    "engagement_score",
    "engagement_comments",
    "query_id",
    "similarity",
    "relevance",
    "composite_score",
    "status",
    "drop_reason",
    "keep_reason",
    "suggested_angle",
)


@tool(writes=True, desk="social-listening")
async def social_listening_save_queries(queries: list[QueryUpsertItem]) -> UpsertResponse:
    """Add or update the listening queries, upserted by text: [{text, enabled?, source?}].
    A query is one plain sentence describing a conversation worth joining; the run expands
    it into search keywords itself. Use source "suggested" for ones you propose; save only
    after the user agrees."""
    if not queries:
        raise ValueError("queries must not be empty.")
    ctx = require_site()
    async with unit_of_work() as db:
        return await social_listening_service.upsert_queries(db, ctx.user_id, ctx.site_id, queries)


@tool(writes=True, desk="social-listening")
async def social_listening_update_post(post_id: str, patch: PostPatchRequest) -> PostResponse:
    """Change one found post: suggestedAngle (a short reply angle, never the reply itself)
    and/or status (to_reply|drafted|replied|skipped|rejected). The user writes and posts
    replies themselves; never fill replyText."""
    if not patch.model_fields_set:
        raise ValueError("patch must not be empty.")
    if patch.reply_text is not None:
        raise ValueError("replyText is the user's own words; leave it unset.")
    ctx = require_site()
    async with unit_of_work() as db:
        return await social_listening_service.patch_post(db, ctx.site_id, post_id, patch)


@tool(desk="social-listening")
async def social_listening_download_posts(status: str | None = None) -> dict:
    """Export every post Meelu has seen (optionally one status) as a CSV file and return its
    path and row count. Analyse the file with the analytics engine; the rows never come back
    inline."""
    ctx = require_site()
    filters = PostFilters(statuses=[status] if status else None, sort="newest")
    async with unit_of_work() as db:
        rows = await social_listening_service.export_posts(db, ctx.site_id, filters)
    out_dir = settings.agent_data_dir / "social-listening" / ctx.schema
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    path = out_dir / f"posts-{stamp}.csv"
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(EXPORT_COLUMNS)
        for row in rows:
            writer.writerow(
                [
                    row.id,
                    row.url,
                    row.platform,
                    row.title or "",
                    (row.text or "").replace("\n", " "),
                    row.author_handle or "",
                    row.posted_at.isoformat() if row.posted_at else "",
                    (row.engagement or {}).get("score", ""),
                    (row.engagement or {}).get("comments", ""),
                    row.query_id or "",
                    row.similarity if row.similarity is not None else "",
                    row.relevance if row.relevance is not None else "",
                    row.composite_score if row.composite_score is not None else "",
                    row.status,
                    row.drop_reason or "",
                    row.keep_reason or "",
                    row.suggested_angle or "",
                ]
            )
    return {"path": str(path), "rows": len(rows)}
