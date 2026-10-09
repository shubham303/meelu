import contextlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from src.agent_plans.endpoints import router as agent_plans_router
from src.agent_scope.endpoints import router as agent_scope_router
from src.analytics.endpoints import router as analytics_router
from src.auth import session_router
from src.content.endpoints import router as content_router
from src.core import scheduler
from src.core.envelope import install_envelope
from src.core.logging import RequestLoggingMiddleware, configure_logging
from src.crawl_jobs.endpoints import router as crawl_jobs_router
from src.credits import cron as credits_cron
from src.credits.endpoints import router as credits_router
from src.credits.service import InsufficientCreditsError, SiteDisabledError
from src.keys.endpoints import router as keys_router
from src.notes.endpoints import router as notes_router
from src.payments.endpoints import router as payments_router
from src.profile.endpoints import router as profile_router
from src.providers.endpoints import router as providers_router
from src.providers.errors import ProviderError
from src.render_jobs.endpoints import router as render_jobs_router
from src.scratchpad import cron as scratchpad_cron
from src.scratchpad.endpoints import router as scratchpad_router
from src.seo.keyword_clusters.endpoints import router as keyword_clusters_router
from src.seo.keyword_tracking.endpoints import router as keyword_tracking_router
from src.seo.site_search.endpoints import router as site_search_router
from src.seo.site_seo.endpoints import router as site_seo_router
from src.seo.site_traffic.endpoints import router as site_traffic_router
from src.settings import settings
from src.site_pages.endpoints import router as site_pages_router
from src.site_structure import cron as site_structure_cron
from src.site_structure.endpoints import router as site_structure_router
from src.sites.endpoints import router as sites_router
from src.social_listening.endpoints import router as social_listening_router
from src.stats.endpoints import router as stats_router
from src.technical_seo.endpoints import router as technical_seo_router

configure_logging()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    credits_cron.register(scheduler.scheduler)
    site_structure_cron.register(scheduler.scheduler)
    scratchpad_cron.register(scheduler.scheduler)
    async with scheduler.running():
        yield


app = FastAPI(title="meelu-api", lifespan=lifespan)

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
    site_pages_router,
    site_structure_router,
    crawl_jobs_router,
    render_jobs_router,
    site_search_router,
    site_seo_router,
    keyword_clusters_router,
    keyword_tracking_router,
    site_traffic_router,
    technical_seo_router,
    content_router,
    analytics_router,
    notes_router,
    social_listening_router,
    agent_scope_router,
    agent_plans_router,
    credits_router,
    payments_router,
    providers_router,
    scratchpad_router,
):
    app.include_router(desk, prefix="/api/v1")


@app.exception_handler(ProviderError)
async def _provider_error(request, exc: ProviderError):
    return JSONResponse({"error": exc.payload()}, status_code=exc.http_status)


@app.exception_handler(InsufficientCreditsError)
async def _credits_error(request, exc: InsufficientCreditsError):
    return JSONResponse(
        {
            "error": {
                "code": exc.code,
                "message": str(exc),
                "balanceMicros": exc.balance_micros,
                "minimumMicros": exc.floor_micros,
            }
        },
        status_code=402,
    )


@app.exception_handler(SiteDisabledError)
async def _site_disabled(request, exc: SiteDisabledError):
    return JSONResponse(
        {"error": {"code": exc.code, "message": str(exc), "siteId": exc.site_id}},
        status_code=402,
    )


@app.get("/healthz")
async def healthz() -> dict[str, bool]:
    return {"ok": True}
