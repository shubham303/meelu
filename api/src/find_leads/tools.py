from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.find_leads.schemas import BriefUpsertItem, LeadPatchRequest, LeadResponse, UpsertResponse
from src.find_leads.service import find_leads_service


@tool(writes=True, desk="find-leads")
async def find_leads_save_briefs(briefs: list[BriefUpsertItem]) -> UpsertResponse:
    """Add or update the briefs, upserted by text: [{text, enabled?, sources?, source?}].
    A brief is one plain sentence on who to look for and what shows they need the site;
    sources are posts, linkedin and web. Use source "suggested" for ones you propose."""
    if not briefs:
        raise ValueError("briefs must not be empty.")
    ctx = require_site()
    async with unit_of_work() as db:
        return await find_leads_service.upsert_briefs(db, ctx.user_id, ctx.site_id, briefs)


@tool(writes=True, desk="find-leads")
async def find_leads_update_lead(lead_id: str, patch: LeadPatchRequest) -> LeadResponse:
    """Change one lead's status: new, contacted or discarded. Only for a lead the user
    has seen; the user contacts people themselves."""
    if patch.status is None:
        raise ValueError("patch.status is required.")
    ctx = require_site()
    async with unit_of_work() as db:
        return await find_leads_service.patch_lead(db, ctx.site_id, lead_id, patch)
