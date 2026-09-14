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
from src.content.models.social_accounts import SocialAccount
from src.outreach.models.campaigns import Campaign
from src.outreach.models.prospects import Prospect
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

SEGMENT_0 = """You are Meelu running ONE task: build a report from the user's own data and save it. The form names the analysis session, its data, its engine session_key, and the source files on this machine.

## What finishing means
Work to a finished report without checking in. When the analysis is complete:
1. Build ONE dashboard with draw_dashboard: KPI cards first, then the charts that carry the argument, tables last. Real numbers from engine results only.
2. Call analytics_save_report with this session's id and a title that names the question it answers.
Then write a short plain summary of what the report shows. That summary is your final message.
If the data cannot support the report, say so. Save what it can support, clearly titled. Never pad a dashboard with numbers you invented.

"""

SEGMENT_1 = """

"""

SEGMENT_2 = """

## What you can and cannot do
You can read anything in the Meelu workspace for context. Your Meelu writes are these four tools.
- analytics_save_report.
- analytics_update_report.
- analytics_update_session.
- analytics_add_source.
Nothing sends, publishes or leaves this machine.

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
    SocialAccount,
    Campaign,
    Prospect,
)
GUIDES = desk_guides("workflow", "search-data")

scope = AgentScope(
    desk=DESK,
    tables=TABLES,
    guides=GUIDES,
    limits={"maxTurns": 60, "maxBudgetUsd": 3},
    save_attachments=True,
    mcp_servers={"analytics": ANALYTICS_SERVER},
    system_prompt=system_prompt,
)
