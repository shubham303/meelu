import re
from typing import Self

from pydantic import BaseModel

from src.technical_seo.schemas.issues import PageIssueRecord, SiteIssueRecord

CSV_COLUMNS = ("kind", "severity", "scope", "type", "state", "url", "issue")


FORMULA_TRIGGERS = ("=", "+", "-", "@", "\t", "\r")


def cell(value: str) -> str:
    if value.startswith(FORMULA_TRIGGERS):
        value = "'" + value
    if re.search(r'["\n\r,]', value):
        escaped = value.replace('"', '""')
        return f'"{escaped}"'
    return value


class IssueCsvRow(BaseModel):
    kind: str
    severity: str
    scope: str
    type: str
    state: str
    url: str = ""
    issue: str

    @classmethod
    def from_site_issue(cls, issue: SiteIssueRecord, state: str) -> Self:
        return cls(
            kind=issue.kind,
            severity=issue.severity,
            scope="site",
            type=issue.issue_type,
            state=state,
            issue=issue.issue,
        )

    @classmethod
    def from_page_issue(cls, issue: PageIssueRecord, state: str) -> Self:
        return cls(
            kind=issue.kind,
            severity=issue.severity,
            scope="pages",
            type=issue.issue_type,
            state=state,
            url=issue.url or "",
            issue=issue.issue,
        )

    def line(self) -> str:
        return ",".join(cell(getattr(self, column)) for column in CSV_COLUMNS)


class IssueCsvFile(BaseModel):
    filename: str
    body: str

    @classmethod
    def build(cls, filename: str, rows: list[IssueCsvRow]) -> Self:
        header = ",".join(CSV_COLUMNS)
        body = header + "\n" + "\n".join(row.line() for row in rows) + "\n"
        return cls(filename=filename, body=body)
