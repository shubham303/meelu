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
    allow_attachments: bool
    limits: dict[str, Any]
    providers: list[str]
    local_tools: list[str]
    silent_writes: list[str]
    desks: list[DeskOffer]
    system_prompt: str
