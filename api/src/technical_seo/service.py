import re
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.sites.schemas import SiteRecord
from src.site_pages.repositories.pages import site_pages
from src.sites.service import site_service
from src.technical_seo.audit_repository import audit_rules
from src.technical_seo.repository import site_audit_runs, site_issues, site_page_issues
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
    IssueCountsByScope,
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
    PageIssueGroup,
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

EXAMPLE_URLS = 3

NO_RUN = "No such technical SEO run for this website."


def slug(domain: str) -> str:
    lowered = domain.lower().removeprefix("www.")
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    lowered = re.sub(r"^-|-$", "", lowered)
    return lowered or "site"


class TechnicalSeoService:
    async def require_run(
        self, db: AsyncSession, site_id: str, run_id: str | None = None
    ) -> AuditRunRecord:
        run = (
            await site_audit_runs.get(db, site_id, run_id)
            if run_id
            else await site_audit_runs.latest(db, site_id)
        )
        if run is None:
            raise HTTPException(
                404,
                NO_RUN
                if run_id
                else "This website has not been audited yet — run the technical SEO check first.",
            )
        return run

    async def list_runs(
        self, db: AsyncSession, site_id: str, filters: AuditRunFilter, paging: PaginationParams
    ) -> PaginatedApiResponse[AuditRunRecord]:
        return await site_audit_runs.list(db, site_id, filters, paging)

    async def get_run(self, db: AsyncSession, site_id: str, run_id: str) -> AuditRunRecord:
        return await self.require_run(db, site_id, run_id)

    async def update_run(
        self, db: AsyncSession, site_id: str, run_id: str, body: AuditRunUpdateRequest
    ) -> AuditRunRecord:
        run = await site_audit_runs.update(db, site_id, run_id, body.to_changes())
        if run is None:
            raise HTTPException(404, NO_RUN)
        return run

    async def delete_run(self, db: AsyncSession, site_id: str, run_id: str) -> AuditRunRecord:
        run = await self.require_run(db, site_id, run_id)
        await site_audit_runs.delete(db, site_id, run.id)
        return run

    async def list_site_issues(
        self,
        db: AsyncSession,
        site_id: str,
        run_id: str | None,
        filters: SiteIssueFilter,
        paging: PaginationParams,
    ) -> PaginatedApiResponse[SiteIssueRecord]:
        run = await self.require_run(db, site_id, run_id)
        return await site_issues.list(db, run.id, filters, paging)

    async def get_site_issue(
        self, db: AsyncSession, site_id: str, issue_id: str
    ) -> SiteIssueRecord:
        issue = await site_issues.get(db, site_id, issue_id)
        if issue is None:
            raise HTTPException(404, "No such site-wide issue on this website.")
        return issue

    async def create_site_issue(
        self, db: AsyncSession, user_id: str, site_id: str, body: SiteIssueCreateRequest
    ) -> SiteIssueRecord:
        run = await self.require_run(db, site_id, body.run_id)
        if await site_issues.count(db, run.id, SiteIssueFilter(kinds=[body.kind])) > 0:
            raise HTTPException(409, f'This run already carries the site-wide "{body.kind}" check.')
        return await site_issues.create(db, user_id, site_id, run.id, body.to_new())

    async def update_site_issue(
        self, db: AsyncSession, site_id: str, issue_id: str, body: IssueUpdateRequest
    ) -> SiteIssueRecord:
        issue = await site_issues.update(db, site_id, issue_id, body.to_changes())
        if issue is None:
            raise HTTPException(404, "No such site-wide issue on this website.")
        return issue

    async def delete_site_issue(
        self, db: AsyncSession, site_id: str, issue_id: str
    ) -> SiteIssueRecord:
        issue = await self.get_site_issue(db, site_id, issue_id)
        await site_issues.delete(db, site_id, issue.id)
        return issue

    async def update_site_issues_by_kind(
        self, db: AsyncSession, site_id: str, body: SiteIssueBulkUpdateRequest
    ) -> IssueBulkUpdateResult:
        run = await self.require_run(db, site_id, body.run_id)
        updated = await site_issues.update_by_kind(db, run.id, body.kind, body.to_changes())
        if updated == 0:
            raise HTTPException(404, f'No site-wide "{body.kind}" issue in this run to change.')
        return IssueBulkUpdateResult(run_id=run.id, updated=updated)

    async def list_page_issues(
        self,
        db: AsyncSession,
        site_id: str,
        run_id: str | None,
        filters: PageIssueFilter,
        paging: PaginationParams,
    ) -> PaginatedApiResponse[PageIssueRecord]:
        run = await self.require_run(db, site_id, run_id)
        scoped = await self._resolve_url_filter(db, site_id, filters)
        if scoped is None:
            return PaginatedApiResponse[PageIssueRecord](
                data=[],
                pagination=PaginationService.build_pagination_meta(
                    0, paging.page, paging.page_size
                ),
            )
        page = await site_page_issues.list(db, run.id, scoped, paging)
        return PaginatedApiResponse[PageIssueRecord](
            data=await self._with_urls(db, site_id, page.data), pagination=page.pagination
        )

    async def _resolve_url_filter(
        self, db: AsyncSession, site_id: str, filters: PageIssueFilter
    ) -> PageIssueFilter | None:
        if not filters.url:
            return filters
        page_id = await site_pages.id_by_url(db, site_id, filters.url)
        if page_id is None or (filters.page_id and filters.page_id != page_id):
            return None
        return filters.model_copy(update={"page_id": page_id, "url": None})

    async def _with_urls(
        self, db: AsyncSession, site_id: str, issues: list[PageIssueRecord]
    ) -> list[PageIssueRecord]:
        urls = await site_pages.urls_by_ids(db, site_id, [i.page_id for i in issues])
        found = [i.model_copy(update={"url": urls.get(i.page_id)}) for i in issues]
        return sorted(found, key=lambda i: (i.severity, i.kind, i.url or ""))

    async def _with_url(
        self, db: AsyncSession, site_id: str, issue: PageIssueRecord
    ) -> PageIssueRecord:
        return (await self._with_urls(db, site_id, [issue]))[0]

    async def get_page_issue(
        self, db: AsyncSession, site_id: str, issue_id: str
    ) -> PageIssueRecord:
        issue = await site_page_issues.get(db, site_id, issue_id)
        if issue is None:
            raise HTTPException(404, "No such page issue on this website.")
        return await self._with_url(db, site_id, issue)

    async def resolve_page_id(
        self, db: AsyncSession, site_id: str, page_id: str | None, url: str | None
    ) -> str:
        if page_id:
            if not await site_pages.exists(db, site_id, page_id):
                raise HTTPException(404, f"No page {page_id} on this website.")
            return page_id
        target = (url or "").strip()
        if not target:
            raise HTTPException(400, "A page issue needs a pageId or a url.")
        found = await site_pages.id_by_url(db, site_id, target)
        if not found:
            raise HTTPException(404, f"No page on record at {target}.")
        return found

    async def create_page_issue(
        self, db: AsyncSession, user_id: str, site_id: str, body: PageIssueCreateRequest
    ) -> PageIssueRecord:
        run = await self.require_run(db, site_id, body.run_id)
        page_id = await self.resolve_page_id(db, site_id, body.page_id, body.url)
        clash = await site_page_issues.count(
            db, run.id, PageIssueFilter(kinds=[body.kind], page_id=page_id)
        )
        if clash > 0:
            raise HTTPException(
                409, f'This run already carries the "{body.kind}" check on that page.'
            )
        created = await site_page_issues.create(db, user_id, site_id, run.id, body.to_new(page_id))
        return await self._with_url(db, site_id, created)

    async def update_page_issue(
        self, db: AsyncSession, site_id: str, issue_id: str, body: IssueUpdateRequest
    ) -> PageIssueRecord:
        issue = await site_page_issues.update(db, site_id, issue_id, body.to_changes())
        if issue is None:
            raise HTTPException(404, "No such page issue on this website.")
        return await self._with_url(db, site_id, issue)

    async def delete_page_issue(
        self, db: AsyncSession, site_id: str, issue_id: str
    ) -> PageIssueRecord:
        issue = await self.get_page_issue(db, site_id, issue_id)
        await site_page_issues.delete(db, site_id, issue.id)
        return issue

    async def update_page_issues_by(
        self, db: AsyncSession, site_id: str, body: PageIssueBulkUpdateRequest
    ) -> IssueBulkUpdateResult:
        run = await self.require_run(db, site_id, body.run_id)
        url_page_ids = None
        if body.url:
            page_id = await site_pages.id_by_url(db, site_id, body.url)
            url_page_ids = [page_id] if page_id else []
        updated = await site_page_issues.update_by(
            db, run.id, body.selector(url_page_ids), body.to_changes()
        )
        if updated == 0:
            raise HTTPException(404, "No page issue in this run matched.")
        return IssueBulkUpdateResult(run_id=run.id, updated=updated)

    async def run_audit(
        self, db: AsyncSession, user_id: str, site_id: str, body: AuditStartRequest
    ) -> AuditResultResponse:
        run, checks = await self.audit(db, user_id, site_id, body.trigger)
        return AuditResultResponse.from_summary(await self.summary(db, site_id, run.id), checks)

    async def audit(
        self, db: AsyncSession, user_id: str, site_id: str, trigger: str
    ) -> tuple[AuditRunRecord, int]:
        site: SiteRecord = await site_service.get(db, user_id, site_id)
        previous = await site_audit_runs.latest(db, site_id)

        if previous is not None:
            prior_site = await site_issues.list_all(
                db, previous.id, SiteIssueFilter(), SITE_ISSUE_LIMIT
            )
            prior_pages = await self._with_urls(
                db,
                site_id,
                await site_page_issues.list_all(
                    db, previous.id, PageIssueFilter(), SITE_ISSUE_LIMIT
                ),
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
            matched = await audit_rules.count_matching(db, site_id, rule.where)
            if matched == 0:
                continue
            ids = await audit_rules.worst_matching(db, site_id, rule.where, PAGE_ISSUE_CAP)
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

        rules = site_rules(site, await audit_rules.render_counts(db, site_id))
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

        run = await site_audit_runs.create(db, user_id, site_id, trigger)
        await site_issues.create_many(db, user_id, site_id, run.id, site_rows)
        await site_page_issues.create_many(db, user_id, site_id, run.id, page_rows)
        await self.carry_forward(db, site_id, run.id, site_decisions, page_decisions)

        checks = len(PAGE_RULES) + len(rules)
        finished = await site_audit_runs.update(
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
        self,
        db: AsyncSession,
        site_id: str,
        run_id: str,
        site_decisions: dict[str, IssueDecision],
        page_decisions: dict[tuple[str, str], IssueDecision],
    ) -> None:
        for kind, decision in site_decisions.items():
            await site_issues.update_by_kind(db, run_id, kind, decision.to_changes())

        page_ids = await site_pages.ids_by_urls(db, site_id, [url for _, url in page_decisions])
        for (kind, url), decision in page_decisions.items():
            page_id = page_ids.get(url)
            if page_id is None:
                continue
            await site_page_issues.update_by(
                db, run_id, PageIssueSelector(kind=kind, page_id=page_id), decision.to_changes()
            )

    async def list_groups(
        self, db: AsyncSession, site_id: str, run_id: str | None, state: str
    ) -> list[IssueGroupResponse]:
        run = await self.require_run(db, site_id, run_id)
        site_rows = await site_issues.list_all(
            db, run.id, SiteIssueFilter(state=state), SITE_ISSUE_LIMIT
        )
        by_kind = await self._page_groups(db, site_id, run.id, state)

        groups = [IssueGroupResponse.from_site_issue(i, state) for i in site_rows] + [
            IssueGroupResponse.from_page_group(g, state) for g in by_kind
        ]
        groups.sort(key=IssueGroupResponse.sort_key)
        return groups

    async def _page_groups(
        self, db: AsyncSession, site_id: str, run_id: str, state: str
    ) -> list[PageIssueGroup]:
        grouped = await site_page_issues.group_by_kind(db, run_id, state)
        urls = await site_pages.urls_by_ids(
            db, site_id, list({p for g in grouped for p in g.page_ids})
        )
        return [
            PageIssueGroup(
                kind=g.kind,
                issue=g.issue,
                severity=g.severity,
                matched=g.matched,
                pages=sum(1 for p in g.page_ids if p in urls),
                examples=sorted(urls[p] for p in g.page_ids if p in urls)[:EXAMPLE_URLS],
                reason=g.reason,
                issue_type=g.issue_type,
            )
            for g in grouped
        ]

    async def summary(
        self, db: AsyncSession, site_id: str, run_id: str | None = None
    ) -> AuditSummaryResponse:
        run = await self.require_run(db, site_id, run_id)
        counts = IssueCountsByScope(
            site=await site_issues.count_by_state(db, run.id),
            pages=await site_page_issues.count_by_state(db, run.id),
        )
        groups = await self.list_groups(db, site_id, run.id, "open")
        return AuditSummaryResponse.build(run, counts, groups)

    async def csv(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        run_id: str | None,
        state: str,
        kinds: list[str] | None,
    ) -> IssueCsvFile:
        site = await site_service.get(db, user_id, site_id)
        run = await self.require_run(db, site_id, run_id)

        site_rows = await site_issues.list_all(
            db, run.id, SiteIssueFilter(state=state, kinds=kinds), SITE_ISSUE_LIMIT
        )
        page_issues = await self._with_urls(
            db,
            site_id,
            await site_page_issues.list_all(
                db, run.id, PageIssueFilter(state=state, kinds=kinds), EXPORT_LIMIT
            ),
        )

        rows = [IssueCsvRow.from_site_issue(r, state) for r in site_rows] + [
            IssueCsvRow.from_page_issue(r, state) for r in page_issues
        ]
        stamp = datetime.now(UTC).strftime("%Y-%m-%d")
        return IssueCsvFile.build(f"{slug(site.domain)}-{state}-issues-{stamp}.csv", rows)


technical_seo_service = TechnicalSeoService()
