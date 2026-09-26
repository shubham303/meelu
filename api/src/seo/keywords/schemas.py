from src.core.schemas import EntityModel, JsDateTime


class KeywordRecord(EntityModel):
    id: str
    keyword: str
    volume: int | None
    difficulty: int | None
    cpc: float | None
    intent: str | None
    facts_fetched_at: JsDateTime | None
    first_source: str
    seed_keyword_id: str | None
    cluster_id: str | None
    branded: bool
    our_position: int | None
    our_url: str | None
    impressions_28d: int
    clicks_28d: int
    impressions_prev_28d: int
    clicks_prev_28d: int
    impressions_ly_28d: int | None
    clicks_ly_28d: int | None
    created_at: JsDateTime


class KeywordFilter(EntityModel):
    source: str | None = None
    cluster_id: str | None = None
    branded: bool | None = None
    search: str | None = None
    has_facts: bool | None = None


class KeywordVector(EntityModel):
    id: str
    keyword: str
    embedding: list[float]
