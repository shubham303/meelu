from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.seo.precompute.schemas import RollupResult
from src.seo.precompute.service import seo_precompute_service
from src.seo.state.schemas import SiteStateRecord

router = APIRouter()


@router.post("/rollup")
async def run_rollup(
    db: AsyncSession = Depends(get_db), ctx: AuthContext = Depends(require_site)
) -> RollupResult:
    return await seo_precompute_service.run_rollup(db, ctx.user_id, ctx.site_id)


@router.post("/precompute")
async def request_precompute(
    db: AsyncSession = Depends(get_db), ctx: AuthContext = Depends(require_site)
) -> SiteStateRecord:
    return await seo_precompute_service.request_precompute(db, ctx.user_id, ctx.site_id)
