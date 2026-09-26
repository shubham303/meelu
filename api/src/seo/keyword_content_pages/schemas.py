from src.core.schemas import EntityModel


class KeywordContentPageRecord(EntityModel):
    id: str
    keyword_id: str
    page_id: str
    coverage: float
    lexical_hit: bool
