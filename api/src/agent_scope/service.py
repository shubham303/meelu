from fastapi import HTTPException

from src.agent.security import BLOCKED_TABLES
from src.agent_scope.guides import render_guides
from src.agent_scope.lib import AgentScope, SiteRef
from src.agent_scope.registry import (
    AGENT_SCOPES,
    DESK_BLURBS,
    LOADABLE_DESKS,
    desk_addition,
)
from src.agent_scope.schemas import AgentScopeResponse, DeskOffer
from src.core.orm import Base


def resolve_scope(action: str) -> AgentScope:
    scope = AGENT_SCOPES.get(action)
    if scope is None:
        raise HTTPException(
            404,
            f'Unknown agent action "{action}". Known: {", ".join(AGENT_SCOPES)}.',
        )
    return scope


def render_tables(tables: tuple[type[Base], ...] | None) -> str:
    if tables is None:
        listed = [t for t in Base.metadata.sorted_tables if t.name not in BLOCKED_TABLES]
    else:
        listed = [t.__table__ for t in tables]
    lines = [
        f"- {t.name}: " + ", ".join(f"{c.name} {str(c.type).lower()}" for c in t.columns)
        for t in sorted(listed, key=lambda t: t.name)
    ]
    return (
        "\n\n## The database\n\n"
        "Query with run_sql. These tables live in `public`, are read-only, and their rows "
        "are already filtered to this user; filter site-scoped tables by the current site's "
        "id. Your personal workspace schema is first on the search_path and fully writable "
        "— materialize derived work there (CREATE TABLE ... AS SELECT ...); list what it "
        "already holds via information_schema.columns.\n\n" + "\n".join(lines)
    )


def resolve_extra_desks(scope: AgentScope, desks: str) -> list[str]:
    requested = list(dict.fromkeys(part.strip() for part in desks.split(",") if part.strip()))
    for name in requested:
        if name not in LOADABLE_DESKS:
            raise HTTPException(
                400, f"Unknown desk {name!r}. Loadable: {', '.join(sorted(LOADABLE_DESKS))}."
            )
    return [name for name in requested if name != scope.desk]


def desk_brief(desk_name: str) -> str:
    addition = desk_addition(desk_name)
    writes = ", ".join(f"`{w}`" for w in addition.write_names) or "none"
    return (
        f"The {desk_name} desk is loaded. Its tools are in your tool list now. "
        f"Writes it adds: {writes}."
        + (render_tables(addition.tables) if addition.tables else "")
        + render_guides(addition.guides)
    )


def scope_response(
    action: str, scope: AgentScope, site: SiteRef | None, desks: str = ""
) -> AgentScopeResponse:
    extra = [desk_addition(name) for name in resolve_extra_desks(scope, desks)]
    loaded = {scope.desk, *(a.desk for a in extra)}

    writes = list(dict.fromkeys(scope.write_names + [w for a in extra for w in a.write_names]))
    silent = list(
        dict.fromkeys(scope.silent_write_names + [w for a in extra for w in a.silent_write_names])
    )
    tables = (
        None
        if scope.tables is None
        else tuple(dict.fromkeys([*scope.tables] + [t for a in extra for t in a.tables]))
    )
    guides = tuple(dict.fromkeys([*scope.guides] + [g for a in extra for g in a.guides]))
    mcp_servers = {k: v for a in extra for k, v in a.mcp_servers.items()} | scope.mcp_servers
    local_tools = list(dict.fromkeys(scope.local_tools + [t for a in extra for t in a.local_tools]))

    return AgentScopeResponse(
        action=action,
        writes=writes,
        desk=scope.desk,
        create_tool_name=scope.create_tool_names,
        is_global=scope.is_global,
        mcp_servers=mcp_servers,
        limits=scope.limits,
        save_attachments=scope.save_attachments,
        providers=scope.providers,
        local_tools=local_tools,
        silent_writes=silent,
        desks=[
            DeskOffer(name=name, blurb=blurb, brief=desk_brief(name))
            for name, blurb in sorted(DESK_BLURBS.items())
            if name not in loaded
        ],
        system_prompt=scope.system_prompt(site) + render_tables(tables) + render_guides(guides),
    )
