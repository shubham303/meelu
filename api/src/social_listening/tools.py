from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.social_listening.schemas import (
    PostPatchRequest,
    PostResponse,
    QueryUpsertItem,
    UpsertResponse,
)
from src.social_listening.service import social_listening_service


@tool(writes=True, desk="social-listening")
async def social_listening_save_queries(queries: list[QueryUpsertItem]) -> UpsertResponse:
    """Add or update the listening queries, upserted by text: [{text, enabled?, source?}].
    A query is one plain sentence describing a conversation worth joining; the run expands
    it into search keywords itself. Use source "suggested" for ones you propose."""
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
