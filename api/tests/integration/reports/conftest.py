from src.app import app
from src.reports.endpoints import router as reports_router

if not any(getattr(route, "path", None) == "/api/v1/reports" for route in app.routes):
    app.include_router(reports_router, prefix="/api/v1")
