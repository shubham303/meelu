from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.geo.schemas import ChecksStartResponse, QueryUpsertItem, UpsertResponse
from src.geo.service import geo_service


@tool(writes=True, desk="geo")
async def geo_save_queries(queries: list[QueryUpsertItem]) -> UpsertResponse:
    """Add or update tracked questions, upserted by text: [{text, enabled?, source?}].
    Use source "suggested" for ones you propose."""
    if not queries:
        raise ValueError("queries must not be empty.")
    ctx = require_site()
    async with unit_of_work() as db:
        return await geo_service.upsert_queries(db, ctx.user_id, ctx.site_id, queries)


@tool(writes=True, desk="geo")
async def geo_remove_queries(query_ids: list[str]) -> list[str]:
    """Stop tracking questions by id, deleting their checks. Only when the user asks."""
    if not query_ids:
        raise ValueError("query_ids must not be empty.")
    ctx = require_site()
    async with unit_of_work() as db:
        return await geo_service.delete_queries(db, ctx.site_id, query_ids)


@tool(writes=True, desk="geo")
async def geo_check_queries(query_ids: list[str] | None = None) -> ChecksStartResponse:
    """Start a check for each question id (none = every question not checked in 7 days).
    Spends credits on AI answers and model calls; results land in geo_check within minutes."""
    ctx = require_site()
    async with unit_of_work() as db:
        return await geo_service.start_checks(db, ctx.user_id, ctx.site_id, query_ids)
