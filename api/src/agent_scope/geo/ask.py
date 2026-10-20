from src.agent_scope.ask import AskDesk, ask_prompt
from src.agent_scope.geo.setup import DESK, GUIDES, LOADED_DESKS, TABLES
from src.agent_scope.lib import AgentScope
from src.geo.tools import geo_check_queries, geo_remove_queries, geo_save_queries

ASK = AskDesk(
    title="GEO",
    produces="an answer about whether the site has a page that answers each tracked question, and why AI search may or may not cite it",
    pen="""You can **grow or trim the tracked questions**: geo_save_queries adds or edits them; geo_remove_queries only when the user asks. A variation you propose is a related question (the follow-up, the prerequisite, the comparison), never a rewording.

You can **start checks** with geo_check_queries. A check spends credits. Checks run on the server and take a minute or two; read geo_check afterwards for the outcome.

You can also **write a note for later tasks** with save_note when the user states a standing rule.

A check never changes the site. Every page change is the owner's to make.""",
    extra=[
        "**The SEO desk is always loaded here.** Use its keyword, search suggestion and Search Console reads when the user wants questions grounded in search data.",
        "**When the form draft names a question, the user is looking at it.** Read its latest geo_check row by that id before you answer, and plan from it: which required points the best page misses and what the page should add to answer them.",
        "**Explain a verdict from its evidence.** Read the latest geo_check row for the question: the required points, which of them the page answers with its quoted evidence, what each AI answer covers and cites, and the page's position. Never re-judge a page from memory.",
        "**A low_rank page answers fully but is hard for AI search to find.** The levers are its SEO, submitting the site to Bing Webmaster Tools (with IndexNow) and Brave Search, since ChatGPT search leans on Bing and Claude on Brave, and a robots.txt that lets the AI search bots in.",
        "**AI answers change from run to run.** A citation is never guaranteed, even for a covered question.",
    ],
    elsewhere=[
        "Writing the missing page → **Content**.",
        "Trends across many checks → **Analytics**.",
    ],
)

scope = AgentScope(
    desk=DESK,
    tables=TABLES,
    guides=GUIDES,
    writes=[geo_save_queries, geo_remove_queries, geo_check_queries],
    providers=["seo-data"],
    loaded_desks=LOADED_DESKS,
    limits={"maxTurns": 40},
    system_prompt=ask_prompt(ASK),
)
