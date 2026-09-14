from src.app import app
from src.site_traffic.endpoints import router

if not any(getattr(r, "path", "") == "/api/v1/site/traffic" for r in app.routes):
    app.include_router(router, prefix="/api/v1")
