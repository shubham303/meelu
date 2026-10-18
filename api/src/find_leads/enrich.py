from datetime import UTC, datetime, timedelta
from typing import Any

from src.core.database import unit_of_work
from src.find_leads.collect import post_quote
from src.find_leads.jobs import JobResult
from src.find_leads.models.lead import Lead
from src.find_leads.repositories.leads import leads
from src.find_leads.repositories.runs import lead_runs
from src.find_leads.schemas import ACTIVITY_ITEMS, MAX_ENRICHED_PER_RUN, MAX_POST_AGE_DAYS
from src.providers.people_search.service import people_search
from src.providers.registry import Caller
from src.providers.social_search.repository import social_posts


def vendor_person(lead: Lead) -> tuple[str, str] | None:
    if lead.platform == "reddit" and lead.handle:
        return "reddit", lead.handle
    if lead.platform == "linkedin" and lead.profile_url:
        return "linkedin", lead.profile_url
    return None


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

    wanted: dict[str, list[str]] = {}
    for lead in shortlist:
        person = vendor_person(lead)
        if person:
            wanted.setdefault(person[0], []).append(person[1])

    caller = Caller(user_id=user_id, site_id=site_id)
    fetched: dict[str, dict[str, list]] = {}
    errors: dict[str, str] = {}
    for platform, people in wanted.items():
        try:
            fetched[platform] = await people_search.activity(
                caller, platform, people, ACTIVITY_ITEMS
            )
        except Exception as exc:
            errors[platform] = str(exc)

    since = datetime.now(UTC) - timedelta(days=MAX_POST_AGE_DAYS)
    from_vendor = from_store = 0
    async with unit_of_work() as db:
        for lead in shortlist:
            stored: list[dict[str, Any]] = []
            if lead.handle and lead.source == "posts":
                rows = await social_posts.by_author(
                    db, lead.platform, lead.handle, since, ACTIVITY_ITEMS
                )
                stored = [store_entry(post_quote(p)) for p in rows]
            person = vendor_person(lead)
            vendor = fetched.get(person[0], {}).get(person[1], []) if person else []
            activity = merged(since, vendor, stored)
            from_vendor += sum(1 for e in activity if e not in stored)
            from_store += sum(1 for e in activity if e in stored)
            await leads.set_activity(db, lead.id, activity)

    stats: dict[str, Any] = {
        "status": "error" if wanted and len(errors) == len(wanted) and not from_store else "done",
        "people": len(shortlist),
        "fromVendor": from_vendor,
        "fromStore": from_store,
    }
    if errors:
        stats["error"] = "; ".join(f"{p}: {e}" for p, e in errors.items())
    return stats, 0
