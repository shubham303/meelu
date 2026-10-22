import src.agent.tools.core
import src.connected_apps.tools
import src.data_analytics.tools
import src.providers.seo_data.tools
import src.scratchpad.tools
import src.seo.search_suggestions.tools
import src.seo.serp_history.tools
import src.seo.serp_results.tools  # noqa: F401
from src.agent import server
from src.agent_scope.analytics import ACTIONS as ANALYTICS_ACTIONS
from src.agent_scope.content import ACTIONS as CONTENT_ACTIONS
from src.agent_scope.find_leads import ACTIONS as FIND_LEADS_ACTIONS
from src.agent_scope.geo import ACTIONS as GEO_ACTIONS
from src.agent_scope.lib import AgentScope
from src.agent_scope.overview import ACTIONS as OVERVIEW_ACTIONS
from src.agent_scope.pages import ACTIONS as PAGES_ACTIONS
from src.agent_scope.plan import scope as plan
from src.agent_scope.profile import ACTIONS as PROFILE_ACTIONS
from src.agent_scope.reports import ACTIONS as REPORTS_ACTIONS
from src.agent_scope.seo import ACTIONS as SEO_ACTIONS
from src.agent_scope.site import ACTIONS as SITE_ACTIONS
from src.agent_scope.social_listening import ACTIONS as SOCIAL_LISTENING_ACTIONS
from src.agent_scope.technical_seo import ACTIONS as TECHNICAL_SEO_ACTIONS
from src.connected_apps.catalog import DESKS as CONNECTED_APP_DESKS
from src.notes.tools import delete_note, save_note, update_note

WRITE_TOOLS = frozenset(server.WRITE_TOOLS)
WRITE_TOOL_NAMES = frozenset(t.__name__ for t in WRITE_TOOLS)

NOTE_TOOLS = (save_note, update_note, delete_note)

AGENT_SCOPES: dict[str, AgentScope] = {
    "plan": plan,
    **OVERVIEW_ACTIONS,
    **SITE_ACTIONS,
    **SEO_ACTIONS,
    **PAGES_ACTIONS,
    **TECHNICAL_SEO_ACTIONS,
    **CONTENT_ACTIONS,
    **PROFILE_ACTIONS,
    **ANALYTICS_ACTIONS,
    **SOCIAL_LISTENING_ACTIONS,
    **FIND_LEADS_ACTIONS,
    **GEO_ACTIONS,
    **REPORTS_ACTIONS,
}


WORKSPACE = "workspace"

DESK_NAMES = frozenset(scope.desk for scope in AGENT_SCOPES.values())

DESK_BLURBS: dict[str, str] = {
    "profile": "The business profile record — who the user is, what they sell, voice and positioning; save or clear its fields.",
    "site": "The website record and site-wide technical issues — record one the audit missed, reject or restore one.",
    "seo": "Keyword research and search competition — build keyword clusters (with intent and importance), read live and past Google results and search suggestions, track search volume, and curate competitors and backlink opportunities over Search Console and Analytics.",
    "pages": "The crawled page corpus — search pages by text or crawl facts.",
    "technical-seo": "The technical audit — open issues, turn-downs, reject or restore findings.",
    "content": "Web pages written for the site — create and revise pieces with their title, H1, meta description, slug and target keyword.",
    "social-listening": "Social posts where a reply from the site belongs, found from the lines of text the user listens for — set reply angles and statuses, grow the list of lines.",
    "find-leads": "People worth a personal message, found from the briefs the user writes — mark leads contacted or discarded, add or reword briefs.",
    "geo": "Questions people ask AI search — whether a page on the site answers each one, what ChatGPT, Claude and AI Overviews say and cite; add, remove and check tracked questions.",
    "analytics": "Analysis over this website's Search Console, Analytics and page data in the database — profiling, clustering, forecasting, period comparison, metric drivers; save reports.",
    **{d.name: d.blurb for d in CONNECTED_APP_DESKS.values()},
}
LOADABLE_DESKS = frozenset(DESK_BLURBS)


def desk_addition(desk_name: str) -> AgentScope:
    scopes = [s for s in AGENT_SCOPES.values() if s.desk == desk_name]
    tagged_writes = [
        fn
        for fn in sorted(server.WRITE_TOOLS, key=lambda f: f.__name__)
        if server.TOOL_DESKS.get(fn) == desk_name
    ]
    writes = list(dict.fromkeys([w for s in scopes for w in s.writes] + tagged_writes))
    tables = list(dict.fromkeys(t for s in scopes if s.tables for t in s.tables))
    guides = tuple(dict.fromkeys(g for s in scopes for g in s.guides))
    local_tools = list(dict.fromkeys(t for s in scopes for t in s.local_tools))
    silent = list(dict.fromkeys(w for s in scopes for w in s.silent_writes))
    return AgentScope(
        desk=desk_name,
        system_prompt=lambda site: "",
        tables=tuple(tables),
        guides=guides,
        writes=writes,
        local_tools=local_tools,
        silent_writes=silent,
    )


def _attach_note_tools() -> None:
    for scope in AGENT_SCOPES.values():
        if scope.desk == WORKSPACE or scope.is_global:
            continue
        scope.writes = [w for w in scope.writes if w not in NOTE_TOOLS] + list(NOTE_TOOLS)


def _verify() -> None:
    for action, scope in AGENT_SCOPES.items():
        for tool in scope.writes:
            if tool not in WRITE_TOOLS:
                raise RuntimeError(f"{action}: {tool.__name__} is not a registered write tool.")
        creates = scope.create_tool if isinstance(scope.create_tool, list) else [scope.create_tool]
        for tool in creates:
            if tool is not None and tool not in scope.writes:
                raise RuntimeError(f"{action}: create_tool {tool.__name__} is not in its writes.")


_attach_note_tools()
_verify()


def desk_writes(desk_name: str) -> frozenset[str]:
    return frozenset(
        name
        for scope in AGENT_SCOPES.values()
        if scope.desk == desk_name
        for name in scope.write_names
    )
