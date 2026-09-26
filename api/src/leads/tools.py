import csv
from datetime import UTC, datetime

from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.leads.service import lead_service
from src.leads.schemas import (
    BulkLeadsResponse,
    CampaignCreateRequest,
    CampaignPatchRequest,
    CampaignResponse,
    LeadFilters,
    LeadPatchRequest,
    LeadResponse,
    LeadsBulkRequest,
)
from src.settings import settings

EXPORT_COLUMNS = (
    "id",
    "name",
    "company",
    "role",
    "email",
    "email_verified",
    "website",
    "source",
    "source_url",
    "campaign_id",
    "stage",
    "fit_score",
    "fit_reason",
    "created_at",
)


@tool(writes=True, desk="leads")
async def leads_save_campaign(
    campaign: CampaignCreateRequest, campaign_id: str | None = None
) -> CampaignResponse:
    """Create a lead campaign brief, or patch one by passing its campaignId. A campaign is one
    standing search: audience (who to look for), sources, schedule. Save only wording the user
    has agreed to."""
    ctx = require_site()
    async with unit_of_work() as db:
        if campaign_id is None:
            return await lead_service.create_campaign(db, ctx.user_id, ctx.site_id, campaign)
        patch = CampaignPatchRequest(**campaign.model_dump())
        return await lead_service.patch_campaign(db, ctx.site_id, campaign_id, patch)


@tool(writes=True, desk="leads")
async def leads_add_leads(leads: LeadsBulkRequest) -> BulkLeadsResponse:
    """Add qualified leads found by a discovery task: {campaignId?, leads: [{name, company?,
    role?, email?, website?, channelHandles?, source?, sourceUrl?, fitScore?, fitReason?,
    evidence?}]}. Leads already in this site's list are skipped, never duplicated.
    Never invent an email — pass one only when it was read on a real page."""
    if not leads.leads:
        raise ValueError("leads must not be empty.")
    ctx = require_site()
    async with unit_of_work() as db:
        return await lead_service.bulk_add_leads(db, ctx.user_id, ctx.site_id, leads)


@tool(writes=True, desk="leads")
async def leads_update_lead(lead_id: str, patch: LeadPatchRequest) -> LeadResponse:
    """Change one lead: fields, evidence, fit, or stage (found, qualified, shortlisted).
    Shortlisted is the curated list — move a lead there only when it clears the filters the
    user asked for."""
    if not patch.model_fields_set:
        raise ValueError("patch must not be empty.")
    ctx = require_site()
    async with unit_of_work() as db:
        return await lead_service.patch_lead(db, ctx.site_id, lead_id, patch)


@tool(desk="leads")
async def leads_download_leads(stage: str | None = None, campaign_id: str | None = None) -> dict:
    """Export the lead list (optionally one stage or one campaignId) as a CSV file and
    return its path and row count. Analyse the file with the analytics engine; the rows
    never come back inline."""
    ctx = require_site()
    filters = LeadFilters(stage=stage, campaign_id=campaign_id, sort="newest")
    async with unit_of_work() as db:
        rows = await lead_service.export_leads(db, ctx.site_id, filters)
    out_dir = settings.agent_data_dir / "leads" / ctx.schema
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    path = out_dir / f"leads-{stamp}.csv"
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(EXPORT_COLUMNS)
        for row in rows:
            writer.writerow(
                [
                    row.id,
                    row.name,
                    row.company or "",
                    row.role or "",
                    row.email or "",
                    row.email_verified,
                    row.website or "",
                    row.source or "",
                    row.source_url or "",
                    row.campaign_id or "",
                    row.stage,
                    row.fit_score if row.fit_score is not None else "",
                    row.fit_reason or "",
                    row.created_at.isoformat(),
                ]
            )
    return {"path": str(path), "rows": len(rows)}
