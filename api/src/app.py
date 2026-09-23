from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from src.agent_plans.endpoints import router as agent_plans_router
from src.agent_scope.endpoints import router as agent_scope_router
from src.analytics.endpoints import router as analytics_router
from src.auth import session_router
from src.content.endpoints import router as content_router
from src.core.envelope import install_envelope
from src.core.logging import RequestLoggingMiddleware, configure_logging
from src.crawl_jobs.endpoints import router as crawl_jobs_router
from src.credits.endpoints import router as credits_router
from src.credits.service import InsufficientCreditsError
from src.keys.endpoints import router as keys_router
from src.leads.endpoints import router as leads_router
from src.notes.endpoints import router as notes_router
from src.profile.endpoints import router as profile_router
from src.providers.endpoints import router as providers_router
from src.providers.errors import ProviderError
from src.render_jobs.endpoints import router as render_jobs_router
from src.seo.endpoints import router as seo_router
from src.settings import settings
from src.site_page_llm_extraction.endpoints import router as site_page_llm_extraction_router
from src.site_pages.endpoints import router as site_pages_router
from src.site_search.endpoints import router as site_search_router
from src.site_structure.endpoints import router as site_structure_router
from src.site_traffic.endpoints import router as site_traffic_router
from src.sites.endpoints import router as sites_router
from src.social_listening.endpoints import router as social_listening_router
from src.stats.endpoints import router as stats_router
from src.technical_seo.endpoints import router as technical_seo_router

configure_logging()

app = FastAPI(title="meelu-api")

install_envelope(app)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(session_router, prefix="/api/auth")

for desk in (
    keys_router,
    profile_router,
    sites_router,
    stats_router,
    site_page_llm_extraction_router,
    site_pages_router,
    site_structure_router,
    seo_router,
    crawl_jobs_router,
    render_jobs_router,
    site_search_router,
    site_traffic_router,
    technical_seo_router,
    content_router,
    analytics_router,
    notes_router,
    social_listening_router,
    leads_router,
    agent_scope_router,
    agent_plans_router,
    credits_router,
    providers_router,
):
    app.include_router(desk, prefix="/api/v1")


@app.exception_handler(ProviderError)
async def _provider_error(request, exc: ProviderError):
    return JSONResponse({"error": exc.payload()}, status_code=exc.http_status)


@app.exception_handler(InsufficientCreditsError)
async def _credits_error(request, exc: InsufficientCreditsError):
    return JSONResponse(
        {"error": {"code": exc.code, "message": str(exc), "balanceMicros": exc.balance_micros}},
        status_code=402,
    )


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": True}
