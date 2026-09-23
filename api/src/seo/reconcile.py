from sqlalchemy.ext.asyncio import AsyncSession

from src.seo import repository as repo
from src.seo.constants import COVERAGE_MARGIN, OWNER_COVERAGE
from src.seo.schemas import PageFactsRecord, PageSuggestionRecord, ReconcileResult

REDIRECT_STATUSES = (301, 302, 307, 308)

CONTENT_STRATEGIES = ("gsc", "cluster", "decay", "gap", "topic", "cannibalisation", "agent")


async def topic_coverage(
    db: AsyncSession, site_id: str, topic_key: str, page_id: str
) -> float | None:
    head = await repo.find_keyword(db, site_id, topic_key)
    if head is None:
        return None
    return await repo.page_coverage(db, site_id, head.id, page_id)


async def add_outcome(db: AsyncSession, site_id: str, row: PageSuggestionRecord) -> str | None:
    head = await repo.find_keyword(db, site_id, row.topic_key)
    if head is None:
        return None
    for candidate in await repo.keyword_content_pages(db, site_id, head.id):
        if candidate.coverage < OWNER_COVERAGE:
            continue
        page = await repo.get_page_facts(db, site_id, candidate.page_id)
        if page is None or not page.live or not page.indexable:
            continue
        if page.first_seen_at and page.first_seen_at > row.created_at:
            return "done"
    return None


async def edit_outcome(
    db: AsyncSession, site_id: str, row: PageSuggestionRecord, page: PageFactsRecord
) -> str | None:
    if not page.live:
        return "stale"
    strategies = set(row.strategies)
    evidence = row.evidence or {}
    snippet_changed = page.title != evidence.get("title") or (
        page.meta_description != evidence.get("meta_description")
    )
    if "ctr" in strategies and snippet_changed:
        return "done"
    if "questions" in strategies:
        wanted = set(evidence.get("questions") or [])
        if wanted and wanted & set(page.questions_answered):
            return "done"
    content_changed = bool(page.content_hash) and page.content_hash != evidence.get("content_hash")
    if strategies & set(CONTENT_STRATEGIES) and content_changed:
        coverage = await topic_coverage(db, site_id, row.topic_key, page.page_id)
        before = row.coverage_at_creation
        if coverage is not None and (before is None or coverage >= before + COVERAGE_MARGIN):
            return "done"
    return None


def delete_outcome(row: PageSuggestionRecord, page: PageFactsRecord) -> str | None:
    if page.status in REDIRECT_STATUSES or page.redirect_to or page.status == 410:
        return "done"
    if page.status == 404 or not page.live:
        return "stale"
    if (
        row.impressions_at_creation is not None
        and page.impressions_28d > row.impressions_at_creation
    ):
        return "stale"
    return None


async def reconcile(db: AsyncSession, site_id: str, pending_precompute: bool) -> ReconcileResult:
    result = ReconcileResult(pending_precompute=pending_precompute)
    closing: dict[str, str] = {}
    for row in await repo.open_suggestions(db, site_id):
        if row.id in closing:
            continue
        outcome: str | None = None
        if row.action == "add":
            outcome = await add_outcome(db, site_id, row)
        else:
            page = await repo.get_page_facts(db, site_id, row.page_id or "")
            if page is None:
                outcome = "stale"
            elif row.action == "edit":
                outcome = await edit_outcome(db, site_id, row, page)
            else:
                outcome = delete_outcome(row, page)
        if outcome is None:
            continue
        closing[row.id] = outcome
        if row.pair_id:
            closing[row.pair_id] = outcome
    for state in ("done", "stale"):
        ids = [i for i, s in closing.items() if s == state]
        count = await repo.close_suggestions(db, site_id, ids, state)
        setattr(result, state, getattr(result, state) + count)
    return result
