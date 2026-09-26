from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Integer, Select, cast, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.technical_seo.models.site_audit_run import SiteAuditRun
from src.technical_seo.models.site_issue import SiteIssue
from src.technical_seo.models.site_page_issue import SitePageIssue
from src.technical_seo.schemas import (
    AuditRunChanges,
    AuditRunFilter,
    AuditRunRecord,
    IssueChanges,
    IssueCounts,
    NewPageIssue,
    NewSiteIssue,
    PageIssueFilter,
    PageIssueKindGroup,
    PageIssueRecord,
    PageIssueSelector,
    SiteIssueFilter,
    SiteIssueRecord,
)


def _apply(row: Any, changes: dict[str, Any]) -> None:
    for key, value in changes.items():
        setattr(row, key, value)
    row.updated_at = datetime.now(UTC)


class SiteAuditRunRepository:
    async def create(
        self, db: AsyncSession, user_id: str, site_id: str, trigger: str
    ) -> AuditRunRecord:
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

    async def get(self, db: AsyncSession, site_id: str, run_id: str) -> AuditRunRecord | None:
        row = await self._row(db, site_id, run_id)
        return None if row is None else AuditRunRecord.model_validate(row)

    async def latest(self, db: AsyncSession, site_id: str) -> AuditRunRecord | None:
        result = await db.execute(
            select(SiteAuditRun)
            .where(SiteAuditRun.site_id == site_id)
            .order_by(SiteAuditRun.seq.desc())
            .limit(1)
        )
        row = result.scalars().first()
        return None if row is None else AuditRunRecord.model_validate(row)

    async def update(
        self, db: AsyncSession, site_id: str, run_id: str, patch: AuditRunChanges
    ) -> AuditRunRecord | None:
        run = await self._row(db, site_id, run_id)
        if run is None:
            return None
        _apply(run, patch.changes())
        await db.flush()
        return AuditRunRecord.model_validate(run)

    async def delete(self, db: AsyncSession, site_id: str, run_id: str) -> None:
        run = await self._row(db, site_id, run_id)
        if run is not None:
            await db.delete(run)
            await db.flush()

    async def _row(self, db: AsyncSession, site_id: str, run_id: str) -> SiteAuditRun | None:
        result = await db.execute(
            select(SiteAuditRun)
            .where(SiteAuditRun.site_id == site_id, SiteAuditRun.id == run_id)
            .limit(1)
        )
        return result.scalars().first()

    async def _count(self, db: AsyncSession, query: Select) -> int:
        return (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()

    async def list(
        self, db: AsyncSession, site_id: str, filters: AuditRunFilter, paging: PaginationParams
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
        total = await self._count(db, query)
        return PaginatedApiResponse[AuditRunRecord](
            data=[AuditRunRecord.model_validate(r) for r in rows],
            pagination=PaginationService.build_pagination_meta(
                total, paging.page, paging.page_size
            ),
        )


site_audit_runs = SiteAuditRunRepository()


class SiteIssueRepository:
    async def create_many(
        self, db: AsyncSession, user_id: str, site_id: str, run_id: str, rows: list[NewSiteIssue]
    ) -> int:
        if not rows:
            return 0
        db.add_all([self._new(user_id, site_id, run_id, row) for row in rows])
        await db.flush()
        return len(rows)

    async def create(
        self, db: AsyncSession, user_id: str, site_id: str, run_id: str, row: NewSiteIssue
    ) -> SiteIssueRecord:
        issue = self._new(user_id, site_id, run_id, row)
        db.add(issue)
        await db.flush()
        return SiteIssueRecord.model_validate(issue)

    async def get(self, db: AsyncSession, site_id: str, issue_id: str) -> SiteIssueRecord | None:
        row = await self._row(db, site_id, issue_id)
        return None if row is None else SiteIssueRecord.model_validate(row)

    async def list_all(
        self, db: AsyncSession, run_id: str, filters: SiteIssueFilter, limit: int
    ) -> list[SiteIssueRecord]:
        rows = (await db.execute(self._query(run_id, filters).limit(limit))).scalars().all()
        return [SiteIssueRecord.model_validate(r) for r in rows]

    async def count(self, db: AsyncSession, run_id: str, filters: SiteIssueFilter) -> int:
        return await self._count(db, self._query(run_id, filters))

    async def update(
        self, db: AsyncSession, site_id: str, issue_id: str, patch: IssueChanges
    ) -> SiteIssueRecord | None:
        issue = await self._row(db, site_id, issue_id)
        if issue is None:
            return None
        _apply(issue, patch.changes())
        await db.flush()
        return SiteIssueRecord.model_validate(issue)

    async def delete(self, db: AsyncSession, site_id: str, issue_id: str) -> None:
        issue = await self._row(db, site_id, issue_id)
        if issue is not None:
            await db.delete(issue)
            await db.flush()

    async def update_by_kind(
        self, db: AsyncSession, run_id: str, kind: str, patch: IssueChanges
    ) -> int:
        result = await db.execute(
            update(SiteIssue)
            .where(SiteIssue.run_id == run_id, SiteIssue.kind == kind)
            .values(**patch.changes(), updated_at=datetime.now(UTC))
        )
        return result.rowcount or 0

    async def count_by_state(self, db: AsyncSession, run_id: str) -> IssueCounts:
        row = (
            await db.execute(
                select(
                    func.count().filter(SiteIssue.state == "open"),
                    func.count().filter(SiteIssue.state == "rejected"),
                ).where(SiteIssue.run_id == run_id)
            )
        ).first()
        return IssueCounts(open=row[0], rejected=row[1]) if row else IssueCounts()

    def _new(self, user_id: str, site_id: str, run_id: str, row: NewSiteIssue) -> SiteIssue:
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
            issue_type=row.issue_type,
            created_at=now,
            updated_at=now,
        )

    async def _row(self, db: AsyncSession, site_id: str, issue_id: str) -> SiteIssue | None:
        result = await db.execute(
            select(SiteIssue).where(SiteIssue.site_id == site_id, SiteIssue.id == issue_id).limit(1)
        )
        return result.scalars().first()

    def _query(self, run_id: str, filters: SiteIssueFilter) -> Select:
        conds: list[Any] = [SiteIssue.run_id == run_id]
        if filters.state:
            conds.append(SiteIssue.state == filters.state)
        if filters.severity:
            conds.append(SiteIssue.severity == filters.severity)
        if filters.kinds:
            conds.append(SiteIssue.kind.in_(filters.kinds))
        if filters.issue_type:
            conds.append(SiteIssue.issue_type == filters.issue_type)
        return select(SiteIssue).where(*conds).order_by(SiteIssue.severity, SiteIssue.kind)

    async def _count(self, db: AsyncSession, query: Select) -> int:
        return (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()

    async def list(
        self, db: AsyncSession, run_id: str, filters: SiteIssueFilter, paging: PaginationParams
    ) -> PaginatedApiResponse[SiteIssueRecord]:
        query = self._query(run_id, filters)
        rows = (
            (await db.execute(query.offset(paging.offset).limit(paging.page_size))).scalars().all()
        )
        total = await self._count(db, query)
        return PaginatedApiResponse[SiteIssueRecord](
            data=[SiteIssueRecord.model_validate(r) for r in rows],
            pagination=PaginationService.build_pagination_meta(
                total, paging.page, paging.page_size
            ),
        )


site_issues = SiteIssueRepository()


class SitePageIssueRepository:
    async def create_many(
        self, db: AsyncSession, user_id: str, site_id: str, run_id: str, rows: list[NewPageIssue]
    ) -> int:
        if not rows:
            return 0
        db.add_all([self._new(user_id, site_id, run_id, row) for row in rows])
        await db.flush()
        return len(rows)

    async def create(
        self, db: AsyncSession, user_id: str, site_id: str, run_id: str, row: NewPageIssue
    ) -> PageIssueRecord:
        issue = self._new(user_id, site_id, run_id, row)
        db.add(issue)
        await db.flush()
        return PageIssueRecord.model_validate(issue)

    async def get(self, db: AsyncSession, site_id: str, issue_id: str) -> PageIssueRecord | None:
        issue = await self._row(db, site_id, issue_id)
        return None if issue is None else PageIssueRecord.model_validate(issue)

    async def list_all(
        self, db: AsyncSession, run_id: str, filters: PageIssueFilter, limit: int
    ) -> list[PageIssueRecord]:
        rows = (await db.execute(self._query(run_id, filters).limit(limit))).scalars().all()
        return [PageIssueRecord.model_validate(r) for r in rows]

    async def count(self, db: AsyncSession, run_id: str, filters: PageIssueFilter) -> int:
        return await self._count(db, self._query(run_id, filters))

    async def update(
        self, db: AsyncSession, site_id: str, issue_id: str, patch: IssueChanges
    ) -> PageIssueRecord | None:
        issue = await self._row(db, site_id, issue_id)
        if issue is None:
            return None
        _apply(issue, patch.changes())
        await db.flush()
        return PageIssueRecord.model_validate(issue)

    async def delete(self, db: AsyncSession, site_id: str, issue_id: str) -> None:
        issue = await self._row(db, site_id, issue_id)
        if issue is not None:
            await db.delete(issue)
            await db.flush()

    async def update_by(
        self, db: AsyncSession, run_id: str, selector: PageIssueSelector, patch: IssueChanges
    ) -> int:
        conds: list[Any] = [SitePageIssue.run_id == run_id]
        if selector.kind:
            conds.append(SitePageIssue.kind == selector.kind)
        if selector.page_id:
            conds.append(SitePageIssue.page_id == selector.page_id)
        if selector.page_ids is not None:
            conds.append(SitePageIssue.page_id.in_(selector.page_ids))
        result = await db.execute(
            update(SitePageIssue)
            .where(*conds)
            .values(**patch.changes(), updated_at=datetime.now(UTC))
        )
        return result.rowcount or 0

    async def group_by_kind(
        self, db: AsyncSession, run_id: str, state: str
    ) -> list[PageIssueKindGroup]:
        result = await db.execute(
            select(
                SitePageIssue.kind,
                func.max(SitePageIssue.issue).label("issue"),
                func.min(SitePageIssue.severity).label("severity"),
                cast(func.max(SitePageIssue.matched_pages), Integer).label("matched"),
                cast(func.count(), Integer).label("pages"),
                func.array_agg(SitePageIssue.page_id).label("page_ids"),
                func.max(SitePageIssue.rejection_reason).label("reason"),
                func.max(SitePageIssue.issue_type).label("issue_type"),
            )
            .where(SitePageIssue.run_id == run_id, SitePageIssue.state == state)
            .group_by(SitePageIssue.kind)
        )
        return [PageIssueKindGroup.model_validate(dict(row)) for row in result.mappings()]

    async def count_by_state(self, db: AsyncSession, run_id: str) -> IssueCounts:
        row = (
            await db.execute(
                select(
                    func.count().filter(SitePageIssue.state == "open"),
                    func.count().filter(SitePageIssue.state == "rejected"),
                ).where(SitePageIssue.run_id == run_id)
            )
        ).first()
        return IssueCounts(open=row[0], rejected=row[1]) if row else IssueCounts()

    def _new(self, user_id: str, site_id: str, run_id: str, row: NewPageIssue) -> SitePageIssue:
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
            issue_type=row.issue_type,
            created_at=now,
            updated_at=now,
        )

    async def _row(self, db: AsyncSession, site_id: str, issue_id: str) -> SitePageIssue | None:
        result = await db.execute(
            select(SitePageIssue)
            .where(SitePageIssue.site_id == site_id, SitePageIssue.id == issue_id)
            .limit(1)
        )
        return result.scalars().first()

    def _query(self, run_id: str, filters: PageIssueFilter) -> Select:
        conds: list[Any] = [SitePageIssue.run_id == run_id]
        if filters.state:
            conds.append(SitePageIssue.state == filters.state)
        if filters.severity:
            conds.append(SitePageIssue.severity == filters.severity)
        if filters.kinds:
            conds.append(SitePageIssue.kind.in_(filters.kinds))
        if filters.issue_type:
            conds.append(SitePageIssue.issue_type == filters.issue_type)
        if filters.page_id:
            conds.append(SitePageIssue.page_id == filters.page_id)
        return (
            select(SitePageIssue)
            .where(*conds)
            .order_by(SitePageIssue.severity, SitePageIssue.kind, SitePageIssue.seq)
        )

    async def _count(self, db: AsyncSession, query: Select) -> int:
        return (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()

    async def list(
        self, db: AsyncSession, run_id: str, filters: PageIssueFilter, paging: PaginationParams
    ) -> PaginatedApiResponse[PageIssueRecord]:
        query = self._query(run_id, filters)
        rows = (
            (await db.execute(query.offset(paging.offset).limit(paging.page_size))).scalars().all()
        )
        total = await self._count(db, query)
        return PaginatedApiResponse[PageIssueRecord](
            data=[PageIssueRecord.model_validate(r) for r in rows],
            pagination=PaginationService.build_pagination_meta(
                total, paging.page, paging.page_size
            ),
        )


site_page_issues = SitePageIssueRepository()
