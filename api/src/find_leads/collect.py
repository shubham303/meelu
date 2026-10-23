from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import unit_of_work
from src.find_leads.identity import author_key, profile_url, usable_handle
from src.find_leads.jobs import JobResult
from src.find_leads.repositories.briefs import lead_briefs
from src.find_leads.repositories.leads import leads
from src.find_leads.repositories.runs import lead_runs
from src.find_leads.repositories.searches import lead_searches
from src.find_leads.repositories.seen import lead_seen
from src.find_leads.schemas import (
    LINKEDIN_PER_BRIEF,
    LOOKBACK_DAYS,
    MAX_CANDIDATES_PER_RUN,
    MAX_CANDIDATES_PER_SOURCE,
    MAX_EVIDENCE,
    MAX_LINKEDIN_PAGES,
    PER_KEYWORD,
    SKIP_HOURS,
)
from src.providers.people_search.service import people_search
from src.providers.registry import Caller
from src.providers.social_search.models.social_post import SocialPost
from src.providers.social_search.repository import social_posts
from src.providers.social_search.store import collect_posts

SNIPPET_CHARS = 600
QUOTE_CHARS = 300
STOPPED = {"status": "error", "error": "The run is no longer going."}


def normalize_keyword(keyword: str) -> str:
    return " ".join(str(keyword).lower().split())


def clip(text: str | None, size: int) -> str:
    return " ".join((text or "").split())[:size]


def post_quote(post: SocialPost) -> dict[str, Any]:
    body = " — ".join(p for p in (clip(post.title, 160), clip(post.text, QUOTE_CHARS)) if p)
    return {
        "url": post.url,
        "quote": body[:QUOTE_CHARS],
        "at": post.posted_at.isoformat() if post.posted_at else None,
    }


def author_candidates(
    posts: list[SocialPost], brief_of_post: dict[str, str | None]
) -> list[dict[str, Any]]:
    by_author: dict[str, dict[str, Any]] = {}
    for post in sorted(posts, key=lambda p: p.posted_at or p.fetched_at, reverse=True):
        handle = usable_handle(post.author_handle)
        if handle is None:
            continue
        key = author_key(post.platform, handle)
        lead = by_author.get(key)
        if lead is None:
            lead = by_author[key] = {
                "identity_key": key,
                "source": "posts",
                "platform": post.platform,
                "brief_id": brief_of_post.get(post.id),
                "name": post.author_name or handle,
                "handle": handle,
                "profile_url": profile_url(post.platform, handle),
                "snippet": clip(f"{post.title or ''} {post.text or ''}", SNIPPET_CHARS),
                "evidence": [],
            }
        if len(lead["evidence"]) < MAX_EVIDENCE:
            lead["evidence"].append(post_quote(post))
    return list(by_author.values())


def linkedin_candidates(people: list[dict], brief_id: str) -> list[dict[str, Any]]:
    out = []
    for person in people:
        if not person.get("profileUrl"):
            continue
        snippet = " · ".join(
            p for p in (person.get("headline"), person.get("location"), person.get("summary")) if p
        )
        out.append(
            {
                "identity_key": f"linkedin:{str(person['id']).lower()}",
                "source": "linkedin",
                "platform": "linkedin",
                "brief_id": brief_id,
                "name": person.get("name"),
                "handle": None,
                "headline": person.get("headline"),
                "profile_url": person["profileUrl"],
                "snippet": clip(snippet, SNIPPET_CHARS),
                "evidence": [],
            }
        )
    return out


async def insert_fresh(
    db: AsyncSession, user_id: str, site_id: str, run_id: str, rows: list[dict[str, Any]]
) -> tuple[int, int]:
    unique = list({r["identity_key"]: r for r in rows}.values())
    keys = [r["identity_key"] for r in unique]
    known = await leads.existing_keys(db, site_id, keys)
    known |= await lead_seen.existing_keys(db, site_id, keys)
    fresh = [r for r in unique if r["identity_key"] not in known]
    room = min(
        MAX_CANDIDATES_PER_SOURCE,
        MAX_CANDIDATES_PER_RUN - await leads.count_for_run(db, run_id),
    )
    inserted = await leads.insert_many(db, user_id, site_id, run_id, fresh[: max(room, 0)])
    return inserted, len(unique) - inserted


async def save_candidates(
    user_id: str, site_id: str, run_id: str, rows: list[dict[str, Any]]
) -> tuple[int, int]:
    async with unit_of_work() as db:
        return await insert_fresh(db, user_id, site_id, run_id, rows)


async def _running(site_id: str, run_id: str) -> bool:
    async with unit_of_work() as db:
        run = await lead_runs.get(db, site_id, run_id)
    return run is not None and run.status == "running"


def recently_searched(rows: dict, now: datetime) -> list[dict[str, str]]:
    cutoff = now - timedelta(hours=SKIP_HOURS)
    return [
        {"query": query, "searchedAt": row.searched_at.isoformat()}
        for query, row in rows.items()
        if row.searched_at >= cutoff
    ]


def linkedin_query_key(plan: dict[str, Any]) -> str:
    return " | ".join(
        [
            plan["query"],
            ", ".join(plan.get("titles") or []),
            ", ".join(plan.get("locations") or []),
        ]
    )


def next_page(previous: int | None) -> int:
    if previous is None or previous >= MAX_LINKEDIN_PAGES:
        return 1
    return previous + 1


def round_keywords(brief, keywords_by_brief: dict[str, list[str]] | None) -> list[str]:
    if keywords_by_brief is not None:
        return keywords_by_brief.get(brief.id) or []
    return (brief.plan or {}).get("keywords") or []


async def collect_post_authors(
    user_id: str,
    site_id: str,
    run_id: str,
    platform: str,
    keywords_by_brief: dict[str, list[str]] | None = None,
) -> JobResult:
    if not await _running(site_id, run_id):
        return STOPPED, 0
    async with unit_of_work() as db:
        briefs = [
            b for b in await lead_briefs.list_enabled(db, site_id) if "posts" in (b.sources or [])
        ]
    brief_of_keyword: dict[str, str] = {}
    for brief in briefs:
        for keyword in round_keywords(brief, keywords_by_brief):
            clean = normalize_keyword(keyword)
            if clean:
                brief_of_keyword.setdefault(clean, brief.id)
    started = datetime.now(UTC)
    async with unit_of_work() as db:
        earlier = await lead_searches.by_query(db, site_id, platform, list(brief_of_keyword))
    skipped_queries = recently_searched(earlier, started)
    skipped_keywords = {s["query"] for s in skipped_queries}
    searched = [k for k in brief_of_keyword if k not in skipped_keywords]
    if not searched:
        return {
            "status": "done",
            "keywords": 0,
            "posts": 0,
            "candidates": 0,
            "skippedQueries": skipped_queries,
        }, 0

    since = started - timedelta(days=LOOKBACK_DAYS)
    windows = dict.fromkeys(searched, since)
    collected = await collect_posts(
        Caller(user_id=user_id, site_id=site_id), platform, windows, PER_KEYWORD
    )
    failed_keywords = {normalize_keyword(k) for k in collected.failed_keywords}
    async with unit_of_work() as db:
        await lead_searches.record(
            db,
            user_id,
            site_id,
            platform,
            [{"query": k} for k in searched if k not in failed_keywords],
            started,
        )
    brief_of_post: dict[str, str | None] = {}
    for keyword, ids in collected.database_by_keyword.items():
        for post_id in ids:
            brief_of_post.setdefault(post_id, brief_of_keyword.get(keyword))
    fallback = briefs[0].id if briefs else None
    for post_id in collected.post_ids:
        brief_of_post.setdefault(post_id, fallback)

    async with unit_of_work() as db:
        posts = await social_posts.get_many(db, collected.post_ids)
    inserted, skipped = await save_candidates(
        user_id, site_id, run_id, author_candidates(posts, brief_of_post)
    )
    stats: dict[str, Any] = {
        "status": "done",
        "keywords": len(windows),
        "posts": len(posts),
        "fromVendor": len(collected.vendor_ids),
        "fromStore": len(set(collected.database_ids) - set(collected.vendor_ids)),
        "candidates": inserted,
        "skipped": skipped,
        "failedKeywords": collected.failed_keywords,
        "skippedQueries": skipped_queries,
    }
    if collected.error:
        stats["error"] = collected.error
    return stats, inserted


async def collect_linkedin_people(user_id: str, site_id: str, run_id: str) -> JobResult:
    if not await _running(site_id, run_id):
        return STOPPED, 0
    async with unit_of_work() as db:
        briefs = [
            b
            for b in await lead_briefs.list_enabled(db, site_id)
            if "linkedin" in (b.sources or [])
            and ((b.plan or {}).get("linkedin") or {}).get("query")
        ]
    keys = {brief.id: linkedin_query_key(brief.plan["linkedin"]) for brief in briefs}
    async with unit_of_work() as db:
        earlier = await lead_searches.by_query(db, site_id, "linkedin", list(keys.values()))
    caller = Caller(user_id=user_id, site_id=site_id)
    inserted = skipped = found = 0
    failed: list[str] = []
    pages: dict[str, int] = {}
    last_error = None
    for brief in briefs:
        plan = brief.plan["linkedin"]
        key = keys[brief.id]
        previous = earlier.get(key)
        page = next_page(previous.page if previous else None)
        try:
            people = await people_search.search_linkedin(
                caller,
                plan["query"],
                plan.get("titles") or [],
                plan.get("locations") or [],
                LINKEDIN_PER_BRIEF,
                page,
            )
        except Exception as exc:
            failed.append(brief.id)
            last_error = str(exc)
            continue
        found += len(people)
        pages[key] = page if people else MAX_LINKEDIN_PAGES
        added, passed = await save_candidates(
            user_id, site_id, run_id, linkedin_candidates(people, brief.id)
        )
        inserted += added
        skipped += passed
    async with unit_of_work() as db:
        await lead_searches.record(
            db,
            user_id,
            site_id,
            "linkedin",
            [{"query": key, "page": page} for key, page in pages.items()],
            datetime.now(UTC),
        )
    stats: dict[str, Any] = {
        "status": "error" if briefs and len(failed) == len(briefs) else "done",
        "briefs": len(briefs),
        "people": found,
        "candidates": inserted,
        "skipped": skipped,
        "failedBriefs": failed,
    }
    if last_error:
        stats["error"] = last_error
    return stats, inserted
