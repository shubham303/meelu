import contextlib

from fastapi import FastAPI
from starlette.concurrency import run_in_threadpool

import src.agent_scope.registry  # noqa: F401
from src.agent import security
from src.agent.auth import AuthMiddleware
from src.agent.schemas import HealthResponse
from src.agent.server import mcp
from src.agent_plans.service import agent_plan_service
from src.core.database import unit_of_work
from src.core.logging import configure_logging

configure_logging()

mcp_app = mcp.streamable_http_app()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    await run_in_threadpool(security.bootstrap)
    async with unit_of_work() as db:
        await agent_plan_service.sync_builtins(db)
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="meelu-agent", lifespan=lifespan)


@app.get("/health")
async def health() -> HealthResponse:
    return HealthResponse(ok=True)


app.mount("/mcp", AuthMiddleware(mcp_app))
