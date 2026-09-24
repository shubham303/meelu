from src.agent_scope.ask import AskDesk, ask_prompt
from src.agent_scope.lib import AgentScope, desk_guides, desk_tables
from src.crawl_jobs.models.site_crawl_job import SiteCrawlJob
from src.site_pages.models.site_page_llm_extraction import SitePageLlmExtraction
from src.site_pages.models.site_chunk import SiteChunk
from src.site_pages.models.site_page import SitePage
from src.site_search.models.site_page_index_status import SitePageIndexStatus
from src.site_pages.models.site_page_link import SitePageLink
from src.site_search.models.site_search_daily import SiteSearchDaily
from src.site_search.models.site_search_sync import SiteSearchSync
from src.site_structure.models.link_suggestion import LinkSuggestion
from src.site_structure.models.pillar_page_suggestion import PillarPageSuggestion
from src.site_structure.models.structure_job import StructureJob
from src.site_structure.tools import (
    finish_structure_job,
    propose_hierarchy_links,
    propose_link_removals,
    propose_pillar_pages,
    propose_unlinked_mentions,
    rank_link_suggestions,
    rank_pillar_suggestions,
    review_link_suggestions,
    review_pillar_suggestions,
    screen_link_suggestions,
    screen_pillar_suggestions,
    start_structure_job,
)
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
    SitePageLink,
    StructureJob,
    LinkSuggestion,
    PillarPageSuggestion,
    SitePageLlmExtraction,
    SiteCrawlJob,
    SiteAuditRun,
    SiteIssue,
    SitePageIssue,
    SiteSearchDaily,
    SiteSearchSync,
    SiteTrafficTotalsDaily,
    SiteTrafficPagesDaily,
    SiteTrafficLandingDaily,
)
GUIDES = desk_guides("workflow", "pages", "structure", "technical-seo", "search-data")

ASK = AskDesk(
    title="Site",
    produces="an answer about what this website is and says",
    pen="""One family of writes on this desk. You can **record a site-level technical issue** with create_site_issue when the user confirms one the audit missed. You can **turn an issue down** with reject_issue, site-wide by kind or for one page. Always pass the user's reason. You can bring one back with restore_issue. Rejections are the user's standing decisions. Never reject on your own judgement. Show an existing rejection reason before you recommend the same fix again.

You can **propose internal links** on the Structure screen. Open a job with start_structure_job and the prompt you are running; it hands back the job_id every suggestion carries. Pick the target pages with SQL over `site_pages`, `site_page_links`, `site_chunks` and the page types, then generate: propose_unlinked_mentions (target page ids plus the phrases a passage would use for them) for links a passage should carry, propose_hierarchy_links for the skeleton (home to and from hubs and utility pages, hub to hub by URL path) where text similarity says nothing. Saved rows are drafts and invisible to the user. Run screen_link_suggestions next: a cheap model throws out the clear noes. Then review_link_suggestions with the prompt you are running: a stronger model reads every remaining draft one by one and is the only step that marks a row ready. Then rank_link_suggestions scores every open row and cuts to each page's link budget. Close with finish_structure_job. Only ready rows reach the user, who marks them done or turns them down on the Structure screen. Never mark done or turn down for them.

You can **propose removing links** the same way. The candidates are the links that exist today: select the edges your strategy targets with SQL over `site_page_links` (joined to the page types, link scores and anchors) into a workspace table with from_page_id, to_page_id and a reason column, then propose_link_removals with that table name. Be generous in the SQL; the tool keeps only body links, protects a target's last inlink and links to the home or a hub page, and scores the rest by how little the anchor's passage relates to the target. The same screen, review and rank steps then settle the delete rows alongside the add rows; rank never strips more than a third of a page's body links or leaves a target with fewer than two inlinks.

You can **propose pillar pages**: a hub a topic lacks. propose_pillar_pages with only the job_id clusters every embedded page by meaning; with a workspace table of group_key, page_id and optional topic it uses the groups your SQL built (a URL folder with no index page, pages sharing a keyword, pages ranking for the same queries). Each surviving group becomes a draft with the member pages, and becomes an expand suggestion when a page partly covers the group already. Then screen_pillar_suggestions, review_pillar_suggestions with your prompt (the reviewer writes the title and the brief), rank_pillar_suggestions to keep the few worth building, and finish_structure_job. Ready rows land on the Structure screen under pillar pages.

You can also **write a note for later tasks**. Use save_note when the user states a rule or corrects you and agrees it is worth keeping. Use update_note to fold overlap into an existing note. Use delete_note only when they ask. Notes are in the user's words and saved once they agree to the wording.

Everything else here is a read. The Website profile screen is where the user edits the website's record and settings.

**You do not crawl.** The crawl runs on the user's own machine from the "Crawl website" button on this desk. It spends no model and no vendor credit. If the crawl never ran, or ran months ago, say so and point at that button. There is no tool for it here. A worker rebuilds the search passages on its own schedule. There is nothing to trigger there either.""",
    extra=[
        "**Read the data rules at the end of this prompt before you analyze.** They cover crawl facts, the user's notes and staleness.",
        "**Answer analytical questions with SQL.** For counts, averages and groupings, query the tables with run_sql. Never walk pages to compute a number.",
        "**Page types come from the LLM extraction table.** `site_page_llm_extraction` holds one row per page with its `page_type` (money, hub, informational, support, company, legal, utility) and the model's `confidence` (0–1), classified on the server right after each crawl finishes. A page with no row, or whose row is behind the page's content hash, has not been classified yet: say so rather than guess, and treat a low confidence as a page the user should confirm. Never guess a page type from its URL.",
    ],
    elsewhere=[
        "Judging a page, or fixing one in code → **Pages**.",
        "Writing a page for the site → **Content**; a post → **Social**.",
        "Finding people or companies to partner with → **Lead Management**.",
        "Charting or exploring a file the user uploads → **Analytics**.",
    ],
)

scope = AgentScope(
    desk=DESK,
    tables=TABLES,
    guides=GUIDES,
    writes=[
        create_site_issue,
        reject_issue,
        restore_issue,
        start_structure_job,
        propose_hierarchy_links,
        propose_unlinked_mentions,
        propose_link_removals,
        screen_link_suggestions,
        review_link_suggestions,
        rank_link_suggestions,
        propose_pillar_pages,
        screen_pillar_suggestions,
        review_pillar_suggestions,
        rank_pillar_suggestions,
        finish_structure_job,
    ],
    limits={"maxTurns": 60, "maxBudgetUsd": 3},
    system_prompt=ask_prompt(ASK),
)
