from fastapi import APIRouter

from src.site_structure.jobs.endpoints import router as jobs_router
from src.site_structure.links.endpoints import router as links_router
from src.site_structure.pillars.endpoints import router as pillars_router

router = APIRouter(prefix="/site/structure")
router.include_router(jobs_router)
router.include_router(links_router)
router.include_router(pillars_router)
