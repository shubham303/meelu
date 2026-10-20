from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.connected_apps.composio import ComposioNotConfiguredError
from src.connected_apps.schemas import (
    AppConnections,
    ConnectedAppDeleteResponse,
    ConnectLink,
    ConnectRequest,
)
from src.connected_apps.service import ConnectionNotFoundError, connected_app_service
from src.core.database import get_db

router = APIRouter()


@router.get("/connected-apps")
async def list_connected_apps(
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> list[AppConnections]:
    return await connected_app_service.overview(db, ctx.user_id, ctx.site_id)


@router.post("/connected-apps", status_code=201)
async def connect_app(
    body: ConnectRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ConnectLink:
    try:
        connected_app_service.desk(body.desk)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    try:
        return await connected_app_service.connect(
            db, ctx.user_id, ctx.site_id, body.desk, body.app
        )
    except ComposioNotConfiguredError as exc:
        raise HTTPException(503, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.delete("/connected-apps/{connected_app_id}")
async def delete_connected_app(
    connected_app_id: str,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> ConnectedAppDeleteResponse:
    try:
        row = await connected_app_service.disconnect(
            db, ctx.user_id, ctx.site_id, None, connected_app_id
        )
    except ConnectionNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    return ConnectedAppDeleteResponse(id=row.id, deleted=True)
