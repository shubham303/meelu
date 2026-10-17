from typing import Any, Literal

from pydantic import Field, field_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel

CHAT_TITLE_MAX = 80


def _required_text(value: Any, field: str) -> str:
    text = ("" if value is None else str(value)).strip()
    if not text:
        raise ValueError(f"`{field}` is required.")
    return text


def _chat_title(value: Any) -> str:
    text = " ".join(_required_text(value, "title").split())
    return text if len(text) <= CHAT_TITLE_MAX else text[: CHAT_TITLE_MAX - 1].rstrip() + "…"


class AnalyticsChatCreateRequest(RequestModel):
    title: str

    @field_validator("title", mode="before")
    @classmethod
    def _validate_title(cls, v: Any) -> str:
        return _chat_title(v)


class AnalyticsChatUpdateRequest(RequestModel):
    title: str | None = None
    sdk_session_id: str | None = None

    @field_validator("title", mode="before")
    @classmethod
    def _validate_title(cls, v: Any) -> str | None:
        return None if v is None else _chat_title(v)

    def changes(self) -> dict[str, str]:
        return self.model_dump(exclude_none=True)


class AnalyticsChatMessageInput(RequestModel):
    role: Literal["user", "assistant"]
    text: str

    @field_validator("text", mode="before")
    @classmethod
    def _validate_text(cls, v: Any) -> str:
        return _required_text(v, "text")


class AnalyticsChatMessagesCreateRequest(RequestModel):
    messages: list[AnalyticsChatMessageInput] = Field(min_length=1)


class AnalyticsChatRecord(EntityModel):
    id: str
    user_id: str
    site_id: str
    title: str
    sdk_session_id: str | None
    created_at: JsDateTime
    updated_at: JsDateTime


class AnalyticsChatSummaryRecord(EntityModel):
    id: str
    title: str
    updated_at: JsDateTime


class AnalyticsChatMessageRecord(EntityModel):
    id: str
    chat_id: str
    role: str
    text: str
    created_at: JsDateTime


class AnalyticsChatResponse(EntityModel):
    id: str
    site_id: str
    title: str
    sdk_session_id: str | None
    created_at: JsDateTime
    updated_at: JsDateTime


class AnalyticsChatListItemResponse(EntityModel):
    id: str
    title: str
    updated_at: JsDateTime


class AnalyticsChatMessageResponse(EntityModel):
    id: str
    role: str
    text: str
    created_at: JsDateTime


class AnalyticsChatDeleteResponse(EntityModel):
    id: str
    deleted: bool = Field(default=True)
