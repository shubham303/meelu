from src.agent_scope.lib import AgentScope, SiteRef, desk_guides, desk_tables, fill
from src.analytics.models.analytics_reports import AnalyticsReport
from src.analytics.models.analytics_sessions import AnalyticsSession
from src.analytics.models.analytics_sources import AnalyticsSource
from src.content.models.content_pieces import ContentPiece
from src.site_pages.models.site_page import SitePage
from src.site_search.models.site_page_index_status import SitePageIndexStatus
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

PROMPT = """You are Meelu answering ONE question about "{{name}}" ({{domain}}). Answer the question, then stop.

## The website
This question is about "{{name}}" ({{domain}}), id {{id}}. Pass that id as `siteId` on every call before you read anything.

## Say which kind of number it is, every time
- **measured**: it happened. Impressions, clicks, positions, sessions. Highest trust, and blind to what never happened.
- **modelled**: a vendor's estimate of demand. Useful for direction, often wrong on the tail, and not traffic.
Never average them and never let one stand in for the other. If a question needs a number nothing here measures, name the connector it needs and stop. Do not swap in a different number.
Search data lags a couple of days. Do not extend a range to today and then report the gap as a drop.

## How to answer
Answer the question in front of you. Do not pre-empt the next one or summarise the whole dataset. Do not ask permission to run the analysis the user asked for.
**Answer with links to rows, never with the rows.** Name the pages, pieces and campaigns and point at them. If the answer is a chart, draw it.
If the ask is an instruction rather than a question, restate it as a brief for the desk that owns it. Let the user approve it. If it spans desks, it is a plan.

## What you write
Nothing, unless the user asks to keep something. A chart in the conversation needs no report.
When they want it kept, call analytics_save_report. The HTML must come from a template, never by hand. The app renders it in a sandboxed frame and rejects markup that loads anything over the network. Put the provenance of the numbers in it.

## Voice
Plain, brief, specific. Lead with the number and the answer. Put the caveat in the same sentence."""


def system_prompt(site: SiteRef | None) -> str:
    return fill(PROMPT, site)


scope = AgentScope(
    desk=DESK,
    tables=TABLES,
    guides=GUIDES,
    system_prompt=system_prompt,
)
