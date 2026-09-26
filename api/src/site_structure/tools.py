from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.site_structure.schemas.results import (
    StructureReconcileResult,
    StructureSuggestionDeleteResponse,
)
from src.site_structure.service import site_structure_service


@tool(writes=True, desk="site")
async def reconcile_structure_suggestions() -> StructureReconcileResult:
    """Delete link and pillar suggestions the site has outgrown: pages gone, links already
    added or already removed, pillars fallen apart or already built. Run it before
    proposing."""
    ctx = require_site()
    async with unit_of_work() as db:
        return await site_structure_service.reconcile(db, ctx.site_id)


@tool(writes=True, desk="site")
async def delete_structure_suggestion(suggestion_id: str) -> StructureSuggestionDeleteResponse:
    """Delete one link or pillar suggestion by its id. Only when the user asks; to turn a
    suggestion down, leave it for the user to reject so it is not proposed again."""
    ctx = require_site()
    async with unit_of_work() as db:
        return await site_structure_service.delete_suggestion(db, ctx.site_id, suggestion_id)
