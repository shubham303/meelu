from enum import StrEnum

from src.core.schemas import EntityModel
from src.site_structure.links.schemas import ReconcileResult as LinkReconcileResult
from src.site_structure.pillars.schemas import ReconcileResult as PillarReconcileResult


class SuggestionKind(StrEnum):
    LINK = "link"
    PILLAR = "pillar"


class StructureReconcileResult(EntityModel):
    links: LinkReconcileResult
    pillars: PillarReconcileResult


class StructureSuggestionDeleteResponse(EntityModel):
    id: str
    kind: SuggestionKind
    deleted: bool = True
