from src.app import app
from src.seo.site_search.endpoints import router

if not any(getattr(r, "path", "") == "/api/v1/site/search-data" for r in app.routes):
    app.include_router(router, prefix="/api/v1")
