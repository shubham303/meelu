from src.app import app
from src.stats.endpoints import router as stats_router

if not any(getattr(route, "path", None) == "/api/v1/stats" for route in app.routes):
    app.include_router(stats_router, prefix="/api/v1")
