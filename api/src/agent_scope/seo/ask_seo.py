from src.agent_scope.ask import AskDesk, ask_prompt
from src.agent_scope.lib import AgentScope, desk_guides, desk_tables
from src.seo.keyword_clusters.models.seo_keyword_cluster import SeoKeywordCluster
from src.seo.keyword_clusters.models.seo_keyword_cluster_competitor import (
    SeoKeywordClusterCompetitor,
)
from src.seo.keyword_clusters.tools import compute_metrics_for_cluster, create_keyword_clusters
from src.seo.keyword_tracking.models.seo_rank_history import SeoRankHistory
from src.seo.keyword_tracking.models.seo_volume_history import SeoVolumeHistory
from src.seo.keyword_tracking.tools import track_keyword_rankings, track_keyword_volumes
from src.seo.market import ENGLISH_MARKETS
from src.seo.site_search.models.site_page_index_status import SitePageIndexStatus
from src.seo.site_search.models.site_search_daily import SiteSearchDaily
from src.seo.site_search.models.site_search_sync import SiteSearchSync
from src.seo.site_seo.models.seo_competitor import SeoCompetitor
from src.seo.site_seo.models.site_seo import SiteSeo
from src.seo.site_seo.tools import add_to_seo_list, remove_from_seo_list
from src.seo.site_traffic.models.site_traffic_channels_daily import SiteTrafficChannelsDaily
from src.seo.site_traffic.models.site_traffic_landing_daily import SiteTrafficLandingDaily
from src.seo.site_traffic.models.site_traffic_pages_daily import SiteTrafficPagesDaily
from src.seo.site_traffic.models.site_traffic_sync import SiteTrafficSync
from src.seo.site_traffic.models.site_traffic_totals_daily import SiteTrafficTotalsDaily
from src.sites.models.site import Site
from src.sites.tools import save_site_market

DESK = "seo"

MARKET_RULE = (
    "**Every search answer is for a market.** The website record holds it: `markets` (country "
    "codes) and `language` on the `site` table. When `markets` is empty and the language is "
    "English or unset, the market is English-speaking searchers worldwide ("
    + ", ".join(ENGLISH_MARKETS)
    + "). If the record has no markets, deduce them from the domain and what the site says, "
    "then ask the user to confirm and save them with save_site_market. The finding and "
    "tracking tools cover every market on the record unless one location_code is passed; "
    "the history tables keep one row per market, so sum or compare across `location_code` "
    "in SQL. Vendor tools that take a single location_code cover one market per call: say "
    "which one an answer rests on."
)
TABLES = desk_tables(
    Site,
    SiteSeo,
    SeoKeywordCluster,
    SeoKeywordClusterCompetitor,
    SeoCompetitor,
    SeoRankHistory,
    SeoVolumeHistory,
    SiteSearchDaily,
    SiteSearchSync,
    SitePageIndexStatus,
    SiteTrafficTotalsDaily,
    SiteTrafficChannelsDaily,
    SiteTrafficLandingDaily,
    SiteTrafficPagesDaily,
    SiteTrafficSync,
)
GUIDES = desk_guides("workflow", "search-data")

ASK = AskDesk(
    title="SEO",
    produces="an answer about how this website performs in search and who it competes with",
    pen="""One family of writes on this desk: the website's saved SEO lists. `seo_competitors` holds the domains this website competes with in search, one row each; `backlink_opportunities` on `site_seo` (one row per website) holds domains worth asking for a link.

Find candidates with find_competitors and find_backlink_opportunities; both spend vendor credit, so run each once per question rather than per idea. Save the ones that belong with add_to_seo_list and take out the ones that do not with remove_from_seo_list. A competitor belongs when it chases the same searchers for the same thing, not when it merely ranks for the same words: marketplaces, encyclopedias, forums and news sites share keywords with everyone. A backlink opportunity belongs when a real editor could plausibly link this website for the same reason they link the competitor; skip spam, directories that link anything, and the competitors themselves. Say what you will add or remove and why, then do it.

You can also **write a note for later tasks** with save_note when the user states a rule or corrects you and agrees it is worth keeping; update_note folds overlap into an existing note, and delete_note is only for when they ask.

You can **build keyword clusters** to decide what to target. create_keyword_clusters builds clusters in `seo_keyword_clusters` from one `source`: seed keywords you choose with the user, this website's Search Console queries, the keywords it already ranks for, or competitor keywords (two or more saved competitors rank for them and this website does not). Noise and off-topic keywords are dropped first, then keywords Google would answer with the same pages share one cluster. `is_ranked` says whether this website ranks for any keyword of the cluster, and `seo_keyword_cluster_competitors` links each cluster to the saved competitors (`seo_competitors`) that rank for it. Every cluster is worked through its `main_keyword`, the member with the most clickstream searches, and `volume` is that keyword's clickstream volume; never treat the other members as separate targets. compute_metrics_for_cluster scores each cluster's `winnability` (0 to 100): how far a page of this website could climb past the results above it, from their link authority against ours and how well each one serves the search. A result that misses the intent is easy to pass however strong it is. The row keeps `likely_position`, `p_top_three`, `p_page_one`, `our_position` when we already rank, and the evidence per result in `climb`. Pick targets with SQL over that table, ordered by `winnability` then `volume`, filtered by topic or phrase; score only the clusters the question needs, and fetch a raw results page only when the score is not enough.

You can **track keywords over time**. track_keyword_rankings records today's top organic results for the keywords you pass into `seo_rank_history` (one row per keyword, day and ranking URL, with `is_site` marking this website's pages) and backfills the last twelve monthly snapshots the first time a keyword is tracked. track_keyword_volumes records monthly search volume, Google Ads and clickstream, into `seo_volume_history`. Track only the keywords the question needs; both spend vendor credit. Once tracked, answer movement questions (pages going up or down, a competitor overtaking, seasonal demand) with SQL over those tables rather than tracking again.

Everything else here is a read.""",
    extra=[
        MARKET_RULE,
        "**Search Console and Analytics are measured; vendor numbers are estimates.** Say which is which whenever both appear in one answer.",
        "**Answer analytical questions with SQL.** For counts, trends and groupings over search or traffic data, query the tables with run_sql.",
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
        add_to_seo_list,
        remove_from_seo_list,
        track_keyword_rankings,
        track_keyword_volumes,
        save_site_market,
        create_keyword_clusters,
        compute_metrics_for_cluster,
    ],
    providers=["seo-data"],
    limits={"maxTurns": 40, "maxBudgetUsd": 2},
    system_prompt=ask_prompt(ASK),
)
