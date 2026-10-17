from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationMeta, PaginationParams
from src.providers.registry import Caller
from src.providers.seo_data.service import seo_data
from src.providers.seo_data.shape import own_domain, pick
from src.seo.site_seo.backlink_repository import site_backlinks
from src.seo.site_seo.competitor_repository import site_competitors
from src.seo.site_seo.constants import (
    BACKLINKS_PER_DOMAIN,
    COMPETITOR_NOT_FOUND,
    MAX_COMPETITORS,
    TOO_MANY_COMPETITORS,
)
from src.seo.site_seo.models.site_backlink import is_genuine
from src.seo.site_seo.schemas import (
    BacklinkDomainRemoved,
    BacklinkDraft,
    BacklinkOpportunity,
    BacklinksFetched,
    BacklinksOfDomain,
    Competitor,
    CompetitorsChange,
    OpportunitiesDismissed,
)


def whole(value: Any) -> int | None:
    number = pick(value)
    return None if number is None else round(number)


def when(value: Any) -> datetime | None:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d %H:%M:%S %z") if value else None
    except ValueError:
        return None


def strings(value: Any) -> list[str]:
    return [str(v) for v in value or [] if isinstance(v, str) and v]


def backlink_draft(
    item: dict, site_domain: str, spam: dict[str, int], dismissed: set[str]
) -> BacklinkDraft | None:
    backlinking_url = item.get("url_from")
    backlink_url = item.get("url_to")
    backlinking_domain = own_domain(item.get("domain_from") or backlinking_url)
    if not backlinking_url or not backlink_url or not backlinking_domain:
        return None
    draft = BacklinkDraft(
        site_domain=site_domain,
        backlink_url=str(backlink_url),
        backlinking_domain=backlinking_domain,
        backlinking_url=str(backlinking_url),
        anchor=item.get("anchor") or None,
        item_type=item.get("item_type"),
        dofollow=item.get("dofollow"),
        link_attributes=strings(item.get("attributes")),
        semantic_location=item.get("semantic_location"),
        links_from_domain=whole(item.get("group_count")),
        is_lost=item.get("is_lost"),
        is_broken=item.get("is_broken"),
        first_seen=when(item.get("first_seen")),
        last_seen=when(item.get("last_seen")),
        backlink_spam_score=whole(item.get("backlink_spam_score")),
        domain_spam_score=spam.get(backlinking_domain),
        domain_rank=whole(item.get("domain_from_rank")),
        page_rank=whole(item.get("page_from_rank")),
        is_ip=item.get("domain_from_is_ip"),
        platform_type=strings(item.get("domain_from_platform_type")),
        country=item.get("domain_from_country"),
        page_title=item.get("page_from_title"),
        page_language=item.get("page_from_language"),
        page_status_code=whole(item.get("page_from_status_code")),
        page_external_links=whole(item.get("page_from_external_links")),
        dismissed=backlinking_domain in dismissed,
    )
    return draft if is_genuine(draft.model_dump()) else None


class SiteSeoService:
    async def list_competitors(self, db: AsyncSession, site_id: str) -> list[Competitor]:
        counts = await site_backlinks.counts_by_domain(db, site_id)
        return [
            Competitor(**c.model_dump(), backlinks=counts.get(c.domain, 0))
            for c in await site_competitors.list(db, site_id)
        ]

    async def add_competitors(
        self,
        db: AsyncSession,
        caller: Caller,
        user_id: str,
        site_id: str,
        site_domain: str,
        domains: list[str],
    ) -> CompetitorsChange:
        own = own_domain(site_domain)
        saved = {c.domain for c in await site_competitors.list(db, site_id)}
        fresh = [d for d in domains if d not in saved and d != own]
        if len(saved) + len(fresh) > MAX_COMPETITORS:
            raise HTTPException(409, TOO_MANY_COMPETITORS)
        ranks: dict[str, int] = {}
        if fresh:
            await db.commit()
            ranks = await seo_data.domain_ranks(caller, fresh)
        added = await site_competitors.add_many(
            db, user_id, site_id, {d: ranks.get(d) for d in fresh}
        )
        return CompetitorsChange(
            added=added,
            unchanged=[d for d in domains if d not in added],
            competitors=[c.domain for c in await site_competitors.list(db, site_id)],
        )

    async def remove_competitors(
        self, db: AsyncSession, site_id: str, domains: list[str]
    ) -> CompetitorsChange:
        removed = await site_competitors.delete_domains(db, site_id, domains)
        await site_backlinks.delete_for_domains(db, site_id, removed)
        return CompetitorsChange(
            removed=removed,
            unchanged=[d for d in domains if d not in removed],
            competitors=[c.domain for c in await site_competitors.list(db, site_id)],
        )

    async def delete_competitor(self, db: AsyncSession, site_id: str, competitor_id: str) -> None:
        found = await site_competitors.get(db, site_id, competitor_id)
        if found is None:
            raise HTTPException(404, COMPETITOR_NOT_FOUND)
        await self.remove_competitors(db, site_id, [found.domain])

    async def fetch_backlinks(
        self,
        db: AsyncSession,
        caller: Caller,
        user_id: str,
        site_id: str,
        site_domain: str,
        domains: list[str],
    ) -> BacklinksFetched:
        own = own_domain(site_domain)
        saved = {c.domain for c in await site_competitors.list(db, site_id)}
        wanted = [d for d in domains if d in saved]
        stored = await site_backlinks.counts_by_domain(db, site_id)
        targets = [*wanted, *([own] if wanted and own not in stored else [])]
        dismissed = await site_backlinks.dismissed_domains(db, site_id)
        await db.commit()
        items_of = {
            target: await seo_data.backlinks(caller, target, BACKLINKS_PER_DOMAIN)
            for target in targets
        }
        spam = await seo_data.domain_spam_scores(
            caller,
            [own_domain(i.get("domain_from")) for items in items_of.values() for i in items],
        )
        fetched: list[BacklinksOfDomain] = []
        for target, items in items_of.items():
            drafts = [
                d
                for d in (backlink_draft(i, target, spam, dismissed) for i in items)
                if d is not None
            ]
            await site_backlinks.replace_for_domain(db, user_id, site_id, target, drafts)
            if target != own:
                await site_competitors.mark_fetched(db, site_id, target)
            await db.commit()
            fetched.append(BacklinksOfDomain(domain=target, backlinks=len(drafts)))
        return BacklinksFetched(fetched=fetched, not_saved=[d for d in domains if d not in saved])

    async def opportunities(
        self, db: AsyncSession, site_id: str, site_domain: str, paging: PaginationParams
    ) -> PaginatedApiResponse[BacklinkOpportunity]:
        params = paging.validate()
        rows, total = await site_backlinks.opportunities(
            db, site_id, own_domain(site_domain), params.offset, params.page_size
        )
        total_pages = (total + params.page_size - 1) // params.page_size
        return PaginatedApiResponse[BacklinkOpportunity](
            data=[BacklinkOpportunity.model_validate(r) for r in rows],
            pagination=PaginationMeta(
                page=params.page,
                page_size=params.page_size,
                total=total,
                total_pages=total_pages,
                has_next=params.page < total_pages,
                has_prev=params.page > 1,
            ),
        )

    async def remove_backlink_domain(
        self, db: AsyncSession, site_id: str, domain: str
    ) -> BacklinkDomainRemoved:
        removed = await site_backlinks.delete_backlinking_domain(db, site_id, domain)
        return BacklinkDomainRemoved(domain=domain, backlinks_removed=removed)

    async def dismiss_opportunities(
        self, db: AsyncSession, site_id: str, domains: list[str]
    ) -> OpportunitiesDismissed:
        dismissed = await site_backlinks.dismiss(db, site_id, domains)
        return OpportunitiesDismissed(
            dismissed=dismissed, not_found=[d for d in domains if d not in dismissed]
        )


site_seo_service = SiteSeoService()
