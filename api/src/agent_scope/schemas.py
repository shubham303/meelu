from typing import Any

from pydantic import Field

from src.core.schemas import EntityModel


class DeskOffer(EntityModel):
    name: str
    blurb: str
    brief: str


class AgentScopeResponse(EntityModel):
    action: str
    writes: list[str]
    desk: str
    create_tool_name: str | list[str] | None
    is_global: bool = Field(alias="global")
    mcp_servers: dict[str, dict[str, Any]]
    limits: dict[str, Any]
    save_attachments: bool
    providers: list[str]
    desks: list[DeskOffer]
    system_prompt: str
