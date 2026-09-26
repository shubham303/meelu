from src.core.schemas import EntityModel


class KeywordGscPageRecord(EntityModel):
    id: str
    keyword_id: str
    page_id: str
    position: float | None
    impressions_28d: int
    clicks_28d: int
    impressions_prev_28d: int
    clicks_prev_28d: int
    impressions_ly_28d: int | None
    clicks_ly_28d: int | None
    ctr: float | None
    ctr_gap: float | None
    leader_days_90d: int
    coverage: float | None
    lexical_hit: bool
