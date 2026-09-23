import src.providers.seo_data.tools  # noqa: F401
from src.agent import server
from src.agent_scope.analytics import ACTIONS as ANALYTICS_ACTIONS
from src.agent_scope.content import ACTIONS as CONTENT_ACTIONS
from src.agent_scope.leads import ACTIONS as LEADS_ACTIONS
from src.agent_scope.lib import AgentScope
from src.agent_scope.pages import ACTIONS as PAGES_ACTIONS
from src.agent_scope.plan import scope as plan
from src.agent_scope.profile import ACTIONS as PROFILE_ACTIONS
from src.agent_scope.seo import ACTIONS as SEO_ACTIONS
from src.agent_scope.site import ACTIONS as SITE_ACTIONS
from src.agent_scope.social_listening import ACTIONS as SOCIAL_LISTENING_ACTIONS
from src.agent_scope.technical_seo import ACTIONS as TECHNICAL_SEO_ACTIONS
from src.notes.tools import delete_note, save_note, update_note

WRITE_TOOLS = frozenset(server.WRITE_TOOLS)
WRITE_TOOL_NAMES = frozenset(t.__name__ for t in WRITE_TOOLS)

NOTE_TOOLS = (save_note, update_note, delete_note)

AGENT_SCOPES: dict[str, AgentScope] = {
    "plan": plan,
    **SITE_ACTIONS,
    **PAGES_ACTIONS,
    **TECHNICAL_SEO_ACTIONS,
    **CONTENT_ACTIONS,
    **LEADS_ACTIONS,
    **PROFILE_ACTIONS,
    **SEO_ACTIONS,
    **ANALYTICS_ACTIONS,
    **SOCIAL_LISTENING_ACTIONS,
}


WORKSPACE = "workspace"

DESK_NAMES = frozenset(scope.desk for scope in AGENT_SCOPES.values())

DESK_BLURBS: dict[str, str] = {
    "profile": "The business profile record — who the user is, what they sell, voice and positioning; save or clear its fields.",
    "site": "The website record and site-wide technical issues — record one the audit missed, reject or restore one.",
    "pages": "The crawled page corpus — search pages by text or crawl facts.",
    "technical-seo": "The technical audit — open issues, turn-downs, reject or restore findings.",
    "seo": "Search performance — keywords, clusters, competitors and page suggestions: propose pages to add, edit or merge from Search Console and keyword evidence.",
    "content": "Written pieces — create and revise pieces, channel rules.",
    "leads": "Lead management — campaign briefs, discovery runs, and the lead list with fit scores and evidence; shape briefs, keep stages honest, curate the shortlist.",
    "social-listening": "Found social posts asking for what the site sells, brand and competitor mentions — set reply angles and statuses, grow the query and competitor lists, export the posts as a CSV.",
    "analytics": "The analytics engine — sessions over CSVs and workspace tables: profiling, clustering, forecasting, reports.",
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
    mcp_servers = {k: v for s in scopes for k, v in s.mcp_servers.items()}
    silent = list(dict.fromkeys(w for s in scopes for w in s.silent_writes))
    return AgentScope(
        desk=desk_name,
        system_prompt=lambda site: "",
        tables=tuple(tables),
        guides=guides,
        writes=writes,
        mcp_servers=mcp_servers,
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
