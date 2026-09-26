from typing import Any, Literal

from src.agent.context import require_site
from src.agent.server import tool
from src.core.database import unit_of_work
from src.seo.page_suggestions.schemas import CreateResult, SavePageSuggestionRequest
from src.seo.page_suggestions.service import seo_page_suggestion_service


@tool(writes=True, desk="seo")
async def save_page_suggestion(
    job_id: str,
    action: Literal["add", "edit", "delete"],
    topic_key: str,
    suggestion: str,
    page_id: str | None = None,
    merge_into_page_id: str | None = None,
    keyword_ids: list[str] | None = None,
    terms: list[str] | None = None,
    evidence: dict[str, Any] | None = None,
) -> CreateResult:
    """Save one page suggestion you wrote yourself; it lands ready for the user. topic_key is
    the head keyword it is about; a delete needs merge_into_page_id and obeys the same
    protections as the generators."""
    ctx = require_site()
    body = SavePageSuggestionRequest(
        job_id=job_id,
        action=action,
        topic_key=topic_key,
        suggestion=suggestion,
        page_id=page_id,
        merge_into_page_id=merge_into_page_id,
        keyword_ids=keyword_ids or [],
        terms=terms or [],
        evidence=evidence or {},
    )
    async with unit_of_work() as db:
        return await seo_page_suggestion_service.save(db, ctx.user_id, ctx.site_id, body)
