from dataclasses import dataclass


@dataclass(frozen=True)
class PageRule:
    kind: str
    severity: str
    issue: str
    where: str
    issue_type: str = "static"


@dataclass(frozen=True)
class SiteRule:
    kind: str
    severity: str
    issue: str
    holds: bool
    issue_type: str = "static"
