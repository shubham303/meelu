from fastapi import HTTPException

from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.technical_seo.service import technical_seo_service
from src.technical_seo.constants import SITE_ISSUE_SEVERITIES as SEVERITIES
from src.technical_seo.schemas import (
    IssueChangeResult,
    IssueUpdateRequest,
    IssueWriteResult,
    PageIssueBulkUpdateRequest,
    SiteIssueBulkUpdateRequest,
    SiteIssueCreateRequest,
)


async def _apply(kind: str, url: str | None, patch: IssueUpdateRequest) -> IssueChangeResult:
    ctx = require_site()
    changes = patch.model_dump(exclude_unset=True)
    async with unit_of_work() as db:
        site = pages = 0
        if url:
            pages = (
                await technical_seo_service.update_page_issues_by(
                    db, ctx.site_id, PageIssueBulkUpdateRequest(kind=kind, url=url, **changes)
                )
            ).updated
        else:
            try:
                site = (
                    await technical_seo_service.update_site_issues_by_kind(
                        db, ctx.site_id, SiteIssueBulkUpdateRequest(kind=kind, **changes)
                    )
                ).updated
            except HTTPException as exc:
                if exc.status_code != 404:
                    raise
            try:
                pages = (
                    await technical_seo_service.update_page_issues_by(
                        db, ctx.site_id, PageIssueBulkUpdateRequest(kind=kind, **changes)
                    )
                ).updated
            except HTTPException as exc:
                if exc.status_code != 404:
                    raise
        if site == 0 and pages == 0:
            raise ValueError(f"No issues of kind {kind!r} on the latest audit run.")
        return IssueChangeResult(site=site, pages=pages, **changes)


@tool(writes=True, desk="technical-seo")
async def create_site_issue(kind: str, issue: str, severity: str = "p2") -> IssueWriteResult:
    """Record a site-level technical SEO issue on the latest audit run; an existing
    issue of the same kind is updated and reopened."""
    if severity not in SEVERITIES:
        raise ValueError(f"severity must be one of {SEVERITIES}.")
    if not issue.strip():
        raise ValueError("An issue description is required.")
    ctx = require_site()
    async with unit_of_work() as db:
        body = SiteIssueCreateRequest(kind=kind, issue=issue, severity=severity)
        try:
            created = await technical_seo_service.create_site_issue(
                db, ctx.user_id, ctx.site_id, body
            )
            return IssueWriteResult(run_id=created.run_id, kind=kind, state="open")
        except HTTPException as exc:
            if exc.status_code != 409:
                raise
        updated = await technical_seo_service.update_site_issues_by_kind(
            db,
            ctx.site_id,
            SiteIssueBulkUpdateRequest(
                kind=body.kind, issue=body.issue, severity=body.severity, state="open"
            ),
        )
        return IssueWriteResult(run_id=updated.run_id, kind=kind, state="open")


@tool(writes=True, desk="technical-seo")
async def update_issue(
    kind: str,
    issue: str | None = None,
    severity: str | None = None,
    url: str | None = None,
) -> IssueChangeResult:
    """Change the description and/or severity of an existing technical SEO issue on
    the latest audit run — site-wide by kind, or for one page when url is given.
    State is untouched; use reject/restore for that."""
    if issue is not None and not issue.strip():
        raise ValueError("issue cannot be blank.")
    if severity is not None and severity not in SEVERITIES:
        raise ValueError(f"severity must be one of {SEVERITIES}.")
    if issue is None and severity is None:
        raise ValueError("Nothing to update: give issue and/or severity.")
    patch = IssueUpdateRequest.model_validate(
        {k: v for k, v in {"issue": issue, "severity": severity}.items() if v is not None}
    )
    return await _apply(kind, url, patch)


@tool(writes=True, desk="technical-seo")
async def reject_issue(kind: str, reason: str, url: str | None = None) -> IssueChangeResult:
    """Turn down a technical SEO issue with a required reason — site-wide by kind, or
    for one page when url is given."""
    if not reason.strip():
        raise ValueError("A reason is required.")
    return await _apply(kind, url, IssueUpdateRequest(state="rejected", rejection_reason=reason))


@tool(writes=True, desk="technical-seo")
async def restore_issue(kind: str, url: str | None = None) -> IssueChangeResult:
    """Reopen a previously rejected technical SEO issue — site-wide by kind, or for
    one page when url is given."""
    return await _apply(kind, url, IssueUpdateRequest(state="open"))
