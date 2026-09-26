from typing import Literal

from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.seo.export.service import seo_export_service


@tool(desk="seo")
async def seo_download_data(
    dataset: Literal[
        "keywords", "gsc_pages", "content_pages", "competitor_keywords", "serps", "suggestions"
    ],
) -> dict:
    """Export one SEO dataset as a CSV file and return its path and row count. Analyse the
    file with the analytics engine; the rows never come back inline."""
    ctx = require_site()
    async with unit_of_work() as db:
        path, rows = await seo_export_service.export(db, ctx.site_id, ctx.schema, dataset)
    return {"path": str(path), "rows": rows, "dataset": dataset}
