from src.agent_scope.ask import AskDesk, ask_prompt
from src.agent_scope.lib import AgentScope, desk_guides, desk_tables
from src.analysis_jobs.models.site_analysis_job import SiteAnalysisJob
from src.analysis_jobs.models.site_page_analysis import SitePageAnalysis
from src.crawl_jobs.models.site_crawl_job import SiteCrawlJob
from src.site_pages.models.site_chunk import SiteChunk
from src.site_pages.models.site_page import SitePage
from src.site_pages.models.site_page_index_status import SitePageIndexStatus
from src.site_search.models.site_search_daily import SiteSearchDaily
from src.site_search.models.site_search_sync import SiteSearchSync
from src.site_traffic.models.site_traffic_landing_daily import SiteTrafficLandingDaily
from src.site_traffic.models.site_traffic_pages_daily import SiteTrafficPagesDaily
from src.site_traffic.models.site_traffic_totals_daily import SiteTrafficTotalsDaily
from src.sites.models.site import Site
from src.technical_seo.models.site_audit_run import SiteAuditRun
from src.technical_seo.models.site_issue import SiteIssue
from src.technical_seo.models.site_page_issue import SitePageIssue
from src.technical_seo.tools import create_site_issue, reject_issue, restore_issue

DESK = "site"
TABLES = desk_tables(
    Site,
    SitePage,
    SiteChunk,
    SitePageIndexStatus,
    SiteCrawlJob,
    SiteAnalysisJob,
    SitePageAnalysis,
    SiteAuditRun,
    SiteIssue,
    SitePageIssue,
    SiteSearchDaily,
    SiteSearchSync,
    SiteTrafficTotalsDaily,
    SiteTrafficPagesDaily,
    SiteTrafficLandingDaily,
)
GUIDES = desk_guides("workflow", "pages", "technical-seo", "search-data")

ASK = AskDesk(
    title="Site",
    produces="an answer about what this website is and says",
    pen="""One family of writes on this desk. You can **record a site-level technical issue** with create_site_issue when the user confirms one the audit missed. You can **turn an issue down** with reject_issue, site-wide by kind or for one page. Always pass the user's reason. You can bring one back with restore_issue. Rejections are the user's standing decisions. Never reject on your own judgement. Show an existing rejection reason before you recommend the same fix again.

You can also **write a note for later tasks**. Use save_note when the user states a rule or corrects you and agrees it is worth keeping. Use update_note to fold overlap into an existing note. Use delete_note only when they ask. Notes are in the user's words and saved once they agree to the wording.

Everything else here is a read. The Website profile screen is where the user edits the website's record and settings.

**You do not crawl.** The crawl runs on the user's own machine from the "Crawl website" button on this desk. It spends no model and no vendor credit. If the crawl never ran, or ran months ago, say so and point at that button. There is no tool for it here. A worker rebuilds the search passages on its own schedule. There is nothing to trigger there either.""",
    extra=[
        "**Read the data rules at the end of this prompt before you analyze.** They cover crawl facts, the user's notes and staleness.",
        "**Answer analytical questions with SQL.** For counts, averages and groupings, query the tables with run_sql. Never walk pages to compute a number.",
    ],
    elsewhere=[
        "Judging a page, or fixing one in code → **Pages**.",
        "Writing a page for the site → **Content**; a post → **Social**.",
        "Sending anything to anyone → **Outreach**.",
        "Charting or exploring a file the user uploads → **Analytics**.",
    ],
)

scope = AgentScope(
    desk=DESK,
    tables=TABLES,
    guides=GUIDES,
    writes=[create_site_issue, reject_issue, restore_issue],
    limits={"maxTurns": 60, "maxBudgetUsd": 3},
    system_prompt=ask_prompt(ASK),
)
