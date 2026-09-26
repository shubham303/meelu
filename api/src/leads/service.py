from datetime import UTC, datetime
from urllib.parse import urlparse

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.leads.repository import lead_campaigns, lead_runs, leads
from src.leads.schemas import (
    CAMPAIGN_STATUSES,
    LEAD_SORTS,
    LEAD_STAGES,
    RUN_STATUSES,
    BulkLeadsResponse,
    CampaignCreateRequest,
    CampaignFunnel,
    CampaignPatchRequest,
    CampaignResponse,
    LeadCreateRequest,
    LeadFilters,
    LeadPatchRequest,
    LeadResponse,
    LeadsBulkRequest,
    LeadUpsertItem,
    RunResponse,
    RunUpdateRequest,
    StageCounts,
    SummaryResponse,
)


class LeadExistsError(Exception):
    def __init__(self, lead_id: str):
        self.lead_id = lead_id


LEAD_FIELDS = (
    "name",
    "company",
    "role",
    "email",
    "email_verified",
    "website",
    "source",
    "source_url",
    "channel_handles",
    "fit_score",
    "fit_reason",
    "evidence",
    "note",
)


def _now() -> datetime:
    return datetime.now(UTC)


def _domain(website: str) -> str | None:
    raw = website.strip().lower()
    if not raw:
        return None
    if "://" not in raw:
        raw = f"https://{raw}"
    host = urlparse(raw).netloc.split("@")[-1].split(":")[0]
    host = host.removeprefix("www.")
    return host or None


def _dedupe_keys_for(item: LeadUpsertItem) -> list[str]:
    keys: list[str] = []
    if item.email and item.email.strip():
        keys.append(item.email.strip().lower())
    if item.website:
        domain = _domain(item.website)
        if domain:
            keys.append(domain)
    for platform, handle in item.channel_handles.items():
        handle = (handle or "").strip().lower().lstrip("@")
        if handle:
            keys.append(f"{platform.strip().lower()}:{handle}")
    return list(dict.fromkeys(keys))


def _lead_values(item: LeadUpsertItem) -> dict:
    return {field: getattr(item, field) for field in LEAD_FIELDS}


class LeadService:
    async def list_campaigns(self, db: AsyncSession, site_id: str) -> list[CampaignResponse]:
        rows = await lead_campaigns.list(db, site_id)
        return [CampaignResponse.model_validate(r) for r in rows]

    async def create_campaign(
        self, db: AsyncSession, user_id: str, site_id: str, body: CampaignCreateRequest
    ) -> CampaignResponse:
        if body.status not in CAMPAIGN_STATUSES:
            raise HTTPException(400, f"status must be one of {', '.join(CAMPAIGN_STATUSES)}.")
        name = body.name.strip()
        if not name:
            raise HTTPException(400, "name must not be empty.")
        if await lead_campaigns.find_by_name(db, site_id, name) is not None:
            raise HTTPException(409, f"A campaign named {name} already exists.")
        values = body.model_dump()
        values["name"] = name
        row = await lead_campaigns.create(db, user_id, site_id, values)
        return CampaignResponse.model_validate(row)

    async def get_campaign(
        self, db: AsyncSession, site_id: str, campaign_id: str
    ) -> CampaignResponse:
        row = await lead_campaigns.get(db, site_id, campaign_id)
        if row is None:
            raise HTTPException(404, "Not found")
        return CampaignResponse.model_validate(row)

    async def patch_campaign(
        self, db: AsyncSession, site_id: str, campaign_id: str, body: CampaignPatchRequest
    ) -> CampaignResponse:
        row = await lead_campaigns.get(db, site_id, campaign_id)
        if row is None:
            raise HTTPException(404, "Not found")
        values = body.changes()
        status = values.get("status")
        if status is not None and status not in CAMPAIGN_STATUSES:
            raise HTTPException(400, f"status must be one of {', '.join(CAMPAIGN_STATUSES)}.")
        merged = await lead_campaigns.update(db, row, values)
        return CampaignResponse.model_validate(merged)

    async def delete_campaign(self, db: AsyncSession, site_id: str, campaign_id: str) -> str:
        row = await lead_campaigns.get(db, site_id, campaign_id)
        if row is None:
            raise HTTPException(404, "Not found")
        await lead_campaigns.delete(db, row)
        return campaign_id

    async def create_run(
        self, db: AsyncSession, user_id: str, site_id: str, campaign_id: str
    ) -> RunResponse:
        if await lead_campaigns.get(db, site_id, campaign_id) is None:
            raise HTTPException(404, f"No campaign {campaign_id} for this website.")
        row = await lead_runs.create(db, user_id, site_id, campaign_id)
        return RunResponse.model_validate(row)

    async def patch_run(
        self, db: AsyncSession, site_id: str, run_id: str, body: RunUpdateRequest
    ) -> RunResponse:
        row = await lead_runs.get(db, site_id, run_id)
        if row is None:
            raise HTTPException(404, "Not found")
        values = body.changes()
        status = values.get("status")
        if status is not None and status not in RUN_STATUSES:
            raise HTTPException(400, f"status must be one of {', '.join(RUN_STATUSES)}.")
        if status in ("done", "stopped", "error") and values.get("finished_at") is None:
            values["finished_at"] = _now()
        merged = await lead_runs.update(db, row, values)
        return RunResponse.model_validate(merged)

    async def list_runs(
        self, db: AsyncSession, site_id: str, campaign_id: str | None, paging: PaginationParams
    ) -> PaginatedApiResponse[RunResponse]:
        return await lead_runs.list(db, site_id, campaign_id, paging)

    async def get_run(self, db: AsyncSession, site_id: str, run_id: str) -> RunResponse:
        row = await lead_runs.get(db, site_id, run_id)
        if row is None:
            raise HTTPException(404, "Not found")
        return RunResponse.model_validate(row)

    async def bulk_add_leads(
        self, db: AsyncSession, user_id: str, site_id: str, body: LeadsBulkRequest
    ) -> BulkLeadsResponse:
        if body.run_id is not None and await lead_runs.get(db, site_id, body.run_id) is None:
            raise HTTPException(404, f"No discovery run {body.run_id} for this website.")
        if (
            body.campaign_id is not None
            and await lead_campaigns.get(db, site_id, body.campaign_id) is None
        ):
            raise HTTPException(404, f"No campaign {body.campaign_id} for this website.")
        all_keys = [k for item in body.leads for k in _dedupe_keys_for(item)]
        existing = await leads.find_with_any_keys(db, site_id, list(dict.fromkeys(all_keys)))
        taken = {k for lead in existing for k in lead.dedupe_keys}
        rows = []
        skipped = 0
        for item in body.leads:
            if item.stage is not None and item.stage not in LEAD_STAGES:
                raise HTTPException(400, f"stage must be one of {', '.join(LEAD_STAGES)}.")
            keys = _dedupe_keys_for(item)
            if keys and any(k in taken for k in keys):
                skipped += 1
                continue
            taken.update(keys)
            values = _lead_values(item)
            values.update(
                campaign_id=body.campaign_id,
                run_id=body.run_id,
                stage=item.stage or "qualified",
                stage_changed_at=_now(),
                dedupe_keys=keys,
            )
            rows.append(values)
        inserted = await leads.create_many(db, user_id, site_id, rows)
        return BulkLeadsResponse(inserted=inserted, skipped=skipped)

    async def create_lead(
        self, db: AsyncSession, user_id: str, site_id: str, body: LeadCreateRequest
    ) -> LeadResponse:
        if (
            body.campaign_id is not None
            and await lead_campaigns.get(db, site_id, body.campaign_id) is None
        ):
            raise HTTPException(404, f"No campaign {body.campaign_id} for this website.")
        keys = _dedupe_keys_for(body)
        existing = await leads.find_with_any_keys(db, site_id, keys)
        if existing:
            raise LeadExistsError(existing[0].id)
        values = _lead_values(body)
        values.update(
            campaign_id=body.campaign_id,
            stage="qualified",
            stage_changed_at=_now(),
            dedupe_keys=keys,
        )
        row = await leads.create(db, user_id, site_id, values)
        return LeadResponse.model_validate(row)

    async def list_leads(
        self, db: AsyncSession, site_id: str, filters: LeadFilters, paging: PaginationParams
    ) -> PaginatedApiResponse[LeadResponse]:
        if filters.stage is not None and filters.stage not in LEAD_STAGES:
            raise HTTPException(400, f"stage must be one of {', '.join(LEAD_STAGES)}.")
        if filters.sort is not None and filters.sort not in LEAD_SORTS:
            raise HTTPException(400, f"sort must be one of {', '.join(LEAD_SORTS)}.")
        return await leads.list(db, site_id, filters, paging)

    async def get_lead(self, db: AsyncSession, site_id: str, lead_id: str) -> LeadResponse:
        row = await leads.get(db, site_id, lead_id)
        if row is None:
            raise HTTPException(404, "Not found")
        return LeadResponse.model_validate(row)

    async def patch_lead(
        self, db: AsyncSession, site_id: str, lead_id: str, body: LeadPatchRequest
    ) -> LeadResponse:
        row = await leads.get(db, site_id, lead_id)
        if row is None:
            raise HTTPException(404, "Not found")
        values = body.changes()
        stage = values.get("stage")
        if stage is not None:
            if stage not in LEAD_STAGES:
                raise HTTPException(400, f"stage must be one of {', '.join(LEAD_STAGES)}.")
            if stage != row.stage:
                values["stage_changed_at"] = _now()
        merged = await leads.update(db, row, values)
        return LeadResponse.model_validate(merged)

    async def delete_lead(self, db: AsyncSession, site_id: str, lead_id: str) -> str:
        row = await leads.get(db, site_id, lead_id)
        if row is None:
            raise HTTPException(404, "Not found")
        await leads.delete(db, row)
        return lead_id

    async def summary(self, db: AsyncSession, site_id: str) -> SummaryResponse:
        stages = await leads.stage_counts(db, site_id)
        per_campaign = await leads.campaign_stage_counts(db, site_id)
        campaigns = await lead_campaigns.list(db, site_id)
        return SummaryResponse(
            stages=StageCounts(**{stage: stages.get(stage, 0) for stage in LEAD_STAGES}),
            last_run=await lead_runs.latest(db, site_id),
            campaigns=[
                CampaignFunnel(
                    id=c.id,
                    name=c.name,
                    status=c.status,
                    qualified=per_campaign.get(c.id, {}).get("qualified", 0),
                    shortlisted=per_campaign.get(c.id, {}).get("shortlisted", 0),
                )
                for c in campaigns
            ],
        )

    async def export_leads(self, db: AsyncSession, site_id: str, filters: LeadFilters):
        if filters.stage is not None and filters.stage not in LEAD_STAGES:
            raise HTTPException(400, f"stage must be one of {', '.join(LEAD_STAGES)}.")
        return await leads.list_all(db, site_id, filters)


lead_service = LeadService()
