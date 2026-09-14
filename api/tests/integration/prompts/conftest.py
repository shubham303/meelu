from src.prompts.endpoints import router as prompts_router

from src.app import app

if not any(getattr(route, "path", None) == "/api/v1/prompts" for route in app.routes):
    app.include_router(prompts_router, prefix="/api/v1")
