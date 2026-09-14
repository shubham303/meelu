from typing import Any, ClassVar, Self

from pydantic import BaseModel, Field, field_validator

from src.core.schemas import EntityModel
from src.technical_seo.schemas.issues import (
    IssueCounts,
    IssueCountsByScope,
    IssueHead,
    SiteIssueRecord,
)
from src.technical_seo.schemas.runs import AuditRunRecord


class PageIssueGroup(BaseModel):
    kind: str
    issue: str
    severity: str
    matched: int
    pages: int
    examples: list[str]
    reason: str | None
    issue_type: str = "static"

    @field_validator("examples", mode="before")
    @classmethod
    def _examples(cls, value: Any) -> list[str]:
        return list(value or [])


class IssueGroupResponse(IssueHead):
    keep_null: ClassVar[frozenset[str]] = frozenset({"reason"})

    scope: str
    pages: int = 0
    matched: int = 0
    examples: list[str] = Field(default_factory=list)
    state: str
    reason: str | None = None
    issue_type: str = "static"

    @classmethod
    def from_site_issue(cls, issue: SiteIssueRecord, state: str) -> Self:
        return cls(
            scope="site",
            kind=issue.kind,
            issue=issue.issue,
            severity=issue.severity,
            state=state,
            reason=issue.rejection_reason,
            issue_type=issue.issue_type,
        )

    @classmethod
    def from_page_group(cls, group: PageIssueGroup, state: str) -> Self:
        return cls(scope="pages", state=state, **dict(group))

    def sort_key(self) -> tuple[str, int, str]:
        return (self.severity, -self.pages, self.kind)


class AuditSummaryResponse(EntityModel):
    run: AuditRunRecord
    site: IssueCounts
    pages: IssueCounts
    open_site_issues: list[IssueHead]
    open_page_issues: list[IssueGroupResponse]

    @classmethod
    def build(
        cls, run: AuditRunRecord, counts: IssueCountsByScope, groups: list[IssueGroupResponse]
    ) -> Self:
        return cls(
            run=run,
            site=counts.site,
            pages=counts.pages,
            open_site_issues=[IssueHead.model_validate(g) for g in groups if g.scope == "site"],
            open_page_issues=[g for g in groups if g.scope == "pages"],
        )


class AuditResultResponse(AuditSummaryResponse):
    checks: int

    @classmethod
    def from_summary(cls, summary: AuditSummaryResponse, checks: int) -> Self:
        return cls(checks=checks, **dict(summary))
