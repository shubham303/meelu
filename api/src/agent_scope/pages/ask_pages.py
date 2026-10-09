from src.agent_scope.ask import AskDesk, ask_prompt
from src.agent_scope.lib import AgentScope, desk_guides, desk_tables
from src.crawl_jobs.models.site_crawl_job import SiteCrawlJob
from src.seo.site_search.models.site_page_index_status import SitePageIndexStatus
from src.site_pages.models.site_chunk import SiteChunk
from src.site_pages.models.site_page import SitePage
from src.site_pages.models.site_page_link import SitePageLink
from src.site_pages.models.site_page_llm_extraction import SitePageLlmExtraction
from src.site_pages.tools import set_page_type
from src.sites.models.site import Site

DESK = "pages"
TABLES = desk_tables(
    Site,
    SitePage,
    SitePageLink,
    SiteChunk,
    SitePageIndexStatus,
    SitePageLlmExtraction,
    SiteCrawlJob,
)
GUIDES = desk_guides("workflow", "pages")

ASK = AskDesk(
    title="Pages",
    produces="an answer about the site's pages — what they say, and what the crawl recorded",
    pen="Nothing on this desk changes a page. The one write is the page type on a page the classifier left unset.",
    extra=[
        "**Search before you fetch.** A question about what the site covers is a search with search_page and `search_text`. Do not walk every page. An empty result is a real answer: it means a gap.",
        "**Crawl facts are a filter, not a search.** The same tool filters on 404s, thin pages, orphan pages, and pages the sitemap misses. Then read the few that matter from `site_pages` with run_sql.",
        """**"How many" is one SQL count.** Count with run_sql over `site_pages`. Anything beyond a count belongs to the Analytics desk over the downloaded corpus, never a walk through the page list here.""",
        "**You do not crawl.** The crawl runs on the user's own machine from the Crawl button on the Site desk. If the crawl never ran, or ran months ago, say so and point at that button.",
        "**Say when knowledge is stale.** Every page carries the date it was last read. Do not answer from a months-old corpus as though it were current.",
        "**A missing page type is yours to fill.** The classifier leaves the type unset when it is not confident. If you have read a page whose type is missing, set it with set_page_type — from what the page is for, not how it is worded. Never touch a page that already has one, and never go looking for unset pages as a task of its own.",
        "**Read the notes before you write anything the user will see.** The `notes` table holds what the user already told you about this website. Read it with SQL. A note that contradicts your plan is the answer.",
    ],
    elsewhere=[
        "Changing the website's record or settings → **Site**; saving a note for later tasks → **Notes**.",
        "Judging audit findings and drafting fix briefs → **Technical SEO**.",
        "Writing a page for the site → **Content**.",
        "Counts, averages, groupings and trends over the whole site → **Analytics**, fed by the site's CSV download.",
    ],
)

scope = AgentScope(
    desk=DESK,
    tables=TABLES,
    guides=GUIDES,
    writes=[set_page_type],
    silent_writes=[set_page_type],
    limits={"maxTurns": 60, "maxBudgetUsd": 3},
    system_prompt=ask_prompt(ASK),
)
