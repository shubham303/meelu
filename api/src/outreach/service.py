import re
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.outreach import repository as repo
from src.outreach.schemas import (
    CampaignCreateRequest,
    CampaignRecord,
    CampaignUpdateRequest,
    ConversationCreateRequest,
    ConversationRecord,
    ConversationSyncMessage,
    ConversationSyncResult,
    ConversationUpdateRequest,
    KnownProspectItem,
    KnownProspectsResponse,
    OutreachCounts,
    OutreachProjectCreateRequest,
    OutreachProjectRecord,
    OutreachProjectUpdateRequest,
    ProspectBulkCreateResult,
    ProspectCreateRequest,
    ProspectRecord,
    ProspectSkipped,
    ProspectUpdateRequest,
)


async def list_projects(
    db: AsyncSession, user_id: str, site_id: str, paging: PaginationParams
) -> PaginatedApiResponse[OutreachProjectRecord]:
    return await repo.list_projects(db, user_id, site_id, paging)


async def get_project(
    db: AsyncSession, user_id: str, site_id: str, project_id: str
) -> OutreachProjectRecord:
    project = await repo.get_project(db, user_id, site_id, project_id)
    if project is None:
        raise HTTPException(404, "Not found")
    return project


async def create_project(
    db: AsyncSession, user_id: str, site_id: str, body: OutreachProjectCreateRequest
) -> OutreachProjectRecord:
    return await repo.create_project(db, user_id, site_id, body.model_dump())


async def update_project(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    project_id: str,
    body: OutreachProjectUpdateRequest,
) -> OutreachProjectRecord:
    project = await get_project(db, user_id, site_id, project_id)
    values = body.changes()
    if not values:
        return project
    return await repo.update_project(db, project.id, values)


async def delete_project(
    db: AsyncSession, user_id: str, site_id: str, project_id: str
) -> OutreachProjectRecord:
    project = await get_project(db, user_id, site_id, project_id)
    await repo.delete_project(db, project.id)
    return project


async def _with_found(db: AsyncSession, campaigns: list[CampaignRecord]) -> list[CampaignRecord]:
    found = {
        c.campaign_id: c.found
        for c in await repo.count_prospects_by_campaign(db, [c.id for c in campaigns])
    }
    return [c.model_copy(update={"found": found.get(c.id, 0)}) for c in campaigns]


async def list_campaigns(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    paging: PaginationParams,
    project_id: str | None = None,
    status: str | None = None,
) -> PaginatedApiResponse[CampaignRecord]:
    page = await repo.list_campaigns(db, user_id, site_id, paging, project_id, status)
    return PaginatedApiResponse[CampaignRecord](
        data=await _with_found(db, page.data), pagination=page.pagination
    )


async def get_campaign(
    db: AsyncSession, user_id: str, site_id: str, campaign_id: str
) -> CampaignRecord:
    campaign = await repo.get_campaign(db, user_id, site_id, campaign_id)
    if campaign is None:
        raise HTTPException(404, "Not found")
    return (await _with_found(db, [campaign]))[0]


async def create_campaign(
    db: AsyncSession, user_id: str, site_id: str, body: CampaignCreateRequest
) -> CampaignRecord:
    project = await repo.get_project(db, user_id, site_id, body.project_id)
    if project is None:
        raise HTTPException(400, "projectId must reference an existing project.")
    return await repo.create_campaign(db, user_id, site_id, project.id, body.requested_count)


async def update_campaign(
    db: AsyncSession, user_id: str, site_id: str, campaign_id: str, body: CampaignUpdateRequest
) -> CampaignRecord:
    existing = await repo.get_campaign(db, user_id, site_id, campaign_id)
    if existing is None:
        raise HTTPException(404, "Not found")

    values = body.changes()
    status = values.get("status")
    if "status" in values and status != "running" and existing.finished_at is None:
        values["finished_at"] = datetime.now(UTC)
    if status == "running":
        values["finished_at"] = None
    if not values:
        return (await _with_found(db, [existing]))[0]

    campaign = await repo.update_campaign(db, existing.id, values)
    return (await _with_found(db, [campaign]))[0]


async def delete_campaign(
    db: AsyncSession, user_id: str, site_id: str, campaign_id: str
) -> CampaignRecord:
    campaign = await repo.get_campaign(db, user_id, site_id, campaign_id)
    if campaign is None:
        raise HTTPException(404, "Not found")
    await repo.delete_campaign(db, campaign.id)
    return campaign


def _str(value: Any) -> str:
    return value.strip().lower() if isinstance(value, str) else ""


def _host_of(website: str) -> str:
    without_scheme = re.sub(r"^https?://", "", website)
    without_www = re.sub(r"^www\.", "", without_scheme)
    return re.split(r"[/?#]", without_www)[0]


def _identity_keys(
    email: str | None, website: str | None, company: str | None, name: str | None
) -> list[str]:
    keys: list[str] = []

    if _str(email):
        keys.append(f"email:{_str(email)}")

    host = _host_of(_str(website))
    if host:
        keys.append(f"domain:{host}")

    if _str(company):
        keys.append(f"company:{_str(company)}")

    if _str(name) and not keys:
        keys.append(f"name:{_str(name)}")

    return keys


async def _ensure_no_duplicate(
    db: AsyncSession,
    user_id: str,
    project_id: str,
    keys: list[str],
    except_id: str | None = None,
) -> None:
    prospect = await repo.find_prospect_by_keys(db, user_id, project_id, keys, except_id)
    if prospect is None:
        return
    matched_on = next((k for k in prospect.dedupe_keys if k in keys), keys[0])
    company = f" ({prospect.company})" if prospect.company else ""
    raise HTTPException(
        409,
        f"Duplicate prospect: {prospect.name}{company} "
        f"was already found for this project by an earlier run [{prospect.id}] — "
        f"matched on {matched_on}. "
        f"Skip this lead and find a different one. Call GET "
        f"/api/v1/outreach/projects/:id/known-prospects before searching so you don't "
        f"re-find them.",
    )


async def list_prospects(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    paging: PaginationParams,
    campaign_id: str | None = None,
    project_id: str | None = None,
    status: str | None = None,
) -> PaginatedApiResponse[ProspectRecord]:
    return await repo.list_prospects(db, user_id, site_id, paging, campaign_id, project_id, status)


def _with_prefix(prospects: list[ProspectRecord], prefix: str) -> list[str]:
    seen: dict[str, None] = {}
    for prospect in prospects:
        for key in prospect.dedupe_keys:
            if key.startswith(prefix):
                seen.setdefault(key[len(prefix) :], None)
    return list(seen)


async def list_known_prospects(
    db: AsyncSession, user_id: str, site_id: str, project_id: str
) -> KnownProspectsResponse:
    project = await get_project(db, user_id, site_id, project_id)
    prospects = await repo.list_prospects_for_project(db, user_id, project.id)
    return KnownProspectsResponse(
        project_id=project.id,
        project_name=project.name,
        count=len(prospects),
        exclude_emails=_with_prefix(prospects, "email:"),
        exclude_domains=_with_prefix(prospects, "domain:"),
        exclude_companies=_with_prefix(prospects, "company:"),
        prospects=[KnownProspectItem.model_validate(p) for p in prospects],
    )


async def get_prospect(
    db: AsyncSession, user_id: str, site_id: str, prospect_id: str
) -> ProspectRecord:
    prospect = await repo.get_prospect(db, user_id, site_id, prospect_id)
    if prospect is None:
        raise HTTPException(404, "Not found")
    return prospect


async def create_prospect(
    db: AsyncSession, user_id: str, site_id: str, body: ProspectCreateRequest
) -> ProspectRecord:
    campaign = await repo.get_campaign(db, user_id, site_id, body.campaign_id)
    if campaign is None:
        raise HTTPException(400, "campaignId must reference an existing campaign run.")

    dedupe_keys = _identity_keys(body.email, body.website, body.company, body.name)
    await _ensure_no_duplicate(db, user_id, campaign.project_id, dedupe_keys)

    return await repo.create_prospect(
        db, user_id, site_id, {**body.model_dump(), "dedupe_keys": dedupe_keys}
    )


async def create_prospects(
    db: AsyncSession, user_id: str, site_id: str, items: list[ProspectCreateRequest]
) -> ProspectBulkCreateResult:
    created: list[ProspectRecord] = []
    skipped: list[ProspectSkipped] = []

    for body in items:
        try:
            created.append(await create_prospect(db, user_id, site_id, body))
        except HTTPException as e:
            skipped.append(ProspectSkipped(name=body.name, reason=str(e.detail)))

    return ProspectBulkCreateResult(created=created, skipped=skipped)


async def update_prospect(
    db: AsyncSession, user_id: str, site_id: str, prospect_id: str, body: ProspectUpdateRequest
) -> ProspectRecord:
    current = await get_prospect(db, user_id, site_id, prospect_id)
    values = body.changes()

    if any(field in values for field in ("email", "website", "company", "name")):
        campaign = await repo.get_campaign(db, user_id, site_id, current.campaign_id)
        if campaign is not None:
            merged = {**current.model_dump(), **values}
            dedupe_keys = _identity_keys(
                merged["email"], merged["website"], merged["company"], merged["name"]
            )
            await _ensure_no_duplicate(db, user_id, campaign.project_id, dedupe_keys, current.id)
            values["dedupe_keys"] = dedupe_keys

    if not values:
        return current
    return await repo.update_prospect(db, current.id, values)


async def delete_prospect(
    db: AsyncSession, user_id: str, site_id: str, prospect_id: str
) -> ProspectRecord:
    prospect = await get_prospect(db, user_id, site_id, prospect_id)
    await repo.delete_prospect(db, prospect.id)
    return prospect


async def list_conversation(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    paging: PaginationParams,
    prospect_id: str | None = None,
    status: str | None = None,
) -> PaginatedApiResponse[ConversationRecord]:
    return await repo.list_conversation(db, user_id, site_id, paging, prospect_id, status)


async def get_conversation_message(
    db: AsyncSession, user_id: str, site_id: str, message_id: str
) -> ConversationRecord:
    message = await repo.get_conversation_message(db, user_id, site_id, message_id)
    if message is None:
        raise HTTPException(404, "Not found")
    return message


async def create_conversation_message(
    db: AsyncSession, user_id: str, site_id: str, body: ConversationCreateRequest
) -> ConversationRecord:
    prospect = await repo.get_prospect(db, user_id, site_id, body.prospect_id)
    if prospect is None:
        raise HTTPException(400, "prospectId must reference an existing prospect.")

    if body.status != "draft" and body.message_id:
        duplicate = await repo.find_conversation_by_message_id(db, user_id, body.message_id)
        if duplicate is not None:
            return duplicate

    values = body.model_dump(exclude={"occurred_at"})
    if values["to"] is None:
        values["to"] = prospect.email
    created_at = body.occurred_at if body.status == "received" else None

    message = await repo.create_conversation_message(db, user_id, site_id, values, created_at)

    if body.status == "sent" and prospect.status == "found":
        await repo.update_prospect(db, prospect.id, {"status": "contacted"})
    if body.status == "received" and prospect.status in ("found", "contacted"):
        await repo.update_prospect(db, prospect.id, {"status": "replied"})

    return message


async def sync_conversation_messages(
    db: AsyncSession, user_id: str, site_id: str, messages: list[ConversationSyncMessage]
) -> ConversationSyncResult:
    added: list[ConversationRecord] = []
    skipped = 0

    for item in messages:
        if not item.message_id:
            skipped += 1
            continue
        if await repo.find_conversation_by_message_id(db, user_id, item.message_id):
            skipped += 1
            continue

        added.append(
            await create_conversation_message(
                db,
                user_id,
                site_id,
                ConversationCreateRequest(
                    prospect_id=item.prospect_id,
                    subject=item.subject
                    if item.subject and item.subject.strip()
                    else "(no subject)",
                    body=item.body if item.body and item.body.strip() else "(empty message)",
                    status="received",
                    from_=item.from_,
                    to=item.to,
                    cc=item.cc,
                    bcc=item.bcc,
                    message_id=item.message_id,
                    thread_ref=item.thread_ref,
                    occurred_at=item.occurred_at,
                ),
            )
        )

    return ConversationSyncResult(added=added, skipped=skipped)


async def update_conversation_message(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    message_id: str,
    body: ConversationUpdateRequest,
) -> ConversationRecord:
    existing = await get_conversation_message(db, user_id, site_id, message_id)
    was_sent = existing.status == "sent"

    values = body.changes()
    if not values:
        return existing
    message = await repo.update_conversation_message(db, existing.id, values)

    if message.status == "sent" and not was_sent:
        prospect = await repo.get_prospect(db, user_id, site_id, message.prospect_id)
        if prospect is not None and prospect.status == "found":
            await repo.update_prospect(db, prospect.id, {"status": "contacted"})

    return message


async def delete_conversation_message(
    db: AsyncSession, user_id: str, site_id: str, message_id: str
) -> ConversationRecord:
    message = await get_conversation_message(db, user_id, site_id, message_id)
    await repo.delete_conversation_message(db, message.id)
    return message


async def counts(db: AsyncSession, user_id: str, site_id: str) -> OutreachCounts:
    return await repo.counts(db, user_id, site_id)
