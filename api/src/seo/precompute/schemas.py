from datetime import datetime

from src.core.schemas import EntityModel


class RollupResult(EntityModel):
    pages: int = 0
    keywords: int = 0
    keyword_pages: int = 0
    embedded: int = 0
    rollup_at: datetime | None = None
