import re
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.sites.schemas import SiteRecord
from src.sites.service import get_site
from src.technical_seo import audit_repository as audit_repo
from src.technical_seo import repository as repo
from src.technical_seo.rules import PAGE_RULES, site_rules
from src.technical_seo.schemas import (
    AuditResultResponse,
    AuditRunChanges,
    AuditRunFilter,
    AuditRunRecord,
    AuditRunUpdateRequest,
    AuditStartRequest,
    AuditSummaryResponse,
    IssueBulkUpdateResult,
    IssueCsvFile,
    IssueCsvRow,
    IssueDecision,
    IssueGroupResponse,
    IssueUpdateRequest,
    NewPageIssue,
    NewSiteIssue,
    PageIssueBulkUpdateRequest,
    PageIssueCreateRequest,
    PageIssueFilter,
    PageIssueRecord,
    PageIssueSelector,
    SiteIssueBulkUpdateRequest,
    SiteIssueCreateRequest,
    SiteIssueFilter,
    SiteIssueRecord,
)

PAGE_ISSUE_CAP = 500

SITE_ISSUE_LIMIT = 1_000

EXPORT_LIMIT = 50_000

NO_RUN = "No such technical SEO run for this website."


async def require_run(db: AsyncSession, site_id: str, run_id: str | None = None) -> AuditRunRecord:
    run = await repo.get_run(db, site_id, run_id) if run_id else await repo.latest_run(db, site_id)
    if run is None:
        raise HTTPException(
            404,
            NO_RUN
            if run_id
            else "This website has not been audited yet — run the technical SEO check first.",
        )
    return run


async def list_runs(
    db: AsyncSession, site_id: str, filters: AuditRunFilter, paging: PaginationParams
) -> PaginatedApiResponse[AuditRunRecord]:
    return await repo.list_runs(db, site_id, filters, paging)


async def get_run(db: AsyncSession, site_id: str, run_id: str) -> AuditRunRecord:
    return await require_run(db, site_id, run_id)


async def update_run(
    db: AsyncSession, site_id: str, run_id: str, body: AuditRunUpdateRequest
) -> AuditRunRecord:
    run = await repo.update_run(db, site_id, run_id, body.to_changes())
    if run is None:
        raise HTTPException(404, NO_RUN)
    return run


async def delete_run(db: AsyncSession, site_id: str, run_id: str) -> AuditRunRecord:
    run = await require_run(db, site_id, run_id)
    await repo.delete_run(db, site_id, run.id)
    return run


async def list_site_issues(
    db: AsyncSession,
    site_id: str,
    run_id: str | None,
    filters: SiteIssueFilter,
    paging: PaginationParams,
) -> PaginatedApiResponse[SiteIssueRecord]:
    run = await require_run(db, site_id, run_id)
    return await repo.list_site_issues(db, run.id, filters, paging)


async def get_site_issue(db: AsyncSession, site_id: str, issue_id: str) -> SiteIssueRecord:
    issue = await repo.get_site_issue(db, site_id, issue_id)
    if issue is None:
        raise HTTPException(404, "No such site-wide issue on this website.")
    return issue


async def create_site_issue(
    db: AsyncSession, user_id: str, site_id: str, body: SiteIssueCreateRequest
) -> SiteIssueRecord:
    run = await require_run(db, site_id, body.run_id)
    if await repo.count_site_issues(db, run.id, SiteIssueFilter(kinds=[body.kind])) > 0:
        raise HTTPException(409, f'This run already carries the site-wide "{body.kind}" check.')
    return await repo.create_site_issue(db, user_id, site_id, run.id, body.to_new())


async def update_site_issue(
    db: AsyncSession, site_id: str, issue_id: str, body: IssueUpdateRequest
) -> SiteIssueRecord:
    issue = await repo.update_site_issue(db, site_id, issue_id, body.to_changes())
    if issue is None:
        raise HTTPException(404, "No such site-wide issue on this website.")
    return issue


async def delete_site_issue(db: AsyncSession, site_id: str, issue_id: str) -> SiteIssueRecord:
    issue = await get_site_issue(db, site_id, issue_id)
    await repo.delete_site_issue(db, site_id, issue.id)
    return issue


async def update_site_issues_by_kind(
    db: AsyncSession, site_id: str, body: SiteIssueBulkUpdateRequest
) -> IssueBulkUpdateResult:
    run = await require_run(db, site_id, body.run_id)
    updated = await repo.update_site_issues_by_kind(db, run.id, body.kind, body.to_changes())
    if updated == 0:
        raise HTTPException(404, f'No site-wide "{body.kind}" issue in this run to change.')
    return IssueBulkUpdateResult(run_id=run.id, updated=updated)


async def list_page_issues(
    db: AsyncSession,
    site_id: str,
    run_id: str | None,
    filters: PageIssueFilter,
    paging: PaginationParams,
) -> PaginatedApiResponse[PageIssueRecord]:
    run = await require_run(db, site_id, run_id)
    return await repo.list_page_issues(db, run.id, filters, paging)


async def get_page_issue(db: AsyncSession, site_id: str, issue_id: str) -> PageIssueRecord:
    issue = await repo.get_page_issue(db, site_id, issue_id)
    if issue is None:
        raise HTTPException(404, "No such page issue on this website.")
    return issue


async def resolve_page_id(
    db: AsyncSession, site_id: str, page_id: str | None, url: str | None
) -> str:
    if page_id:
        if not await audit_repo.page_exists(db, site_id, page_id):
            raise HTTPException(404, f"No page {page_id} on this website.")
        return page_id
    target = (url or "").strip()
    if not target:
        raise HTTPException(400, "A page issue needs a pageId or a url.")
    found = await audit_repo.page_id_by_url(db, site_id, target)
    if not found:
        raise HTTPException(404, f"No page on record at {target}.")
    return found


async def create_page_issue(
    db: AsyncSession, user_id: str, site_id: str, body: PageIssueCreateRequest
) -> PageIssueRecord:
    run = await require_run(db, site_id, body.run_id)
    page_id = await resolve_page_id(db, site_id, body.page_id, body.url)
    clash = await repo.count_page_issues(
        db, run.id, PageIssueFilter(kinds=[body.kind], page_id=page_id)
    )
    if clash > 0:
        raise HTTPException(409, f'This run already carries the "{body.kind}" check on that page.')
    return await repo.create_page_issue(db, user_id, site_id, run.id, body.to_new(page_id))


async def update_page_issue(
    db: AsyncSession, site_id: str, issue_id: str, body: IssueUpdateRequest
) -> PageIssueRecord:
    issue = await repo.update_page_issue(db, site_id, issue_id, body.to_changes())
    if issue is None:
        raise HTTPException(404, "No such page issue on this website.")
    return issue


async def delete_page_issue(db: AsyncSession, site_id: str, issue_id: str) -> PageIssueRecord:
    issue = await get_page_issue(db, site_id, issue_id)
    await repo.delete_page_issue(db, site_id, issue.id)
    return issue


async def update_page_issues_by(
    db: AsyncSession, site_id: str, body: PageIssueBulkUpdateRequest
) -> IssueBulkUpdateResult:
    run = await require_run(db, site_id, body.run_id)
    updated = await repo.update_page_issues_by(db, run.id, body.selector(), body.to_changes())
    if updated == 0:
        raise HTTPException(404, "No page issue in this run matched.")
    return IssueBulkUpdateResult(run_id=run.id, updated=updated)


async def run_audit(
    db: AsyncSession, user_id: str, site_id: str, body: AuditStartRequest
) -> AuditResultResponse:
    run, checks = await audit(db, user_id, site_id, body.trigger)
    return AuditResultResponse.from_summary(await summary(db, site_id, run.id), checks)


async def audit(
    db: AsyncSession, user_id: str, site_id: str, trigger: str
) -> tuple[AuditRunRecord, int]:
    site: SiteRecord = await get_site(db, user_id, site_id)
    previous = await repo.latest_run(db, site_id)

    if previous is not None:
        prior_site = await repo.all_site_issues(
            db, previous.id, SiteIssueFilter(), SITE_ISSUE_LIMIT
        )
        prior_pages = await repo.all_page_issues(
            db, previous.id, PageIssueFilter(), SITE_ISSUE_LIMIT
        )
    else:
        prior_site, prior_pages = [], []

    site_decisions: dict[str, IssueDecision] = {}
    for row in prior_site:
        decision = IssueDecision.from_issue(row)
        if decision.decided:
            site_decisions[row.kind] = decision

    page_decisions: dict[tuple[str, str], IssueDecision] = {}
    for row in prior_pages:
        decision = IssueDecision.from_issue(row)
        if decision.decided and row.url:
            page_decisions[(row.kind, row.url)] = decision

    page_rows: list[NewPageIssue] = []
    for rule in PAGE_RULES:
        matched = await audit_repo.count_matching(db, site_id, rule.where)
        if matched == 0:
            continue
        ids = await audit_repo.worst_matching(db, site_id, rule.where, PAGE_ISSUE_CAP)
        page_rows.extend(
            NewPageIssue(
                kind=rule.kind,
                issue=rule.issue,
                severity=rule.severity,
                page_id=page_id,
                matched_pages=matched,
                issue_type=rule.issue_type,
            )
            for page_id in ids
        )

    rules = site_rules(site, await audit_repo.render_counts(db, site_id))
    site_rows = [
        NewSiteIssue(
            kind=r.kind,
            issue=r.issue,
            severity=r.severity,
            issue_type=r.issue_type,
        )
        for r in rules
        if r.holds
    ]

    run = await repo.create_run(db, user_id, site_id, trigger)
    await repo.insert_site_issues(db, user_id, site_id, run.id, site_rows)
    await repo.insert_page_issues(db, user_id, site_id, run.id, page_rows)
    await carry_forward(db, run.id, site_decisions, page_decisions)

    checks = len(PAGE_RULES) + len(rules)
    finished = await repo.update_run(
        db,
        site_id,
        run.id,
        AuditRunChanges(
            rules_run=checks,
            site_issues_found=len(site_rows),
            page_issues_found=len(page_rows),
            finished_at=datetime.now(UTC),
        ),
    )
    return (finished or run), checks


async def carry_forward(
    db: AsyncSession,
    run_id: str,
    site_decisions: dict[str, IssueDecision],
    page_decisions: dict[tuple[str, str], IssueDecision],
) -> None:
    for kind, decision in site_decisions.items():
        await repo.update_site_issues_by_kind(db, run_id, kind, decision.to_changes())

    for (kind, url), decision in page_decisions.items():
        await repo.update_page_issues_by(
            db, run_id, PageIssueSelector(kind=kind, url=url), decision.to_changes()
        )


async def list_groups(
    db: AsyncSession, site_id: str, run_id: str | None, state: str
) -> list[IssueGroupResponse]:
    run = await require_run(db, site_id, run_id)
    site_rows = await repo.all_site_issues(
        db, run.id, SiteIssueFilter(state=state), SITE_ISSUE_LIMIT
    )
    by_kind = await repo.group_page_issues(db, run.id, state)

    groups = [IssueGroupResponse.from_site_issue(i, state) for i in site_rows] + [
        IssueGroupResponse.from_page_group(g, state) for g in by_kind
    ]
    groups.sort(key=IssueGroupResponse.sort_key)
    return groups


async def summary(
    db: AsyncSession, site_id: str, run_id: str | None = None
) -> AuditSummaryResponse:
    run = await require_run(db, site_id, run_id)
    counts = await repo.count_issues_by_state(db, run.id)
    groups = await list_groups(db, site_id, run.id, "open")
    return AuditSummaryResponse.build(run, counts, groups)


def slug(domain: str) -> str:
    lowered = domain.lower().removeprefix("www.")
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    lowered = re.sub(r"^-|-$", "", lowered)
    return lowered or "site"


async def csv(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    run_id: str | None,
    state: str,
    kinds: list[str] | None,
) -> IssueCsvFile:
    site = await get_site(db, user_id, site_id)
    run = await require_run(db, site_id, run_id)

    site_issues = await repo.all_site_issues(
        db, run.id, SiteIssueFilter(state=state, kinds=kinds), SITE_ISSUE_LIMIT
    )
    page_issues = await repo.all_page_issues(
        db, run.id, PageIssueFilter(state=state, kinds=kinds), EXPORT_LIMIT
    )

    rows = [IssueCsvRow.from_site_issue(r, state) for r in site_issues] + [
        IssueCsvRow.from_page_issue(r, state) for r in page_issues
    ]
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    return IssueCsvFile.build(f"{slug(site.domain)}-{state}-issues-{stamp}.csv", rows)
