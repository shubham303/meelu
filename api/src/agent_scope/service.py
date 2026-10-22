from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.security import READABLE_TABLES
from src.agent_scope.guides import render_guides
from src.agent_scope.lib import AgentScope, SiteRef
from src.agent_scope.registry import (
    AGENT_SCOPES,
    DESK_BLURBS,
    LOADABLE_DESKS,
    WORKSPACE,
    desk_addition,
)
from src.agent_scope.schemas import AgentScopeResponse, DeskOffer
from src.connected_apps.catalog import DESKS as ACCOUNT_DESKS
from src.core.orm import Base
from src.sites.repository import sites

ACCOUNTS_PROMPT = """

## The user's own accounts

The {desks} desks act inside accounts the user connects: draft emails and newsletters, CMS drafts, CRM contacts and notes, Notion and Google Docs pages, and replies on Reddit, LinkedIn and GitHub. When the user asks for one of those, load that desk; if the account is not connected yet, it hands you a sign-in link for the user. Where this prompt says Meelu never sends, posts or publishes, that means never on its own: through those desks you act only when the user asks, and the user approves each write. No desk can send a LinkedIn direct message or post on X; say so plainly when asked."""


class AgentScopeService:
    async def scope(
        self,
        db: AsyncSession,
        user_id: str,
        action: str,
        site_id: str | None,
        desks: str,
    ) -> AgentScopeResponse:
        scope = self.resolve_scope(action)
        if not site_id and not scope.is_global:
            raise HTTPException(400, "This action needs a website — send x-meelu-site.")
        site_ref = None
        if site_id:
            site = await sites.get(db, user_id, site_id)
            if site is None:
                raise HTTPException(404, f"No website {site_id} in this workspace.")
            site_ref = SiteRef(id=site.id, name=site.name, domain=site.domain)
        return self.scope_response(action, scope, site_ref, desks)

    def resolve_scope(self, action: str) -> AgentScope:
        scope = AGENT_SCOPES.get(action)
        if scope is None:
            raise HTTPException(
                404,
                f'Unknown agent action "{action}". Known: {", ".join(AGENT_SCOPES)}.',
            )
        return scope

    def render_tables(self, tables: tuple[type[Base], ...] | None) -> str:
        if tables is None:
            listed = [t for t in Base.metadata.sorted_tables if t.name in READABLE_TABLES]
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

    def resolve_extra_desks(self, scope: AgentScope, desks: str) -> list[str]:
        requested = list(dict.fromkeys(part.strip() for part in desks.split(",") if part.strip()))
        for name in requested:
            if name not in LOADABLE_DESKS:
                raise HTTPException(
                    400, f"Unknown desk {name!r}. Loadable: {', '.join(sorted(LOADABLE_DESKS))}."
                )
        return [
            name for name in dict.fromkeys([*scope.loaded_desks, *requested]) if name != scope.desk
        ]

    def accounts_prompt(self, scope: AgentScope) -> str:
        if scope.is_global or scope.desk == WORKSPACE:
            return ""
        return ACCOUNTS_PROMPT.format(desks=", ".join(ACCOUNT_DESKS))

    def desk_brief(self, desk_name: str) -> str:
        addition = desk_addition(desk_name)
        writes = ", ".join(f"`{w}`" for w in addition.write_names) or "none"
        return (
            f"The {desk_name} desk is loaded. Its tools are in your tool list now. "
            f"Writes it adds, which this task may now call (the user approves each): {writes}."
            + (self.render_tables(addition.tables) if addition.tables else "")
            + render_guides(addition.guides)
        )

    def scope_response(
        self, action: str, scope: AgentScope, site: SiteRef | None, desks: str = ""
    ) -> AgentScopeResponse:
        extra = [desk_addition(name) for name in self.resolve_extra_desks(scope, desks)]
        loaded = {scope.desk, *(a.desk for a in extra)}

        writes = list(dict.fromkeys(scope.write_names + [w for a in extra for w in a.write_names]))
        silent = list(
            dict.fromkeys(
                scope.silent_write_names + [w for a in extra for w in a.silent_write_names]
            )
        )
        tables = (
            None
            if scope.tables is None
            else tuple(dict.fromkeys([*scope.tables] + [t for a in extra for t in a.tables]))
        )
        guides = tuple(dict.fromkeys([*scope.guides] + [g for a in extra for g in a.guides]))
        local_tools = list(
            dict.fromkeys(scope.local_tools + [t for a in extra for t in a.local_tools])
        )

        return AgentScopeResponse(
            action=action,
            writes=writes,
            desk=scope.desk,
            create_tool_name=scope.create_tool_names,
            is_global=scope.is_global,
            allow_attachments=scope.allow_attachments,
            limits=scope.limits,
            providers=scope.providers,
            local_tools=local_tools,
            silent_writes=silent,
            loaded_desks=list(scope.loaded_desks),
            desks=[
                DeskOffer(name=name, blurb=blurb, brief=self.desk_brief(name))
                for name, blurb in sorted(DESK_BLURBS.items())
                if name not in loaded
            ],
            system_prompt=scope.system_prompt(site)
            + self.render_tables(tables)
            + render_guides(guides)
            + self.accounts_prompt(scope),
        )


agent_scope_service = AgentScopeService()
