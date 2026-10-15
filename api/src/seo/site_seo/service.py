from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.providers.registry import Caller
from src.providers.seo_data.service import seo_data
from src.providers.seo_data.shape import own_domain
from src.seo.site_search.repositories.site_search_daily import site_search_dailies
from src.seo.site_seo.competitor_repository import seo_competitors
from src.seo.site_seo.constants import (
    COMPETITOR_SAMPLE_QUERIES,
    GAP_DOMAINS_PER_COMPETITOR,
    MAX_GAP_COMPETITORS,
    MAX_LIST_ITEMS,
    SeoList,
)
from src.seo.site_seo.repository import site_seo
from src.seo.site_seo.schemas import (
    BacklinkOpportunities,
    BacklinkOpportunity,
    FoundCompetitor,
    FoundCompetitors,
    SeoListChange,
    SiteSeoRecord,
)


def add_source(row: FoundCompetitor, source: str) -> None:
    if source not in row.sources:
        row.sources.append(source)


def best(current: float | None, found: float | None) -> float | None:
    values = [v for v in (current, found) if v is not None]
    return min(values) if values else None


NO_COMPETITORS = (
    "No competitors to compare against. Pass some, or save the site's competitors first."
)


class SiteSeoService:
    async def get(self, db: AsyncSession, site_id: str) -> SiteSeoRecord:
        return SiteSeoRecord(
            site_id=site_id,
            competitors=[c.domain for c in await seo_competitors.list(db, site_id)],
            backlink_opportunities=await site_seo.backlink_opportunities(db, site_id),
        )

    async def add_items(
        self, db: AsyncSession, user_id: str, site_id: str, name: SeoList, items: list[str]
    ) -> SeoListChange:
        current = getattr(await self.get(db, site_id), name)
        added = [i for i in items if i not in current]
        if len(current) + len(added) > MAX_LIST_ITEMS:
            raise HTTPException(409, f"The {name} list holds at most {MAX_LIST_ITEMS} entries.")
        if name == "competitors":
            await seo_competitors.add_many(db, user_id, site_id, added)
        else:
            await site_seo.set_backlink_opportunities(db, user_id, site_id, [*current, *added])
        return SeoListChange(
            list=name,
            added=added,
            unchanged=[i for i in items if i in current],
            items=getattr(await self.get(db, site_id), name),
        )

    async def remove_items(
        self, db: AsyncSession, user_id: str, site_id: str, name: SeoList, items: list[str]
    ) -> SeoListChange:
        current = getattr(await self.get(db, site_id), name)
        removed = [i for i in items if i in current]
        if name == "competitors":
            await seo_competitors.delete_domains(db, site_id, removed)
        else:
            await site_seo.set_backlink_opportunities(
                db, user_id, site_id, [i for i in current if i not in removed]
            )
        return SeoListChange(
            list=name,
            removed=removed,
            unchanged=[i for i in items if i not in current],
            items=getattr(await self.get(db, site_id), name),
        )

    async def find_competitors(
        self,
        db: AsyncSession,
        caller: Caller,
        site_id: str,
        domain: str,
        limit: int,
        targets: list[dict],
    ) -> FoundCompetitors:
        own = own_domain(domain)
        saved = set((await self.get(db, site_id)).competitors)
        found: dict[str, FoundCompetitor] = {}

        def entry(name: str) -> FoundCompetitor | None:
            key = own_domain(name)
            if not key or key == own:
                return None
            return found.setdefault(
                key, FoundCompetitor(domain=key, sources=[], saved=key in saved)
            )

        totals = await site_search_dailies.query_window_totals(db, site_id)
        queries = [
            t.query
            for t in sorted(totals, key=lambda t: -t.impressions_28d)
            if t.impressions_28d > 0
        ][:COMPETITOR_SAMPLE_QUERIES]
        await db.commit()

        for market in targets:
            code, language = market["location_code"], market["language_code"]
            rivals = await seo_data.rival_domains(caller, own, limit, code, language)
            for rival in rivals["rivals"]:
                if (row := entry(rival["domain"])) is not None:
                    add_source(row, "shared_keywords")
                    row.shared_keywords = (row.shared_keywords or 0) + (rival["intersections"] or 0)
                    row.avg_position = best(row.avg_position, rival["avgPosition"])
            if queries:
                serp = await seo_data.serp_competitors(caller, queries, limit, code, language)
                for competitor in serp["competitors"]:
                    if (row := entry(competitor["domain"])) is not None:
                        add_source(row, "search_console_serps")
                        row.visibility = max(row.visibility or 0, competitor["visibility"] or 0)
                        row.avg_position = best(row.avg_position, competitor["avgPosition"])

        ranked = sorted(
            found.values(),
            key=lambda c: (-len(c.sources), -(c.shared_keywords or 0), -(c.visibility or 0)),
        )
        return FoundCompetitors(sampled_queries=len(queries), competitors=ranked[:limit])

    async def find_backlink_opportunities(
        self,
        db: AsyncSession,
        caller: Caller,
        site_id: str,
        domain: str,
        competitors: list[str] | None,
        limit: int,
    ) -> BacklinkOpportunities:
        record = await self.get(db, site_id)
        own = own_domain(domain)
        targets = [
            c
            for c in dict.fromkeys(own_domain(c) for c in (competitors or record.competitors))
            if c and c != own
        ][:MAX_GAP_COMPETITORS]
        if not targets:
            raise HTTPException(409, NO_COMPETITORS)
        saved = set(record.backlink_opportunities)
        found: dict[str, BacklinkOpportunity] = {}
        await db.commit()
        for target in targets:
            for referrer in await seo_data.referring_domains_gap(
                caller, target, [own], GAP_DOMAINS_PER_COMPETITOR
            ):
                key = own_domain(referrer["target"])
                if not key or key == own or key in targets:
                    continue
                row = found.setdefault(
                    key, BacklinkOpportunity(domain=key, links_to=[], saved=key in saved)
                )
                row.links_to.append(target)
                row.backlinks_to_competitors += int(referrer.get("backlinks") or 0)
                row.rank = max(row.rank or 0, int(referrer.get("rank") or 0)) or None
                spam = referrer.get("backlinks_spam_score")
                if isinstance(spam, int):
                    row.spam_score = spam if row.spam_score is None else min(row.spam_score, spam)
        ranked = sorted(found.values(), key=lambda o: (-len(o.links_to), -(o.rank or 0)))
        return BacklinkOpportunities(
            competitors=targets, total=len(ranked), opportunities=ranked[:limit]
        )


site_seo_service = SiteSeoService()
