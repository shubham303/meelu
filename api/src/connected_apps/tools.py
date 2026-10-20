from typing import Any

from src.agent.context import require_site
from src.agent.server import ToolFn, tool
from src.connected_apps.catalog import DESKS, Desk
from src.connected_apps.schemas import ActionResult, AppStatus, ConnectedAppResponse, ConnectLink
from src.connected_apps.service import connected_app_service
from src.core.database import unit_of_work


def _named(fn: ToolFn, name: str, doc: str) -> ToolFn:
    fn.__name__ = name
    fn.__qualname__ = name
    fn.__doc__ = doc
    return fn


def _register(desk: Desk) -> dict[str, ToolFn]:
    apps_list = ", ".join(a.toolkit for a in desk.apps)

    async def apps() -> list[AppStatus]:
        ctx = require_site()
        async with unit_of_work() as db:
            return await connected_app_service.apps(db, ctx.user_id, ctx.site_id, desk.name)

    async def connect(app: str) -> ConnectLink:
        ctx = require_site()
        async with unit_of_work() as db:
            return await connected_app_service.connect(db, ctx.user_id, ctx.site_id, desk.name, app)

    async def read(
        action: str, arguments: dict[str, Any], connection_id: str | None = None
    ) -> ActionResult:
        ctx = require_site()
        async with unit_of_work() as db:
            return await connected_app_service.run(
                db, ctx.user_id, ctx.site_id, desk.name, "read", action, arguments, connection_id
            )

    async def write(
        action: str, arguments: dict[str, Any], connection_id: str | None = None
    ) -> ActionResult:
        ctx = require_site()
        async with unit_of_work() as db:
            return await connected_app_service.run(
                db, ctx.user_id, ctx.site_id, desk.name, "write", action, arguments, connection_id
            )

    async def disconnect(connection_id: str) -> ConnectedAppResponse:
        ctx = require_site()
        async with unit_of_work() as db:
            row = await connected_app_service.disconnect(
                db, ctx.user_id, ctx.site_id, desk.name, connection_id
            )
            return ConnectedAppResponse.model_validate(row)

    n = desk.name
    return {
        "apps": tool(desk=n)(
            _named(
                apps,
                f"{n}_apps",
                f"The {desk.noun} apps this website can connect ({apps_list}), its connections, and "
                "for each connected app the actions with their input schemas. Call it first.",
            )
        ),
        "connect": tool(desk=n)(
            _named(
                connect,
                f"{n}_connect",
                f"A sign-in link that connects the user's own {desk.noun} app to this website. "
                f"Give the user the full link, which opens in their browser; when they say they are "
                f"done, call {n}_apps.",
            )
        ),
        "read": tool(desk=n)(
            _named(
                read,
                f"{n}_read",
                f"Run a read action from {n}_apps on a connected app. connection_id only when "
                "the app has several connections.",
            )
        ),
        "write": tool(writes=True, desk=n)(
            _named(
                write,
                f"{n}_write",
                f"Run a write action from {n}_apps on a connected app. {desk.rule}",
            )
        ),
        "disconnect": tool(writes=True, desk=n)(
            _named(
                disconnect,
                f"{n}_disconnect",
                "Remove a connection from this website, so Meelu can no longer reach that account. "
                "Only when the user asks.",
            )
        ),
    }


DESK_TOOLS: dict[str, dict[str, ToolFn]] = {name: _register(d) for name, d in DESKS.items()}
