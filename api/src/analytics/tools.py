from src.agent.context import require_site
from src.agent.server import tool
from src.analytics.schemas import (
    AnalyticsReportCreateRequest,
    AnalyticsReportSummaryRecord,
    AnalyticsReportSummaryResponse,
    AnalyticsReportUpdateRequest,
)
from src.analytics.service import analytics_service
from src.core.database import unit_of_work


@tool(writes=True, desk="analytics")
async def analytics_save_report(title: str, html: str) -> AnalyticsReportSummaryResponse:
    """Save a report for this website once the user asks to keep a result. The HTML
    must be self-contained: inline CSS and SVG only, nothing loaded over the network."""
    ctx = require_site()
    body = AnalyticsReportCreateRequest(title=title, html=html)
    async with unit_of_work() as db:
        record = await analytics_service.create_report(db, ctx.user_id, ctx.site_id, body)
    return AnalyticsReportSummaryResponse.model_validate(
        AnalyticsReportSummaryRecord.from_report(record)
    )


@tool(writes=True, desk="analytics")
async def analytics_update_report(
    report_id: str, title: str | None = None, html: str | None = None
) -> AnalyticsReportSummaryResponse:
    """Replace a saved report's title and/or HTML by its id, when the user asks to
    change it."""
    ctx = require_site()
    body = AnalyticsReportUpdateRequest(title=title, html=html)
    async with unit_of_work() as db:
        record = await analytics_service.update_report(
            db, ctx.user_id, ctx.site_id, report_id, body
        )
    return AnalyticsReportSummaryResponse.model_validate(
        AnalyticsReportSummaryRecord.from_report(record)
    )
