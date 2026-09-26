from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.seo.generators.schemas import CannibalisationRequest, PageEditsRequest
from src.seo.generators.service import seo_generator_service
from src.seo.page_suggestions.schemas import CreateResult

router = APIRouter()


@router.post("/page-suggestions/propose-edits")
async def propose_page_edits(
    body: PageEditsRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CreateResult:
    return await seo_generator_service.propose_page_edits(db, ctx.user_id, ctx.site_id, body)


@router.post("/page-suggestions/propose-cannibalisation")
async def propose_cannibalisation(
    body: CannibalisationRequest,
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> CreateResult:
    return await seo_generator_service.propose_cannibalisation(db, ctx.user_id, ctx.site_id, body)
