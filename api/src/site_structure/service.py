from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.site_structure.links.repository import link_suggestions
from src.site_structure.links.service import link_suggestion_service
from src.site_structure.pillars.repository import pillar_page_suggestions
from src.site_structure.pillars.service import pillar_page_suggestion_service
from src.site_structure.schemas.results import (
    StructureReconcileResult,
    StructureSuggestionDeleteResponse,
    SuggestionKind,
)


class SiteStructureService:
    async def reconcile(self, db: AsyncSession, site_id: str) -> StructureReconcileResult:
        return StructureReconcileResult(
            links=await link_suggestion_service.reconcile(db, site_id),
            pillars=await pillar_page_suggestion_service.reconcile(db, site_id),
        )

    async def delete_suggestion(
        self, db: AsyncSession, site_id: str, suggestion_id: str
    ) -> StructureSuggestionDeleteResponse:
        prefix = suggestion_id.partition("_")[0]
        if prefix == link_suggestions.ID_PREFIX:
            await link_suggestion_service.delete(db, site_id, suggestion_id)
            return StructureSuggestionDeleteResponse(id=suggestion_id, kind=SuggestionKind.LINK)
        if prefix == pillar_page_suggestions.ID_PREFIX:
            await pillar_page_suggestion_service.delete(db, site_id, suggestion_id)
            return StructureSuggestionDeleteResponse(id=suggestion_id, kind=SuggestionKind.PILLAR)
        raise HTTPException(404, f"No link or pillar suggestion {suggestion_id} on this website.")


site_structure_service = SiteStructureService()
