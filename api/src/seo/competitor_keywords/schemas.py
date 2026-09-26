from src.core.schemas import EntityModel, JsDateTime


class CompetitorKeywordRecord(EntityModel):
    id: str
    competitor_id: str
    keyword_id: str
    position: int | None
    url: str | None
    etv: float | None
    fetched_at: JsDateTime | None
