from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.agent.context import tenant_names
from src.auth import AuthContext, require_site
from src.core.database import get_db
from src.seo.export.service import seo_export_service

router = APIRouter()


@router.get("/export")
async def export_dataset(
    dataset: str = Query(...),
    db: AsyncSession = Depends(get_db),
    ctx: AuthContext = Depends(require_site),
) -> dict:
    _, schema = tenant_names(ctx.user_id)
    path, rows = await seo_export_service.export(db, ctx.site_id, schema, dataset)
    return {"path": str(path), "rows": rows, "dataset": dataset}
