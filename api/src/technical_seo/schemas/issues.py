from datetime import UTC, datetime
from typing import Any, ClassVar, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel
from src.technical_seo.schemas import fields


class IssueHead(EntityModel):
    kind: str
    issue: str
    severity: str
    issue_type: str = "static"


class SiteIssueRecord(IssueHead):
    id: str
    site_id: str
    run_id: str
    state: str
    rejection_reason: str | None = None
    reviewed_at: JsDateTime | None = None
    created_at: JsDateTime
    updated_at: JsDateTime


class PageIssueRecord(SiteIssueRecord):
    page_id: str
    matched_pages: int
    url: str | None = None


class SiteIssueResponse(SiteIssueRecord):
    pass


class SiteIssueListItemResponse(SiteIssueRecord):
    pass


class SiteIssueDeleteResponse(EntityModel):
    id: str
    deleted: bool = Field(default=True)


class PageIssueResponse(PageIssueRecord):
    pass


class PageIssueListItemResponse(PageIssueRecord):
    pass


class PageIssueDeleteResponse(EntityModel):
    id: str
    deleted: bool = Field(default=True)


class IssueCounts(EntityModel):
    open: int = 0
    rejected: int = 0


class IssueCountsByScope(EntityModel):
    site: IssueCounts
    pages: IssueCounts


class SiteIssueFilter(BaseModel):
    state: str | None = None
    severity: str | None = None
    kinds: list[str] | None = None
    issue_type: str | None = None


class PageIssueFilter(SiteIssueFilter):
    page_id: str | None = None
    url: str | None = None


class NewSiteIssue(BaseModel):
    kind: str
    issue: str
    severity: str = "p2"
    state: str = "open"
    issue_type: str = "static"


class NewPageIssue(NewSiteIssue):
    page_id: str
    matched_pages: int = 1


class IssueChanges(BaseModel):
    issue: str | None = None
    severity: str | None = None
    state: str | None = None
    rejection_reason: str | None = None
    reviewed_at: datetime | None = None

    def changes(self) -> dict[str, Any]:
        return self.model_dump(exclude_unset=True)


class IssueDecision(BaseModel):
    state: str
    issue: str
    rejection_reason: str | None
    reviewed_at: datetime | None

    @classmethod
    def from_issue(cls, issue: SiteIssueRecord) -> Self:
        return cls.model_validate(issue, from_attributes=True)

    @property
    def decided(self) -> bool:
        return self.state != "open" or self.reviewed_at is not None

    def to_changes(self) -> IssueChanges:
        changes = IssueChanges(
            issue=self.issue, state=self.state, rejection_reason=self.rejection_reason
        )
        if self.reviewed_at:
            changes.reviewed_at = self.reviewed_at
        return changes


class IssueCreateRequest(RequestModel):
    run_id: str | None = None
    kind: str = Field(default="", validate_default=True)
    issue: str = Field(default="", validate_default=True)
    severity: str = "p2"
    state: str = "open"

    @field_validator("kind", mode="before")
    @classmethod
    def _kind(cls, value: Any) -> str:
        return fields.kind(value)

    @field_validator("issue", mode="before")
    @classmethod
    def _issue(cls, value: Any) -> str:
        return fields.issue_text(value)

    @field_validator("severity", mode="before")
    @classmethod
    def _severity(cls, value: Any) -> str:
        return "p2" if fields.blank(value) else fields.severity(value)

    @field_validator("state", mode="before")
    @classmethod
    def _state(cls, value: Any) -> str:
        return "open" if fields.blank(value) else fields.state(value)


class SiteIssueCreateRequest(IssueCreateRequest):
    def to_new(self) -> NewSiteIssue:
        return NewSiteIssue(
            kind=self.kind, issue=self.issue, severity=self.severity, state=self.state
        )


class PageIssueCreateRequest(IssueCreateRequest):
    page_id: str | None = None
    url: str | None = None
    matched_pages: int = Field(default=1, validate_default=True)

    @field_validator("matched_pages", mode="before")
    @classmethod
    def _matched(cls, value: Any) -> int:
        return fields.matched_pages(value)

    def to_new(self, page_id: str) -> NewPageIssue:
        return NewPageIssue(
            kind=self.kind,
            issue=self.issue,
            severity=self.severity,
            state=self.state,
            page_id=page_id,
            matched_pages=self.matched_pages,
        )


class IssueUpdateRequest(RequestModel):
    PATCH_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {"issue", "severity", "state", "rejection_reason"}
    )

    issue: str | None = None
    severity: str | None = None
    state: str | None = None
    rejection_reason: str | None = None

    @field_validator("issue", mode="before")
    @classmethod
    def _issue(cls, value: Any) -> str:
        return fields.issue_text(value)

    @field_validator("severity", mode="before")
    @classmethod
    def _severity(cls, value: Any) -> str:
        if fields.blank(value):
            raise ValueError("A severity cannot be blank.")
        return fields.severity(value)

    @field_validator("state", mode="before")
    @classmethod
    def _state(cls, value: Any) -> str:
        if fields.blank(value):
            raise ValueError("A state cannot be blank.")
        return fields.state(value)

    @field_validator("rejection_reason", mode="before")
    @classmethod
    def _reason(cls, value: Any) -> str | None:
        return fields.reason(value)

    @model_validator(mode="after")
    def _something_to_change(self) -> Self:
        if not self.model_fields_set & self.PATCH_FIELDS:
            raise ValueError("Nothing to change. Send issue, severity, state or rejectionReason.")
        return self

    def to_changes(self) -> IssueChanges:
        changes = IssueChanges(reviewed_at=datetime.now(UTC))
        if self.issue is not None:
            changes.issue = self.issue
        if self.severity is not None:
            changes.severity = self.severity
        if self.state is not None:
            changes.state = self.state
            changes.rejection_reason = None if self.state == "open" else self.rejection_reason
        elif "rejection_reason" in self.model_fields_set:
            changes.rejection_reason = self.rejection_reason
        return changes


class SiteIssueBulkUpdateRequest(IssueUpdateRequest):
    run_id: str | None = None
    kind: str = Field(default="", validate_default=True)

    @field_validator("kind", mode="before")
    @classmethod
    def _kind(cls, value: Any) -> str:
        return fields.kind(value)


class PageIssueSelector(BaseModel):
    kind: str | None = None
    page_id: str | None = None
    url: str | None = None


class PageIssueBulkUpdateRequest(IssueUpdateRequest):
    run_id: str | None = None
    kind: str | None = None
    page_id: str | None = None
    url: str | None = None

    @field_validator("kind", mode="before")
    @classmethod
    def _kind(cls, value: Any) -> str | None:
        return None if fields.blank(value) else fields.kind(value)

    @field_validator("page_id", "url", mode="before")
    @classmethod
    def _optional_text(cls, value: Any) -> str | None:
        return None if fields.blank(value) else str(value)

    @model_validator(mode="after")
    def _needs_a_target(self) -> Self:
        if not self.kind and not self.page_id and not self.url:
            raise ValueError("Changing page issues in bulk needs a kind, a pageId or a url.")
        return self

    def selector(self) -> PageIssueSelector:
        return PageIssueSelector(kind=self.kind, page_id=self.page_id, url=self.url)


class IssueBulkUpdateResult(EntityModel):
    run_id: str
    updated: int


class IssueWriteResult(EntityModel):
    run_id: str
    kind: str
    state: str


class IssueChangeResult(EntityModel):
    site: int
    pages: int
    issue: str | None = None
    severity: str | None = None
    state: str | None = None
    rejection_reason: str | None = None
