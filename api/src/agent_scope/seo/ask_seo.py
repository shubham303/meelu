from src.agent_scope.ask import AskDesk, ask_prompt
from src.agent_scope.lib import AgentScope, desk_guides, desk_tables
from src.seo.clusters.model import SeoKeywordCluster
from src.seo.collect.tools import (
    collect_competitor_keywords,
    collect_competitors,
    collect_keywords,
    collect_serps,
)
from src.seo.competitor_keywords.model import SeoCompetitorKeyword
from src.seo.competitors.model import SeoCompetitor
from src.seo.gap.tools import propose_gap_pages, propose_topic_pages
from src.seo.generators.tools import propose_cannibalisation, propose_page_edits
from src.seo.jobs.model import SeoJob
from src.seo.jobs.tools import finish_seo_job, start_seo_job
from src.seo.keyword_content_pages.model import SeoKeywordContentPage
from src.seo.keyword_gsc_pages.model import SeoKeywordGscPage
from src.seo.keywords.model import SeoKeyword
from src.seo.page_facts.model import SeoPageFacts
from src.seo.page_suggestion_keywords.model import SeoPageSuggestionKeyword
from src.seo.page_suggestions.model import SeoPageSuggestion
from src.seo.page_suggestions.tools import save_page_suggestion
from src.seo.pipeline.tools import rank_page_suggestions, screen_page_suggestions
from src.seo.serp_results.model import SeoSerpResult
from src.seo.serp_snapshots.model import SeoSerpSnapshot
from src.seo.state.model import SeoSiteState
from src.sites.models.site import Site

DESK = "seo"
TABLES = desk_tables(
    Site,
    SeoSiteState,
    SeoJob,
    SeoPageFacts,
    SeoKeyword,
    SeoKeywordCluster,
    SeoKeywordGscPage,
    SeoKeywordContentPage,
    SeoCompetitor,
    SeoCompetitorKeyword,
    SeoSerpSnapshot,
    SeoSerpResult,
    SeoPageSuggestion,
    SeoPageSuggestionKeyword,
)
GUIDES = desk_guides("workflow", "seo")

ASK = AskDesk(
    title="SEO",
    produces="a short list of pages to add, edit or delete, grounded in search data",
    pen="""Every answer on this desk ends in page suggestions: add a page, edit a page, or delete and merge a page. They live on the SEO screen; you never list them in chat, you point at them.

Open a job with start_seo_job and the prompt you are running. It reconciles the standing suggestions first, tells you whether the precompute is pending, and hands back the job_id every row carries, plus how many ready rows the user already has per action. If the site has ready rows on the same topics, say so before generating more.

Generate drafts with the generators, never by hand-listing rows: propose_page_edits (Search Console and cluster evidence, one kind or all) and propose_cannibalisation (pairs of pages fighting for the same queries). Narrow them with page_ids or keyword_ids you selected with SQL. Each returns how many drafts it saved, which existing rows it collided with, and what it filtered and why. Drafts are invisible to the user. Then screen_page_suggestions (a cheap model throws out the clear noes), review_page_suggestions with the prompt you are running (it reads each draft one by one off your context with the live page, keyword and search facts, rewrites the suggestion and settles it), and rank_page_suggestions (keeps the budget per action as ready). Close with finish_seo_job. Only ready rows reach the user, who marks them done or turns them down on the SEO screen. Never mark done or turn down for them.

When a strategy needs a row no generator makes — you compared two pages yourself, the user named a topic — write it with save_page_suggestion. It lands ready; you are its reviewer, so hold it to the same bar.

Vendor data arrives through the collect tools and every one of them spends the job's vendor budget: collect_keywords (our ranked keywords, ideas per seed, facts), collect_competitors (candidates the user confirms on the SEO screen; stop and wait for that), collect_competitor_keywords (what confirmed competitors rank for), collect_serps (the top ten for a keyword, its questions and related searches; pass suggestion_ids to cover a job's drafts). Run one collect per turn unless the user asked for breadth, and use dry_run first when the set is large. Then propose_gap_pages (clusters competitors rank for and we do not) and propose_topic_pages (a topic the user names) make add drafts; review needs a search snapshot for an add, so collect_serps on the drafts before reviewing.

Everything else here is a read.

You can also **write a note for later tasks**. Use save_note when the user states a rule or corrects you and agrees it is worth keeping. Use update_note to fold overlap into an existing note. Use delete_note only when they ask.""",
    extra=[
        "**Read the data rules at the end of this prompt before you analyze.** They name every table, its grain, the states and the filters the generators apply.",
        "**Answer analytical questions with SQL.** Counts, groupings and trends come from run_sql over the seo tables. Never walk pages to compute a number.",
        "**Search Console is the ground truth for our positions.** `seo_keyword_gsc_pages` holds them; no vendor number replaces it.",
    ],
    elsewhere=[
        "Internal links and pillar pages → **Site**.",
        "Judging a page, or fixing one in code → **Pages**.",
        "Writing the page an add suggestion asks for → **Content**.",
        "Charting or exploring a file → **Analytics**.",
    ],
)

scope = AgentScope(
    desk=DESK,
    tables=TABLES,
    guides=GUIDES,
    writes=[
        start_seo_job,
        propose_page_edits,
        propose_cannibalisation,
        propose_gap_pages,
        propose_topic_pages,
        collect_keywords,
        collect_competitors,
        collect_competitor_keywords,
        collect_serps,
        save_page_suggestion,
        screen_page_suggestions,
        rank_page_suggestions,
        finish_seo_job,
    ],
    silent_writes=[
        propose_page_edits,
        propose_cannibalisation,
        propose_gap_pages,
        screen_page_suggestions,
        rank_page_suggestions,
        finish_seo_job,
    ],
    local_tools=["review_page_suggestions"],
    limits={"maxTurns": 60, "maxBudgetUsd": 3},
    system_prompt=ask_prompt(ASK),
)
