from src.agent_scope.analytics.prompt import (
    ANALYTICS_SERVER,
    engine_part,
    site_part,
    voice_part,
)
from src.agent_scope.lib import AgentScope, SiteRef, desk_guides, desk_tables, fill
from src.analytics.models.analytics_reports import AnalyticsReport
from src.analytics.models.analytics_sessions import AnalyticsSession
from src.analytics.models.analytics_sources import AnalyticsSource
from src.content.models.content_pieces import ContentPiece
from src.site_pages.models.site_page import SitePage
from src.site_pages.models.site_page_index_status import SitePageIndexStatus
from src.site_search.models.site_search_daily import SiteSearchDaily
from src.site_search.models.site_search_sync import SiteSearchSync
from src.site_traffic.models.site_traffic_channels_daily import SiteTrafficChannelsDaily
from src.site_traffic.models.site_traffic_events_daily import SiteTrafficEventsDaily
from src.site_traffic.models.site_traffic_geo_daily import SiteTrafficGeoDaily
from src.site_traffic.models.site_traffic_landing_daily import SiteTrafficLandingDaily
from src.site_traffic.models.site_traffic_pages_daily import SiteTrafficPagesDaily
from src.site_traffic.models.site_traffic_sync import SiteTrafficSync
from src.site_traffic.models.site_traffic_tech_daily import SiteTrafficTechDaily
from src.site_traffic.models.site_traffic_totals_daily import SiteTrafficTotalsDaily
from src.sites.models.site import Site
from src.technical_seo.models.site_audit_run import SiteAuditRun
from src.technical_seo.models.site_issue import SiteIssue
from src.technical_seo.models.site_page_issue import SitePageIssue

SEGMENT_0 = """You are Meelu answering ONE question about the user's own data. The form names the analysis session, its data, its engine session_key, and the source files on this machine.

## How this conversation works
Answer the question in front of you and stop. Do not pre-empt the next one or summarise the whole dataset. Do not ask permission to run the analysis the user asked for.

"""

SEGMENT_1 = """

## Keeping something permanently
If the user asks to keep a dashboard, save it with analytics_save_report. Pass this session's id so it appears on the session's page and the Analytics desk. Otherwise a chart just lives in the answer and needs no report.

"""

SEGMENT_2 = """

## What you can and cannot do
You can read anything in the Meelu workspace. Projects, prospects and posts often explain what a number means. Your Meelu writes are these four tools.
- analytics_update_session.
- analytics_add_source.
- analytics_save_report.
- analytics_update_report.
Nothing sends, publishes or leaves this machine.

## When the user asks for something else
This conversation is about this session's data. When the user asks for something another desk owns, load that desk with add_desk when the prompt offers it, and carry on. Otherwise name the desk that owns it and stop there.

"""


def system_prompt(site: SiteRef | None) -> str:
    return fill(
        SEGMENT_0 + engine_part() + SEGMENT_1 + site_part(site) + SEGMENT_2 + voice_part(),
        site,
    )


DESK = "analytics"
TABLES = desk_tables(
    AnalyticsSession,
    AnalyticsSource,
    AnalyticsReport,
    Site,
    SitePage,
    SitePageIndexStatus,
    SiteSearchDaily,
    SiteSearchSync,
    SiteTrafficTotalsDaily,
    SiteTrafficPagesDaily,
    SiteTrafficLandingDaily,
    SiteTrafficChannelsDaily,
    SiteTrafficGeoDaily,
    SiteTrafficTechDaily,
    SiteTrafficEventsDaily,
    SiteTrafficSync,
    SiteAuditRun,
    SiteIssue,
    SitePageIssue,
    ContentPiece,
)
GUIDES = desk_guides("workflow", "search-data")

scope = AgentScope(
    desk=DESK,
    tables=TABLES,
    guides=GUIDES,
    limits={"maxTurns": 40, "maxBudgetUsd": 2},
    save_attachments=True,
    mcp_servers={"analytics": ANALYTICS_SERVER},
    system_prompt=system_prompt,
)
