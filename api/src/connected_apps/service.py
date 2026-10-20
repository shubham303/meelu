import asyncio
import json
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.connected_apps import composio
from src.connected_apps.catalog import DESKS, ActionKind, App, Desk
from src.connected_apps.repository import connected_apps
from src.connected_apps.schemas import (
    ActionResult,
    AppAction,
    AppConnections,
    AppStatus,
    ConnectedAppRecord,
    Connection,
    ConnectLink,
)
from src.core.logging import get_logger
from src.providers.errors import ProviderRequestError

log = get_logger()

ACTIVE = "ACTIVE"
INITIATED = "INITIATED"
SCHEMA_TTL_S = 6 * 60 * 60
MAX_RESULT_CHARS = 60_000
PENDING_RETENTION = timedelta(days=1)
SWEEP_BATCH = 200


def composio_user(user_id: str, site_id: str) -> str:
    return f"{user_id}.{site_id}"


def _key(name: str) -> str:
    return name.lower().replace("_", "").replace("-", "")


class ConnectionNotFoundError(ValueError):
    pass


class ConnectedAppService:
    def __init__(self) -> None:
        self._auth_configs: dict[str, str] = {}
        self._auth_lock = asyncio.Lock()
        self._schemas: dict[str, tuple[float, dict[str, Any]]] = {}

    def desk(self, name: str) -> Desk:
        desk = DESKS.get(name)
        if desk is None:
            raise ValueError(f"Unknown desk {name!r}.")
        return desk

    async def list_connections(
        self, db: AsyncSession, user_id: str, site_id: str
    ) -> list[ConnectedAppRecord]:
        return await connected_apps.list_for_site(db, user_id, site_id)

    async def overview(self, db: AsyncSession, user_id: str, site_id: str) -> list[AppConnections]:
        rows = await self._refreshed(db, user_id, site_id, None)
        return [
            AppConnections(
                desk=desk.name,
                app=app.toolkit,
                name=app.name,
                connections=[
                    Connection(connection_id=r.id, status=r.status, label=r.label)
                    for r in rows
                    if r.desk == desk.name and r.toolkit == app.toolkit
                ],
            )
            for desk in DESKS.values()
            for app in desk.apps
        ]

    async def apps(
        self, db: AsyncSession, user_id: str, site_id: str, desk_name: str
    ) -> list[AppStatus]:
        desk = self.desk(desk_name)
        rows = await self._refreshed(db, user_id, site_id, desk.name)
        await db.commit()
        connected = [
            a for a in desk.apps if any(r.toolkit == a.toolkit for r in rows if r.status == ACTIVE)
        ]
        schemas = await self._tool_schemas([s for a in connected for s in (*a.reads, *a.writes)])
        out: list[AppStatus] = []
        for app in desk.apps:
            actions = []
            if app in connected:
                actions = [
                    self._action(app, slug, kind, schemas[slug])
                    for kind, slugs in (("read", app.reads), ("write", app.writes))
                    for slug in slugs
                    if slug in schemas
                ]
            out.append(
                AppStatus(
                    app=app.toolkit,
                    name=app.name,
                    connections=[
                        Connection(connection_id=r.id, status=r.status, label=r.label)
                        for r in rows
                        if r.toolkit == app.toolkit
                    ],
                    actions=actions,
                )
            )
        return out

    async def connect(
        self, db: AsyncSession, user_id: str, site_id: str, desk_name: str, toolkit: str
    ) -> ConnectLink:
        desk = self.desk(desk_name)
        app = desk.app(toolkit)
        if app is None:
            raise ValueError(
                f"{toolkit!r} is not a {desk.noun} app Meelu connects. "
                f"Choose one of: {', '.join(a.toolkit for a in desk.apps)}."
            )
        link = await self._link(app, composio_user(user_id, site_id))
        try:
            row = await connected_apps.create(
                db,
                user_id,
                site_id,
                desk.name,
                app.toolkit,
                link["connected_account_id"],
                INITIATED,
            )
            await db.commit()
        except Exception:
            await composio.delete_account(link["connected_account_id"])
            raise
        log.info(
            "connected_apps.link_created", desk=desk.name, toolkit=app.toolkit, site_id=site_id
        )
        return ConnectLink(
            app=app.toolkit,
            connection_id=row.id,
            url=link["redirect_url"],
            expires_at=link.get("expires_at"),
        )

    async def run(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        desk_name: str,
        kind: ActionKind,
        action: str,
        arguments: dict[str, Any],
        connection_id: str | None,
    ) -> ActionResult:
        desk = self.desk(desk_name)
        app = desk.app_for_action(action)
        if app is None:
            raise ValueError(
                f"{action} is not a {desk.noun} action. List the actions with the apps call."
            )
        actual = app.kind_of(action)
        if actual != kind:
            raise ValueError(f"{action} is a {actual} action; call the {desk.name}_{actual} tool.")
        schema = (await self._tool_schemas([action])).get(action)
        if schema is None:
            raise ValueError(f"{action} is not available from {app.name} right now.")
        self._check_arguments(app, action, arguments, schema)
        row = await self._connection(db, user_id, site_id, desk, app, connection_id)
        await db.commit()
        merged = {**arguments, **app.fixed_arguments.get(action, {})}
        started = time.monotonic()
        try:
            body = await composio.execute(
                action, composio_user(user_id, site_id), row.account_id, merged
            )
        except ProviderRequestError as exc:
            log.warning(
                "connected_apps.action_failed",
                desk=desk.name,
                action=action,
                status=exc.status,
                error=str(exc),
            )
            raise ValueError(f"{app.name} refused {action}: {exc}") from exc
        log.info(
            "connected_apps.action_ran",
            desk=desk.name,
            action=action,
            kind=kind,
            site_id=site_id,
            successful=bool(body.get("successful")),
            duration_ms=round((time.monotonic() - started) * 1000),
        )
        if not body.get("successful"):
            raise ValueError(
                f"{app.name} refused {action}: {body.get('error') or 'no reason given'}"
            )
        data = body.get("data")
        size = len(json.dumps(data, default=str))
        if size > MAX_RESULT_CHARS:
            raise ValueError(
                f"{action} returned {size} characters, more than a task can hold. "
                "Narrow it: fewer results, a tighter query, or fetch one item by id."
            )
        return ActionResult(action=action, connection_id=row.id, data=data)

    async def disconnect(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        desk_name: str | None,
        connection_id: str,
    ) -> ConnectedAppRecord:
        row = await connected_apps.get(db, user_id, site_id, connection_id)
        if row is None or (desk_name is not None and row.desk != desk_name):
            raise ConnectionNotFoundError(f"No connection {connection_id} on this website.")
        await db.commit()
        await composio.delete_account(row.account_id)
        await connected_apps.delete(db, row.id)
        log.info("connected_apps.disconnected", desk=row.desk, toolkit=row.toolkit, site_id=site_id)
        return row

    async def sweep(self, db: AsyncSession) -> int:
        stale = await connected_apps.list_stale(
            db, ACTIVE, datetime.now(UTC) - PENDING_RETENTION, SWEEP_BATCH
        )
        owned = [r for r in stale if r.site_id is not None and r.user_id is not None]
        await db.commit()
        remote = {
            a["id"]: a for a in await composio.connected_accounts([r.account_id for r in owned])
        }
        removed = 0
        for row in stale:
            account = remote.get(row.account_id) if row in owned else None
            if account is not None and account.get("status") == ACTIVE:
                await connected_apps.update_state(db, row.id, ACTIVE, self._label(account, row))
                continue
            try:
                await composio.delete_account(row.account_id)
            except ProviderRequestError as exc:
                log.warning("connected_apps.sweep_delete_failed", row_id=row.id, error=str(exc))
                continue
            await connected_apps.delete(db, row.id)
            removed += 1
        return removed

    async def _refreshed(
        self, db: AsyncSession, user_id: str, site_id: str, desk_name: str | None
    ) -> list[ConnectedAppRecord]:
        rows = await connected_apps.list_for_site(db, user_id, site_id, desk_name)
        await db.commit()
        remote = {
            a["id"]: a for a in await composio.connected_accounts([r.account_id for r in rows])
        }
        kept: list[ConnectedAppRecord] = []
        for row in rows:
            account = remote.get(row.account_id)
            if account is None:
                if row.status == ACTIVE:
                    await composio.delete_account(row.account_id)
                    await connected_apps.delete(db, row.id)
                else:
                    kept.append(row)
                continue
            status = str(account.get("status") or row.status)
            label = self._label(account, row)
            if status != row.status or label != row.label:
                await connected_apps.update_state(db, row.id, status, label)
            kept.append(row.model_copy(update={"status": status, "label": label}))
        return kept

    async def _connection(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        desk: Desk,
        app: App,
        connection_id: str | None,
    ) -> ConnectedAppRecord:
        rows = await connected_apps.list_for_site(db, user_id, site_id, desk.name)
        if not any(r.toolkit == app.toolkit and r.status == ACTIVE for r in rows):
            rows = await self._refreshed(db, user_id, site_id, desk.name)
        candidates = [r for r in rows if r.toolkit == app.toolkit and r.status == ACTIVE]
        if connection_id is not None:
            match = next((r for r in candidates if r.id == connection_id), None)
            if match is None:
                raise ValueError(
                    f"{connection_id} is not an active {app.name} connection on this website."
                )
            return match
        if not candidates:
            raise ValueError(
                f"No active {app.name} connection on this website. Offer the user a connect link."
            )
        if len(candidates) > 1:
            ids = ", ".join(f"{r.id} ({r.label or 'unnamed'})" for r in candidates)
            raise ValueError(f"Several {app.name} connections; pass connection_id, one of: {ids}.")
        return candidates[0]

    def _label(self, account: dict[str, Any], row: ConnectedAppRecord) -> str | None:
        return account.get("alias") or account.get("word_id") or row.label

    def _check_arguments(
        self, app: App, action: str, arguments: dict[str, Any], tool: dict[str, Any]
    ) -> None:
        fixed = app.fixed_arguments.get(action, {})
        pinned = {_key(k) for k in fixed}
        overridden = [k for k in arguments if _key(k) in pinned]
        if overridden:
            raise ValueError(f"{', '.join(overridden)} is set by Meelu on {action}; leave it out.")
        properties = (tool.get("input_parameters") or {}).get("properties")
        if isinstance(properties, dict):
            unknown = [k for k in arguments if k not in properties]
            if unknown:
                raise ValueError(
                    f"{action} takes no {', '.join(unknown)}; use the input schema from the apps call."
                )

    async def _link(self, app: App, user: str) -> dict[str, Any]:
        auth_config_id = await self._auth_config(app)
        try:
            return await composio.create_link(auth_config_id, user)
        except ProviderRequestError as exc:
            if exc.status is None or exc.status >= 500:
                raise
            self._auth_configs.pop(app.toolkit, None)
            return await composio.create_link(await self._auth_config(app), user)

    async def _auth_config(self, app: App) -> str:
        cached = self._auth_configs.get(app.toolkit)
        if cached:
            return cached
        async with self._auth_lock:
            cached = self._auth_configs.get(app.toolkit)
            if cached:
                return cached
            found = next(
                (
                    c["id"]
                    for c in await composio.auth_configs(app.toolkit)
                    if c.get("status", "ENABLED") == "ENABLED" and self._fits(app, c)
                ),
                None,
            )
            if found is None:
                found = await composio.create_auth_config(
                    app.toolkit,
                    composio.MANAGED_AUTH if app.auth == "managed" else composio.API_KEY_AUTH,
                )
                log.info("connected_apps.auth_config_created", toolkit=app.toolkit, auth=app.auth)
            self._auth_configs[app.toolkit] = found
            return found

    def _fits(self, app: App, config: dict[str, Any]) -> bool:
        if app.auth == "managed":
            return bool(config.get("is_composio_managed"))
        return config.get("auth_scheme") == "API_KEY"

    async def _tool_schemas(self, slugs: list[str]) -> dict[str, dict[str, Any]]:
        now = time.monotonic()
        missing = [
            s for s in slugs if now - self._schemas.get(s, (float("-inf"), {}))[0] > SCHEMA_TTL_S
        ]
        if missing:
            fetched = {t["slug"]: t for t in await composio.tools(missing)}
            for slug in missing:
                if slug in fetched:
                    self._schemas[slug] = (now, fetched[slug])
                else:
                    log.warning("connected_apps.tool_missing", action=slug)
        return {s: self._schemas[s][1] for s in slugs if s in self._schemas}

    def _action(self, app: App, slug: str, kind: str, tool: dict[str, Any]) -> AppAction:
        fixed = app.fixed_arguments.get(slug, {})
        schema = dict(tool.get("input_parameters") or {})
        if fixed and isinstance(schema.get("properties"), dict):
            schema["properties"] = {k: v for k, v in schema["properties"].items() if k not in fixed}
            schema["required"] = [r for r in schema.get("required", []) if r not in fixed]
        return AppAction(
            action=slug,
            kind=kind,
            description=str(tool.get("description") or tool.get("name") or slug),
            input_schema=schema,
        )


connected_app_service = ConnectedAppService()
