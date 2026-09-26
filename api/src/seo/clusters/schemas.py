from src.core.schemas import EntityModel, JsDateTime


class ClusterRecord(EntityModel):
    id: str
    head_keyword_id: str
    size: int
    volume_sum: int
    difficulty_median: float | None
    owner_page_id: str | None
    owner_coverage: float | None
    site_similarity: float | None
    rebuilt_at: JsDateTime | None
