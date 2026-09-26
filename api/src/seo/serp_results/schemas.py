from src.core.schemas import EntityModel


class SerpResultRecord(EntityModel):
    id: str
    snapshot_id: str
    rank: int
    domain: str
    url: str
    title: str | None
    description: str | None
    is_ours: bool
