from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.site_pages.models.site_page import SitePage
from src.technical_seo.models.site_audit_run import SiteAuditRun
from src.technical_seo.models.site_issue import SiteIssue
from src.technical_seo.models.site_page_issue import SitePageIssue
from src.technical_seo.schemas import (
    AuditRunChanges,
    AuditRunFilter,
    AuditRunRecord,
    IssueChanges,
    IssueCounts,
    IssueCountsByScope,
    NewPageIssue,
    NewSiteIssue,
    PageIssueFilter,
    PageIssueGroup,
    PageIssueRecord,
    PageIssueSelector,
    SiteIssueFilter,
    SiteIssueRecord,
)


def _page_record(issue: SitePageIssue, url: str | None) -> PageIssueRecord:
    return PageIssueRecord.model_validate(issue).model_copy(update={"url": url})


async def _count(db: AsyncSession, query: Select) -> int:
    return (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()


async def create_run(db: AsyncSession, user_id: str, site_id: str, trigger: str) -> AuditRunRecord:
    now = datetime.now(UTC)
    run = SiteAuditRun(
        id=uid("sar"),
        user_id=user_id,
        site_id=site_id,
        trigger=trigger,
        rules_run=0,
        site_issues_found=0,
        page_issues_found=0,
        created_at=now,
        updated_at=now,
    )
    db.add(run)
    await db.flush()
    return AuditRunRecord.model_validate(run)


async def _run_row(db: AsyncSession, site_id: str, run_id: str) -> SiteAuditRun | None:
    result = await db.execute(
        select(SiteAuditRun)
        .where(SiteAuditRun.site_id == site_id, SiteAuditRun.id == run_id)
        .limit(1)
    )
    return result.scalars().first()


async def get_run(db: AsyncSession, site_id: str, run_id: str) -> AuditRunRecord | None:
    row = await _run_row(db, site_id, run_id)
    return None if row is None else AuditRunRecord.model_validate(row)


async def latest_run(db: AsyncSession, site_id: str) -> AuditRunRecord | None:
    result = await db.execute(
        select(SiteAuditRun)
        .where(SiteAuditRun.site_id == site_id)
        .order_by(SiteAuditRun.seq.desc())
        .limit(1)
    )
    row = result.scalars().first()
    return None if row is None else AuditRunRecord.model_validate(row)


async def list_runs(
    db: AsyncSession, site_id: str, filters: AuditRunFilter, paging: PaginationParams
) -> PaginatedApiResponse[AuditRunRecord]:
    conds = [SiteAuditRun.site_id == site_id]
    if filters.trigger:
        conds.append(SiteAuditRun.trigger == filters.trigger)
    if filters.reviewed is True:
        conds.append(SiteAuditRun.reviewed_at.is_not(None))
    if filters.reviewed is False:
        conds.append(SiteAuditRun.reviewed_at.is_(None))
    query = select(SiteAuditRun).where(*conds)
    rows = (
        (
            await db.execute(
                query.order_by(SiteAuditRun.seq.desc())
                .offset(paging.offset)
                .limit(paging.page_size)
            )
        )
        .scalars()
        .all()
    )
    total = await _count(db, query)
    return PaginatedApiResponse[AuditRunRecord](
        data=[AuditRunRecord.model_validate(r) for r in rows],
        pagination=PaginationService.build_pagination_meta(total, paging.page, paging.page_size),
    )


async def update_run(
    db: AsyncSession, site_id: str, run_id: str, patch: AuditRunChanges
) -> AuditRunRecord | None:
    run = await _run_row(db, site_id, run_id)
    if run is None:
        return None
    _apply(run, patch.changes())
    await db.flush()
    return AuditRunRecord.model_validate(run)


async def delete_run(db: AsyncSession, site_id: str, run_id: str) -> None:
    run = await _run_row(db, site_id, run_id)
    if run is not None:
        await db.delete(run)
        await db.flush()


def _site_issue(user_id: str, site_id: str, run_id: str, row: NewSiteIssue) -> SiteIssue:
    now = datetime.now(UTC)
    return SiteIssue(
        id=uid("sis"),
        user_id=user_id,
        site_id=site_id,
        run_id=run_id,
        kind=row.kind,
        issue=row.issue,
        severity=row.severity,
        state=row.state,
        llm_check_required=row.llm_check_required,
        issue_type=row.issue_type,
        created_at=now,
        updated_at=now,
    )


def _page_issue(user_id: str, site_id: str, run_id: str, row: NewPageIssue) -> SitePageIssue:
    now = datetime.now(UTC)
    return SitePageIssue(
        id=uid("spi"),
        user_id=user_id,
        site_id=site_id,
        run_id=run_id,
        page_id=row.page_id,
        kind=row.kind,
        issue=row.issue,
        severity=row.severity,
        state=row.state,
        matched_pages=row.matched_pages,
        llm_check_required=row.llm_check_required,
        issue_type=row.issue_type,
        created_at=now,
        updated_at=now,
    )


async def insert_site_issues(
    db: AsyncSession, user_id: str, site_id: str, run_id: str, rows: list[NewSiteIssue]
) -> int:
    if not rows:
        return 0
    db.add_all([_site_issue(user_id, site_id, run_id, row) for row in rows])
    await db.flush()
    return len(rows)


async def insert_page_issues(
    db: AsyncSession, user_id: str, site_id: str, run_id: str, rows: list[NewPageIssue]
) -> int:
    if not rows:
        return 0
    db.add_all([_page_issue(user_id, site_id, run_id, row) for row in rows])
    await db.flush()
    return len(rows)


async def create_site_issue(
    db: AsyncSession, user_id: str, site_id: str, run_id: str, row: NewSiteIssue
) -> SiteIssueRecord:
    issue = _site_issue(user_id, site_id, run_id, row)
    db.add(issue)
    await db.flush()
    return SiteIssueRecord.model_validate(issue)


async def create_page_issue(
    db: AsyncSession, user_id: str, site_id: str, run_id: str, row: NewPageIssue
) -> PageIssueRecord:
    issue = _page_issue(user_id, site_id, run_id, row)
    db.add(issue)
    await db.flush()
    url = (
        await db.execute(select(SitePage.url).where(SitePage.id == issue.page_id).limit(1))
    ).scalar_one_or_none()
    return _page_record(issue, url)


async def _site_issue_row(db: AsyncSession, site_id: str, issue_id: str) -> SiteIssue | None:
    result = await db.execute(
        select(SiteIssue).where(SiteIssue.site_id == site_id, SiteIssue.id == issue_id).limit(1)
    )
    return result.scalars().first()


async def get_site_issue(db: AsyncSession, site_id: str, issue_id: str) -> SiteIssueRecord | None:
    row = await _site_issue_row(db, site_id, issue_id)
    return None if row is None else SiteIssueRecord.model_validate(row)


async def _page_issue_row(
    db: AsyncSession, site_id: str, issue_id: str
) -> tuple[SitePageIssue, str] | None:
    result = await db.execute(
        select(SitePageIssue, SitePage.url)
        .join(SitePage, SitePage.id == SitePageIssue.page_id)
        .where(SitePageIssue.site_id == site_id, SitePageIssue.id == issue_id)
        .limit(1)
    )
    row = result.first()
    return (row[0], row[1]) if row else None


async def get_page_issue(db: AsyncSession, site_id: str, issue_id: str) -> PageIssueRecord | None:
    found = await _page_issue_row(db, site_id, issue_id)
    return None if found is None else _page_record(*found)


def _site_issue_query(run_id: str, filters: SiteIssueFilter) -> Select:
    conds: list[Any] = [SiteIssue.run_id == run_id]
    if filters.state:
        conds.append(SiteIssue.state == filters.state)
    if filters.severity:
        conds.append(SiteIssue.severity == filters.severity)
    if filters.kinds:
        conds.append(SiteIssue.kind.in_(filters.kinds))
    if filters.llm_check_pending is True:
        conds.extend(
            [SiteIssue.llm_check_required.is_(True), SiteIssue.llm_check_done_at.is_(None)]
        )
    if filters.llm_check_pending is False:
        conds.append(SiteIssue.llm_check_done_at.is_not(None))
    if filters.issue_type:
        conds.append(SiteIssue.issue_type == filters.issue_type)
    return select(SiteIssue).where(*conds).order_by(SiteIssue.severity, SiteIssue.kind)


async def list_site_issues(
    db: AsyncSession, run_id: str, filters: SiteIssueFilter, paging: PaginationParams
) -> PaginatedApiResponse[SiteIssueRecord]:
    query = _site_issue_query(run_id, filters)
    rows = (await db.execute(query.offset(paging.offset).limit(paging.page_size))).scalars().all()
    total = await _count(db, query)
    return PaginatedApiResponse[SiteIssueRecord](
        data=[SiteIssueRecord.model_validate(r) for r in rows],
        pagination=PaginationService.build_pagination_meta(total, paging.page, paging.page_size),
    )


async def all_site_issues(
    db: AsyncSession, run_id: str, filters: SiteIssueFilter, limit: int
) -> list[SiteIssueRecord]:
    rows = (await db.execute(_site_issue_query(run_id, filters).limit(limit))).scalars().all()
    return [SiteIssueRecord.model_validate(r) for r in rows]


async def count_site_issues(db: AsyncSession, run_id: str, filters: SiteIssueFilter) -> int:
    return await _count(db, _site_issue_query(run_id, filters))


def _page_issue_query(run_id: str, filters: PageIssueFilter) -> Select:
    conds: list[Any] = [SitePageIssue.run_id == run_id]
    if filters.state:
        conds.append(SitePageIssue.state == filters.state)
    if filters.severity:
        conds.append(SitePageIssue.severity == filters.severity)
    if filters.kinds:
        conds.append(SitePageIssue.kind.in_(filters.kinds))
    if filters.llm_check_pending is True:
        conds.extend(
            [SitePageIssue.llm_check_required.is_(True), SitePageIssue.llm_check_done_at.is_(None)]
        )
    if filters.llm_check_pending is False:
        conds.append(SitePageIssue.llm_check_done_at.is_not(None))
    if filters.issue_type:
        conds.append(SitePageIssue.issue_type == filters.issue_type)
    if filters.page_id:
        conds.append(SitePageIssue.page_id == filters.page_id)
    if filters.url:
        conds.append(SitePage.url == filters.url)
    return (
        select(SitePageIssue, SitePage.url)
        .join(SitePage, SitePage.id == SitePageIssue.page_id)
        .where(*conds)
        .order_by(SitePageIssue.severity, SitePageIssue.kind, SitePage.url)
    )


async def list_page_issues(
    db: AsyncSession, run_id: str, filters: PageIssueFilter, paging: PaginationParams
) -> PaginatedApiResponse[PageIssueRecord]:
    query = _page_issue_query(run_id, filters)
    rows = (await db.execute(query.offset(paging.offset).limit(paging.page_size))).all()
    total = await _count(db, query)
    return PaginatedApiResponse[PageIssueRecord](
        data=[_page_record(row[0], row[1]) for row in rows],
        pagination=PaginationService.build_pagination_meta(total, paging.page, paging.page_size),
    )


async def all_page_issues(
    db: AsyncSession, run_id: str, filters: PageIssueFilter, limit: int
) -> list[PageIssueRecord]:
    rows = (await db.execute(_page_issue_query(run_id, filters).limit(limit))).all()
    return [_page_record(row[0], row[1]) for row in rows]


async def count_page_issues(db: AsyncSession, run_id: str, filters: PageIssueFilter) -> int:
    return await _count(db, _page_issue_query(run_id, filters))


def _apply(row: Any, changes: dict[str, Any]) -> None:
    for key, value in changes.items():
        setattr(row, key, value)
    row.updated_at = datetime.now(UTC)


async def update_site_issue(
    db: AsyncSession, site_id: str, issue_id: str, patch: IssueChanges
) -> SiteIssueRecord | None:
    issue = await _site_issue_row(db, site_id, issue_id)
    if issue is None:
        return None
    _apply(issue, patch.changes())
    await db.flush()
    return SiteIssueRecord.model_validate(issue)


async def update_page_issue(
    db: AsyncSession, site_id: str, issue_id: str, patch: IssueChanges
) -> PageIssueRecord | None:
    found = await _page_issue_row(db, site_id, issue_id)
    if found is None:
        return None
    issue, url = found
    _apply(issue, patch.changes())
    await db.flush()
    return _page_record(issue, url)


async def delete_site_issue(db: AsyncSession, site_id: str, issue_id: str) -> None:
    issue = await _site_issue_row(db, site_id, issue_id)
    if issue is not None:
        await db.delete(issue)
        await db.flush()


async def delete_page_issue(db: AsyncSession, site_id: str, issue_id: str) -> None:
    result = await db.execute(
        select(SitePageIssue)
        .where(SitePageIssue.site_id == site_id, SitePageIssue.id == issue_id)
        .limit(1)
    )
    issue = result.scalars().first()
    if issue is not None:
        await db.delete(issue)
        await db.flush()


async def update_site_issues_by_kind(
    db: AsyncSession, run_id: str, kind: str, patch: IssueChanges
) -> int:
    result = await db.execute(
        update(SiteIssue)
        .where(SiteIssue.run_id == run_id, SiteIssue.kind == kind)
        .values(**patch.changes(), updated_at=datetime.now(UTC))
    )
    return result.rowcount or 0


async def update_page_issues_by(
    db: AsyncSession, run_id: str, selector: PageIssueSelector, patch: IssueChanges
) -> int:
    conds: list[Any] = [SitePageIssue.run_id == run_id]
    if selector.kind:
        conds.append(SitePageIssue.kind == selector.kind)
    if selector.page_id:
        conds.append(SitePageIssue.page_id == selector.page_id)
    if selector.url:
        conds.append(
            SitePageIssue.page_id.in_(select(SitePage.id).where(SitePage.url == selector.url))
        )
    result = await db.execute(
        update(SitePageIssue).where(*conds).values(**patch.changes(), updated_at=datetime.now(UTC))
    )
    return result.rowcount or 0


async def count_issues_by_state(db: AsyncSession, run_id: str) -> IssueCountsByScope:
    async def counts(model: Any) -> IssueCounts:
        row = (
            await db.execute(
                select(
                    func.count().filter(model.state == "open"),
                    func.count().filter(model.state == "rejected"),
                ).where(model.run_id == run_id)
            )
        ).first()
        return IssueCounts(open=row[0], rejected=row[1]) if row else IssueCounts()

    return IssueCountsByScope(site=await counts(SiteIssue), pages=await counts(SitePageIssue))


async def group_page_issues(db: AsyncSession, run_id: str, state: str) -> list[PageIssueGroup]:
    result = await db.execute(
        text(
            """
            select i.kind,
                   max(i.issue) as issue,
                   min(i.severity) as severity,
                   max(i.matched_pages)::int as matched,
                   count(*)::int as pages,
                   (array_agg(pg.url order by pg.url))[1:3] as examples,
                   max(i.rejection_reason) as reason,
                   max(i.issue_type) as issue_type
              from site_page_issues i
              join site_pages pg on pg.id = i.page_id
             where i.run_id = :run_id and i.state = :state
             group by i.kind
            """
        ),
        {"run_id": run_id, "state": state},
    )
    return [PageIssueGroup.model_validate(row, from_attributes=True) for row in result]
