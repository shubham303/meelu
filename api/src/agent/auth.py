from fastapi import HTTPException
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from src.agent.context import AgentContext, reset_context, set_context
from src.agent.security import ensure_user
from src.core.database import unit_of_work
from src.keys.repository import find_user_by_api_key
from src.sites import repository as sites_repository


async def resolve(api_key: str, site_header: str | None) -> AgentContext:
    async with unit_of_work() as db:
        owner = await find_user_by_api_key(db, api_key)
        if owner is None:
            raise HTTPException(401, "Invalid API key.")
        user_id = owner.user_id

        site_id = site_domain = None
        if site_header:
            site = await sites_repository.get_site(db, user_id, site_header)
            if site is None:
                raise HTTPException(404, f"No website {site_header!r} in this workspace.")
            site_id, site_domain = site.id, site.domain
        else:
            only = await sites_repository.default_site_id(db, user_id)
            if only:
                site = await sites_repository.get_site(db, user_id, only)
                site_id, site_domain = site.id, site.domain

    role, schema = await run_in_threadpool(ensure_user, user_id)
    return AgentContext(
        user_id=user_id,
        site_id=site_id,
        site_domain=site_domain,
        role=role,
        schema=schema,
        api_key=api_key,
    )


class AuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        api_key = headers.get("x-api-key")
        if not api_key:
            await JSONResponse({"error": "x-api-key header required"}, status_code=401)(
                scope, receive, send
            )
            return

        try:
            ctx = await resolve(api_key, headers.get("x-meelu-site"))
        except HTTPException as exc:
            await JSONResponse({"error": exc.detail}, status_code=exc.status_code)(
                scope, receive, send
            )
            return

        token = set_context(ctx)
        try:
            await self.app(scope, receive, send)
        finally:
            reset_context(token)
