from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.outreach.models.campaigns import Campaign
from src.outreach.models.conversations import Conversation
from src.outreach.models.projects import Project
from src.outreach.models.prospects import Prospect
from src.outreach.schemas import (
    CampaignProspectCount,
    CampaignRecord,
    ConversationRecord,
    OutreachCounts,
    OutreachProjectRecord,
    ProspectRecord,
)


async def list_projects(
    db: AsyncSession, user_id: str, site_id: str, paging: PaginationParams
) -> PaginatedApiResponse[OutreachProjectRecord]:
    query = (
        select(Project)
        .where(Project.user_id == user_id, Project.site_id == site_id)
        .order_by(Project.seq.desc())
    )
    return await PaginationService.paginate_query(
        db, query, paging.page, paging.page_size, OutreachProjectRecord
    )


async def get_project(
    db: AsyncSession, user_id: str, site_id: str, project_id: str
) -> OutreachProjectRecord | None:
    row = (
        await db.execute(
            select(Project).where(
                Project.user_id == user_id, Project.id == project_id, Project.site_id == site_id
            )
        )
    ).scalar_one_or_none()
    return None if row is None else OutreachProjectRecord.model_validate(row)


async def create_project(
    db: AsyncSession, user_id: str, site_id: str, values: dict[str, Any]
) -> OutreachProjectRecord:
    now = datetime.now(UTC)
    row = Project(
        id=uid("prj"), user_id=user_id, site_id=site_id, created_at=now, updated_at=now, **values
    )
    db.add(row)
    await db.flush()
    return OutreachProjectRecord.model_validate(row)


async def update_project(
    db: AsyncSession, project_id: str, values: dict[str, Any]
) -> OutreachProjectRecord:
    row = (
        await db.execute(
            update(Project)
            .where(Project.id == project_id)
            .values(**values, updated_at=datetime.now(UTC))
            .returning(Project)
        )
    ).scalar_one()
    return OutreachProjectRecord.model_validate(row)


async def delete_project(db: AsyncSession, project_id: str) -> None:
    await db.execute(delete(Project).where(Project.id == project_id))
    await db.flush()


async def list_campaigns(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    paging: PaginationParams,
    project_id: str | None = None,
    status: str | None = None,
) -> PaginatedApiResponse[CampaignRecord]:
    query = select(Campaign).where(Campaign.user_id == user_id, Campaign.site_id == site_id)
    if project_id:
        query = query.where(Campaign.project_id == project_id)
    if status:
        query = query.where(Campaign.status == status)
    query = query.order_by(Campaign.seq.desc())
    return await PaginationService.paginate_query(
        db, query, paging.page, paging.page_size, CampaignRecord
    )


async def get_campaign(
    db: AsyncSession, user_id: str, site_id: str, campaign_id: str
) -> CampaignRecord | None:
    row = (
        await db.execute(
            select(Campaign).where(
                Campaign.user_id == user_id,
                Campaign.id == campaign_id,
                Campaign.site_id == site_id,
            )
        )
    ).scalar_one_or_none()
    return None if row is None else CampaignRecord.model_validate(row)


async def count_prospects_by_campaign(
    db: AsyncSession, campaign_ids: list[str]
) -> list[CampaignProspectCount]:
    if not campaign_ids:
        return []
    rows = (
        await db.execute(
            select(Prospect.campaign_id, func.count().label("found"))
            .where(Prospect.campaign_id.in_(campaign_ids))
            .group_by(Prospect.campaign_id)
        )
    ).all()
    return [CampaignProspectCount(campaign_id=r.campaign_id, found=r.found) for r in rows]


async def create_campaign(
    db: AsyncSession, user_id: str, site_id: str, project_id: str, requested_count: int
) -> CampaignRecord:
    now = datetime.now(UTC)
    row = Campaign(
        id=uid("cmp"),
        user_id=user_id,
        site_id=site_id,
        project_id=project_id,
        requested_count=requested_count,
        status="running",
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.flush()
    return CampaignRecord.model_validate(row)


async def update_campaign(
    db: AsyncSession, campaign_id: str, values: dict[str, Any]
) -> CampaignRecord:
    row = (
        await db.execute(
            update(Campaign)
            .where(Campaign.id == campaign_id)
            .values(**values, updated_at=datetime.now(UTC))
            .returning(Campaign)
        )
    ).scalar_one()
    return CampaignRecord.model_validate(row)


async def delete_campaign(db: AsyncSession, campaign_id: str) -> None:
    await db.execute(delete(Campaign).where(Campaign.id == campaign_id))
    await db.flush()


async def list_prospects(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    paging: PaginationParams,
    campaign_id: str | None = None,
    project_id: str | None = None,
    status: str | None = None,
) -> PaginatedApiResponse[ProspectRecord]:
    query = select(Prospect).where(Prospect.user_id == user_id, Prospect.site_id == site_id)
    if project_id:
        query = query.join(Campaign, Campaign.id == Prospect.campaign_id).where(
            Campaign.project_id == project_id
        )
    if campaign_id:
        query = query.where(Prospect.campaign_id == campaign_id)
    if status:
        query = query.where(Prospect.status == status)
    query = query.order_by(Prospect.seq.desc())
    return await PaginationService.paginate_query(
        db, query, paging.page, paging.page_size, ProspectRecord
    )


async def list_prospects_for_project(
    db: AsyncSession, user_id: str, project_id: str
) -> list[ProspectRecord]:
    rows = (
        await db.execute(
            select(Prospect)
            .join(Campaign, Campaign.id == Prospect.campaign_id)
            .where(Prospect.user_id == user_id, Campaign.project_id == project_id)
            .order_by(Prospect.seq.desc())
        )
    ).scalars()
    return [ProspectRecord.model_validate(r) for r in rows]


async def get_prospect(
    db: AsyncSession, user_id: str, site_id: str, prospect_id: str
) -> ProspectRecord | None:
    row = (
        await db.execute(
            select(Prospect).where(
                Prospect.user_id == user_id,
                Prospect.id == prospect_id,
                Prospect.site_id == site_id,
            )
        )
    ).scalar_one_or_none()
    return None if row is None else ProspectRecord.model_validate(row)


async def find_prospect_by_keys(
    db: AsyncSession,
    user_id: str,
    project_id: str,
    keys: list[str],
    except_id: str | None = None,
) -> ProspectRecord | None:
    if not keys:
        return None
    conditions = [
        Prospect.user_id == user_id,
        Campaign.project_id == project_id,
        Prospect.dedupe_keys.overlap(keys),
    ]
    if except_id:
        conditions.append(Prospect.id != except_id)
    row = (
        await db.execute(
            select(Prospect)
            .join(Campaign, Campaign.id == Prospect.campaign_id)
            .where(*conditions)
            .order_by(Prospect.seq.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return None if row is None else ProspectRecord.model_validate(row)


async def create_prospect(
    db: AsyncSession, user_id: str, site_id: str, values: dict[str, Any]
) -> ProspectRecord:
    now = datetime.now(UTC)
    row = Prospect(
        id=uid("pro"), user_id=user_id, site_id=site_id, created_at=now, updated_at=now, **values
    )
    db.add(row)
    await db.flush()
    return ProspectRecord.model_validate(row)


async def update_prospect(
    db: AsyncSession, prospect_id: str, values: dict[str, Any]
) -> ProspectRecord:
    row = (
        await db.execute(
            update(Prospect)
            .where(Prospect.id == prospect_id)
            .values(**values, updated_at=datetime.now(UTC))
            .returning(Prospect)
        )
    ).scalar_one()
    return ProspectRecord.model_validate(row)


async def delete_prospect(db: AsyncSession, prospect_id: str) -> None:
    await db.execute(delete(Prospect).where(Prospect.id == prospect_id))
    await db.flush()


async def list_conversation(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    paging: PaginationParams,
    prospect_id: str | None = None,
    status: str | None = None,
) -> PaginatedApiResponse[ConversationRecord]:
    query = select(Conversation).where(
        Conversation.user_id == user_id, Conversation.site_id == site_id
    )
    if prospect_id:
        query = query.where(Conversation.prospect_id == prospect_id)
    if status:
        query = query.where(Conversation.status == status)
    query = query.order_by(Conversation.created_at.asc(), Conversation.seq.asc())
    return await PaginationService.paginate_query(
        db, query, paging.page, paging.page_size, ConversationRecord
    )


async def get_conversation_message(
    db: AsyncSession, user_id: str, site_id: str, message_id: str
) -> ConversationRecord | None:
    row = (
        await db.execute(
            select(Conversation).where(
                Conversation.user_id == user_id,
                Conversation.id == message_id,
                Conversation.site_id == site_id,
            )
        )
    ).scalar_one_or_none()
    return None if row is None else ConversationRecord.model_validate(row)


async def find_conversation_by_message_id(
    db: AsyncSession, user_id: str, message_id: str
) -> ConversationRecord | None:
    row = (
        await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id, Conversation.message_id == message_id)
            .limit(1)
        )
    ).scalar_one_or_none()
    return None if row is None else ConversationRecord.model_validate(row)


async def create_conversation_message(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    values: dict[str, Any],
    created_at: datetime | None = None,
) -> ConversationRecord:
    now = datetime.now(UTC)
    row = Conversation(
        id=uid("cnv"),
        user_id=user_id,
        site_id=site_id,
        created_at=created_at or now,
        updated_at=now,
        **values,
    )
    db.add(row)
    await db.flush()
    return ConversationRecord.model_validate(row)


async def update_conversation_message(
    db: AsyncSession, message_id: str, values: dict[str, Any]
) -> ConversationRecord:
    row = (
        await db.execute(
            update(Conversation)
            .where(Conversation.id == message_id)
            .values(**values, updated_at=datetime.now(UTC))
            .returning(Conversation)
        )
    ).scalar_one()
    return ConversationRecord.model_validate(row)


async def delete_conversation_message(db: AsyncSession, message_id: str) -> None:
    await db.execute(delete(Conversation).where(Conversation.id == message_id))
    await db.flush()


async def counts(db: AsyncSession, user_id: str, site_id: str) -> OutreachCounts:
    projects = (
        await db.execute(
            select(func.count())
            .select_from(Project)
            .where(Project.user_id == user_id, Project.site_id == site_id)
        )
    ).scalar_one()

    campaigns = (
        await db.execute(
            select(
                func.count().label("runs"),
                func.count().filter(Campaign.status == "running").label("active_runs"),
            )
            .select_from(Campaign)
            .where(Campaign.user_id == user_id, Campaign.site_id == site_id)
        )
    ).one()

    prospects = (
        await db.execute(
            select(
                func.count().label("prospects"),
                func.count().filter(Prospect.status == "replied").label("replies"),
            )
            .select_from(Prospect)
            .where(Prospect.user_id == user_id, Prospect.site_id == site_id)
        )
    ).one()

    conversations = (
        await db.execute(
            select(
                func.count().filter(Conversation.status == "draft").label("drafts"),
                func.count().filter(Conversation.status == "sent").label("sent"),
            )
            .select_from(Conversation)
            .where(Conversation.user_id == user_id, Conversation.site_id == site_id)
        )
    ).one()

    return OutreachCounts(
        projects=projects,
        runs=campaigns.runs,
        active_runs=campaigns.active_runs,
        prospects=prospects.prospects,
        drafts=conversations.drafts,
        sent=conversations.sent,
        replies=prospects.replies,
    )
