from typing import Any, Literal

from src.core.schemas import EntityModel, JsDateTime, RequestModel


class ConnectedAppRecord(EntityModel):
    id: str
    user_id: str | None
    site_id: str | None
    desk: str
    toolkit: str
    account_id: str
    status: str
    label: str | None
    created_at: JsDateTime
    updated_at: JsDateTime


class ConnectedAppResponse(EntityModel):
    id: str
    desk: str
    toolkit: str
    status: str
    label: str | None
    created_at: JsDateTime
    updated_at: JsDateTime


class ConnectedAppDeleteResponse(EntityModel):
    id: str
    deleted: bool


class Connection(EntityModel):
    connection_id: str
    status: str
    label: str | None


class AppAction(EntityModel):
    action: str
    kind: Literal["read", "write"]
    description: str
    input_schema: dict[str, Any]


class AppStatus(EntityModel):
    app: str
    name: str
    connections: list[Connection]
    actions: list[AppAction]


class AppConnections(EntityModel):
    desk: str
    app: str
    name: str
    connections: list[Connection]


class ConnectRequest(RequestModel):
    desk: str
    app: str


class ConnectLink(EntityModel):
    app: str
    connection_id: str
    url: str
    expires_at: str | None


class ActionResult(EntityModel):
    action: str
    connection_id: str
    data: Any
