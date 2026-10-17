from src.agent_scope.ask import AskDesk, ask_prompt
from src.agent_scope.lib import AgentScope, desk_guides, desk_tables
from src.reports.models.report import Report
from src.reports.tools import save_report, update_report
from src.seo.keyword_clusters.models.seo_keyword_cluster import SeoKeywordCluster
from src.seo.keyword_clusters.tools import (
    add_keywords_to_clusters,
    compute_metrics_for_cluster,
    create_keyword_clusters_from_competitors,
    create_keyword_clusters_from_search_console,
    create_keyword_clusters_from_seeds,
    delete_keyword_clusters,
    remove_keywords_from_cluster,
)
from src.seo.keyword_tracking.models.seo_volume_history import SeoVolumeHistory
from src.seo.keyword_tracking.tools import track_keyword_volumes
from src.seo.site_search.models.site_page_index_status import SitePageIndexStatus
from src.seo.site_search.models.site_search_daily import SiteSearchDaily
from src.seo.site_search.models.site_search_sync import SiteSearchSync
from src.seo.site_seo.models.site_backlink import SiteBacklink
from src.seo.site_seo.models.site_competitor import SiteCompetitor
from src.seo.site_seo.tools import (
    add_competitors,
    dismiss_backlink_opportunities,
    fetch_competitor_backlinks,
    remove_backlink_domain,
    remove_competitors,
)
from src.seo.site_traffic.models.site_traffic_channels_daily import SiteTrafficChannelsDaily
from src.seo.site_traffic.models.site_traffic_landing_daily import SiteTrafficLandingDaily
from src.seo.site_traffic.models.site_traffic_pages_daily import SiteTrafficPagesDaily
from src.seo.site_traffic.models.site_traffic_sync import SiteTrafficSync
from src.seo.site_traffic.models.site_traffic_totals_daily import SiteTrafficTotalsDaily
from src.sites.models.site import Site
from src.sites.tools import save_site_market

DESK = "seo"

TABLES = desk_tables(
    Site,
    SiteCompetitor,
    SiteBacklink,
    SeoKeywordCluster,
    SeoVolumeHistory,
    SiteSearchDaily,
    SiteSearchSync,
    SitePageIndexStatus,
    SiteTrafficTotalsDaily,
    SiteTrafficChannelsDaily,
    SiteTrafficLandingDaily,
    SiteTrafficPagesDaily,
    SiteTrafficSync,
    Report,
)
GUIDES = desk_guides("workflow", "search-data", "seo")

ASK = AskDesk(
    title="SEO",
    produces="an answer about how this website performs in search and who it competes with",
    pen="""This desk writes the website's saved SEO lists, its keyword clusters and its tracked search volumes; how each works is in the SEO desk guide below.

When the user asks to keep an answer, **save it as a report** with save_report, desk "seo": self-contained HTML with inline CSS and inline SVG charts, real numbers from what you read, and where they came from and the date range. The app rejects markup that loads anything over the network. To change a saved report, use update_report with its id from the reports table.

You can also **write a note for later tasks** with save_note when the user states a rule or corrects you and agrees it is worth keeping; update_note folds overlap into an existing note, and delete_note is only for when they ask.

Everything else here is a read.""",
    extra=[
        "**You can read any public web page.** read_web_page loads it in a browser, scripts included, and returns what a crawl records: title, meta description, headings, word count, schema, dates, link counts and its first 1000 words. Use it to see what a competitor's page covers next to this website's own; it skips pages their robots.txt disallows.",
    ],
    elsewhere=[
        "Crawled pages, internal links and technical checks → **Site**.",
        "Judging a page, or fixing one in code → **Pages**.",
        "Writing a page for the site → **Content**.",
    ],
)

scope = AgentScope(
    desk=DESK,
    tables=TABLES,
    guides=GUIDES,
    writes=[
        add_competitors,
        fetch_competitor_backlinks,
        remove_competitors,
        dismiss_backlink_opportunities,
        remove_backlink_domain,
        track_keyword_volumes,
        save_site_market,
        create_keyword_clusters_from_seeds,
        create_keyword_clusters_from_search_console,
        create_keyword_clusters_from_competitors,
        add_keywords_to_clusters,
        compute_metrics_for_cluster,
        remove_keywords_from_cluster,
        delete_keyword_clusters,
        save_report,
        update_report,
    ],
    providers=["seo-data"],
    local_tools=["read_web_page"],
    limits={"maxTurns": 40, "maxBudgetUsd": 2},
    system_prompt=ask_prompt(ASK),
)
