from datetime import UTC, datetime, timedelta
from typing import Any

from src.core.database import unit_of_work
from src.find_leads.collect import post_quote
from src.find_leads.jobs import JobResult
from src.find_leads.repositories.leads import leads
from src.find_leads.repositories.runs import lead_runs
from src.find_leads.schemas import ACTIVITY_ITEMS, MAX_ENRICHED_PER_RUN, MAX_POST_AGE_DAYS
from src.providers.social_search.repository import social_posts


def store_entry(quote: dict[str, Any]) -> dict[str, Any]:
    return {"url": quote["url"], "text": quote["quote"], "at": quote["at"], "kind": "post"}


def recent(entry: dict[str, Any], oldest: datetime) -> bool:
    at = entry.get("at")
    if not at:
        return entry.get("kind") == "profile"
    try:
        stamp = datetime.fromisoformat(str(at).replace("Z", "+00:00"))
    except ValueError:
        return False
    return (stamp if stamp.tzinfo else stamp.replace(tzinfo=UTC)) >= oldest


def merged(oldest: datetime, *groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for group in groups:
        for entry in group:
            if recent(entry, oldest):
                seen.setdefault(entry["url"], entry)
    ordered = sorted(seen.values(), key=lambda e: e.get("at") or "", reverse=True)
    return ordered[: ACTIVITY_ITEMS * 2]


async def enrich_shortlist(user_id: str, site_id: str, run_id: str) -> JobResult:
    async with unit_of_work() as db:
        run = await lead_runs.get(db, site_id, run_id)
        if run is None or run.status != "running":
            return {"status": "error", "error": "The run is no longer going."}, 0
        shortlist = await leads.list_unenriched(db, site_id, MAX_ENRICHED_PER_RUN)

    since = datetime.now(UTC) - timedelta(days=MAX_POST_AGE_DAYS)
    from_store = 0
    async with unit_of_work() as db:
        for lead in shortlist:
            stored: list[dict[str, Any]] = []
            if lead.handle and lead.source == "posts":
                rows = await social_posts.by_author(
                    db, lead.platform, lead.handle, since, ACTIVITY_ITEMS
                )
                stored = [store_entry(post_quote(p)) for p in rows]
            activity = merged(since, stored)
            from_store += len(activity)
            await leads.set_activity(db, lead.id, activity)

    return {"status": "done", "people": len(shortlist), "fromStore": from_store}, 0
