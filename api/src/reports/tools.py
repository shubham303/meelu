from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.reports.schemas import (
    ReportCreateRequest,
    ReportDesk,
    ReportSummaryRecord,
    ReportSummaryResponse,
    ReportUpdateRequest,
)
from src.reports.service import report_service


@tool(writes=True, desk="reports")
async def save_report(desk: ReportDesk, title: str, html: str) -> ReportSummaryResponse:
    """Save a report for this website once the user asks to keep a result; `desk` is the
    desk you are working on. The HTML must be self-contained: inline CSS and SVG only,
    nothing loaded over the network."""
    ctx = require_site()
    body = ReportCreateRequest(desk=desk, title=title, html=html)
    async with unit_of_work() as db:
        record = await report_service.create_report(db, ctx.user_id, ctx.site_id, body)
    return ReportSummaryResponse.model_validate(ReportSummaryRecord.from_report(record))


@tool(writes=True, desk="reports")
async def update_report(
    report_id: str, title: str | None = None, html: str | None = None
) -> ReportSummaryResponse:
    """Replace a saved report's title and/or HTML by its id, when the user asks to
    change it."""
    ctx = require_site()
    body = ReportUpdateRequest(title=title, html=html)
    async with unit_of_work() as db:
        record = await report_service.update_report(db, ctx.user_id, ctx.site_id, report_id, body)
    return ReportSummaryResponse.model_validate(ReportSummaryRecord.from_report(record))
