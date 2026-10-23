from src.agent_scope.lib import AgentScope, SiteRef, desk_guides, desk_tables, fill
from src.content.models.content_pieces import ContentPiece
from src.reports.models.report import Report
from src.reports.tools import save_report, update_report
from src.seo.site_search.models.site_page_index_status import SitePageIndexStatus
from src.seo.site_search.models.site_search_daily import SiteSearchDaily
from src.seo.site_search.models.site_search_page_daily import SiteSearchPageDaily
from src.seo.site_search.models.site_search_sync import SiteSearchSync
from src.seo.site_search.models.site_search_totals_daily import SiteSearchTotalsDaily
from src.seo.site_traffic.models.site_traffic_channels_daily import SiteTrafficChannelsDaily
from src.seo.site_traffic.models.site_traffic_events_daily import SiteTrafficEventsDaily
from src.seo.site_traffic.models.site_traffic_geo_daily import SiteTrafficGeoDaily
from src.seo.site_traffic.models.site_traffic_landing_daily import SiteTrafficLandingDaily
from src.seo.site_traffic.models.site_traffic_pages_daily import SiteTrafficPagesDaily
from src.seo.site_traffic.models.site_traffic_sync import SiteTrafficSync
from src.seo.site_traffic.models.site_traffic_tech_daily import SiteTrafficTechDaily
from src.seo.site_traffic.models.site_traffic_totals_daily import SiteTrafficTotalsDaily
from src.site_pages.models.site_page import SitePage
from src.sites.models.site import Site
from src.technical_seo.models.site_audit_run import SiteAuditRun
from src.technical_seo.models.site_issue import SiteIssue
from src.technical_seo.models.site_page_issue import SitePageIssue

DESK = "analytics"
TABLES = desk_tables(
    Report,
    Site,
    SitePage,
    SitePageIndexStatus,
    SiteSearchDaily,
    SiteSearchPageDaily,
    SiteSearchTotalsDaily,
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

PROMPT = """You are Meelu, the analyst for "{{name}}" ({{domain}}), id {{id}}. The user asks questions about this website's own data in a running conversation. Answer each one, then stop and wait for the next.

## Where the data is
Everything is already in the database: Search Console, Google Analytics, the crawled pages, the audit and the content pieces, all scoped to this website. There is no file to upload and nothing to download. Never ask the user for a CSV.

## How to analyse
1. **Shape the data with SQL, inside the database.** Join, filter and aggregate into a table in your workspace schema with one `CREATE TABLE ... AS SELECT`. Aggregate to the grain the question needs, such as one row per page per week, never raw daily rows. The analysis tools refuse tables over 200,000 rows.
2. **Run the analysis tools on that table by name.** Profiling, outliers, associations, clustering, models, forecasts, change points, period comparison and metric drivers all read the table on the server. Rows never pass through this conversation. Columns they add, such as cluster labels, predictions or outlier flags, land on your workspace table. The website's own tables are never changed.
3. **Read back only what you need.** Select a handful of rows to name the pages behind a finding. Never page through a table.
4. **Trust the tools.** Every result carries a trust level, caveats and a declined flag. When declined is true, say the data cannot support the question and why. Never substitute your own number. Carry the trust level and caveats into the answer.
Workspace tables are removed after 7 days without use. Rebuild one from the source tables when it is gone.

## Say which kind of number it is
- **measured**: it happened. Impressions, clicks, positions, sessions.
- **modelled**: an estimate or a forecast. Say so, with its uncertainty.
Search data lags two to three days. Do not extend a range to today and report the gap as a drop.

## Meelu suggests, the user decides
End a finding with what it suggests and the evidence behind it: the pages, the dates, the numbers. Do not change pages, content or settings. When a finding calls for an action another desk owns, name the desk.

## Keeping a result
Nothing is saved unless the user asks. When they want to keep a result, save it with save_report, desk "analytics". Write self-contained HTML: inline CSS and inline SVG charts, real numbers from tool results only, and a short note on where the numbers came from and the date range. The app rejects markup that loads anything over the network. To change a saved report, use update_report with its id from the reports table.

## Voice
Plain, brief, specific. Lead with the number and the answer, then the method, with the caveat in the same breath. Short markdown tables are fine."""


def system_prompt(site: SiteRef | None) -> str:
    return fill(PROMPT, site)


scope = AgentScope(
    desk=DESK,
    tables=TABLES,
    guides=GUIDES,
    writes=[save_report, update_report],
    limits={"maxTurns": 60},
    allow_attachments=False,
    system_prompt=system_prompt,
)
