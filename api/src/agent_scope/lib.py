from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from src.core.orm import Base

Tables = tuple[type[Base], ...]
Tool = Callable[..., Any]


@dataclass(frozen=True)
class SiteRef:
    id: str
    name: str
    domain: str


@dataclass
class AgentScope:
    desk: str
    system_prompt: Callable[[SiteRef | None], str]
    tables: tuple[type[Base], ...] | None = None
    guides: tuple[str, ...] = ()
    writes: list[Tool] = field(default_factory=list)
    create_tool: Tool | list[Tool] | None = None
    is_global: bool = False
    allow_attachments: bool = True
    limits: dict[str, Any] = field(default_factory=dict)
    providers: list[str] = field(default_factory=list)
    local_tools: list[str] = field(default_factory=list)
    silent_writes: list[Tool] = field(default_factory=list)
    loaded_desks: tuple[str, ...] = ()

    @property
    def table_names(self) -> frozenset[str] | None:
        if self.tables is None:
            return None
        return frozenset(t.__tablename__ for t in self.tables)

    @property
    def write_names(self) -> list[str]:
        return [w.__name__ for w in self.writes]

    @property
    def silent_write_names(self) -> list[str]:
        return [w.__name__ for w in self.silent_writes]

    @property
    def create_tool_names(self) -> str | list[str] | None:
        if self.create_tool is None:
            return None
        if isinstance(self.create_tool, list):
            return [mcp_name(t) for t in self.create_tool]
        return mcp_name(self.create_tool)


def mcp_name(tool: Tool) -> str:
    return f"mcp__meelu__{tool.__name__}"


def fill(template: str, site: SiteRef | None) -> str:
    if site is None:
        return template
    return (
        template.replace("{{name}}", site.name)
        .replace("{{domain}}", site.domain)
        .replace("{{id}}", site.id)
    )


def desk_tables(*tables: type[Base]) -> tuple[type[Base], ...]:
    from src.notes.models.notes import Note

    return tuple(dict.fromkeys((*tables, Note)))


def desk_guides(*guides: str) -> tuple[str, ...]:
    return (*guides, "notes")
