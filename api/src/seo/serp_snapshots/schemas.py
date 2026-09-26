from src.core.schemas import EntityModel, JsDateTime


class SerpSnapshotRecord(EntityModel):
    id: str
    keyword_id: str
    device: str
    fetched_at: JsDateTime
    features: list[str]
