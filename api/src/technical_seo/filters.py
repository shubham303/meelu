from fastapi import HTTPException, Query

from src.technical_seo.schemas import AuditRunFilter, PageIssueFilter, SiteIssueFilter, fields


def _checked(fn, value):
    try:
        return fn(value)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


def optional_state(state: str | None = Query(None)) -> str | None:
    return None if fields.blank(state) else _checked(fields.state, state)


def default_open_state(state: str | None = Query(None)) -> str:
    return "open" if fields.blank(state) else _checked(fields.state, state)


def optional_kinds(kind: list[str] | None = Query(None)) -> list[str] | None:
    return _checked(fields.kinds, kind)


def audit_run_filter(
    trigger: str | None = Query(None),
    reviewed: bool | None = Query(None),
) -> AuditRunFilter:
    return AuditRunFilter(trigger=trigger or None, reviewed=reviewed)


def site_issue_filter(
    state: str | None = Query(None),
    severity: str | None = Query(None),
    kind: list[str] | None = Query(None),
    issue_type: str | None = Query(None, alias="type"),
) -> SiteIssueFilter:
    return SiteIssueFilter(
        state=None if fields.blank(state) else _checked(fields.state, state),
        severity=None if fields.blank(severity) else _checked(fields.severity, severity),
        kinds=_checked(fields.kinds, kind),
        issue_type=None if fields.blank(issue_type) else _checked(fields.issue_type, issue_type),
    )


def page_issue_filter(
    state: str | None = Query(None),
    severity: str | None = Query(None),
    kind: list[str] | None = Query(None),
    page_id: str | None = Query(None, alias="pageId"),
    url: str | None = Query(None),
    issue_type: str | None = Query(None, alias="type"),
) -> PageIssueFilter:
    return PageIssueFilter(
        state=None if fields.blank(state) else _checked(fields.state, state),
        severity=None if fields.blank(severity) else _checked(fields.severity, severity),
        kinds=_checked(fields.kinds, kind),
        page_id=page_id or None,
        url=url or None,
        issue_type=None if fields.blank(issue_type) else _checked(fields.issue_type, issue_type),
    )
