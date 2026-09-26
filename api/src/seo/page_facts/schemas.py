from src.core.schemas import EntityModel, JsDateTime


class PageFactsRecord(EntityModel):
    id: str
    page_id: str
    url: str
    status: int | None
    redirect_to: str | None
    page_type: str | None
    lang: str | None
    title: str | None
    h1: str | None
    headings: list[str]
    meta_description: str | None
    title_pixels: int | None
    word_count: int | None
    inlinks: int
    link_score: float | None
    published_at: JsDateTime | None
    first_seen_at: JsDateTime | None
    content_hash: str | None
    indexable: bool
    live: bool
    is_home: bool
    impressions_28d: int
    clicks_28d: int
    impressions_ly_28d: int | None
    clicks_ly_28d: int | None
