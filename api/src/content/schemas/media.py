from src.core.schemas import EntityModel, JsDateTime


class PostMediaRecord(EntityModel):
    id: str
    content_type: str
    byte_size: int
    width: int | None
    height: int | None
    original_name: str | None
    created_at: JsDateTime
    updated_at: JsDateTime


class PostMediaContent(EntityModel):
    data: bytes
    content_type: str


class PostMediaResponse(EntityModel):
    id: str
    content_type: str
    byte_size: int
    width: int | None
    height: int | None
    original_name: str | None
    created_at: JsDateTime
    updated_at: JsDateTime
