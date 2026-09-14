from dataclasses import dataclass


@dataclass(frozen=True)
class PageRule:
    kind: str
    severity: str
    issue: str
    where: str
    llm_check: bool = False
    issue_type: str = "static"


@dataclass(frozen=True)
class SiteRule:
    kind: str
    severity: str
    issue: str
    holds: bool
    llm_check: bool = False
    issue_type: str = "static"
