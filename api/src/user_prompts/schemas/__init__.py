from typing import Any, Literal

from pydantic import Field, field_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel

USER_PROMPT_SURFACES = ("seo", "structure")
MAX_LABEL_CHARS = 80
MAX_PROMPT_CHARS = 8000

UserPromptSurface = Literal["seo", "structure"]


def _surface(value: Any) -> str:
    surface = str(value)
    if surface not in USER_PROMPT_SURFACES:
        raise ValueError(
            f'Invalid surface "{surface}". Allowed values: {", ".join(USER_PROMPT_SURFACES)}.'
        )
    return surface


def _text(value: Any, field: str, limit: int) -> str:
    text = ("" if value is None else str(value)).strip()
    if not text:
        raise ValueError(f"A saved prompt needs a {field}.")
    if len(text) > limit:
        raise ValueError(f"That {field} is {len(text)} characters — keep it under {limit}.")
    return text


class UserPromptCreateRequest(RequestModel):
    surface: str
    label: str
    prompt: str

    @field_validator("surface", mode="before")
    @classmethod
    def _validate_surface(cls, v: Any) -> str:
        return _surface(v)

    @field_validator("label", mode="before")
    @classmethod
    def _validate_label(cls, v: Any) -> str:
        return _text(v, "name", MAX_LABEL_CHARS)

    @field_validator("prompt", mode="before")
    @classmethod
    def _validate_prompt(cls, v: Any) -> str:
        return _text(v, "prompt", MAX_PROMPT_CHARS)


class UserPromptUpdateRequest(RequestModel):
    label: str | None = None
    prompt: str | None = None

    @field_validator("label", mode="before")
    @classmethod
    def _validate_label(cls, v: Any) -> str | None:
        return None if v is None else _text(v, "name", MAX_LABEL_CHARS)

    @field_validator("prompt", mode="before")
    @classmethod
    def _validate_prompt(cls, v: Any) -> str | None:
        return None if v is None else _text(v, "prompt", MAX_PROMPT_CHARS)


class UserPromptListFilters(RequestModel):
    surface: str | None = None
    contains: str | None = None

    @field_validator("surface", mode="before")
    @classmethod
    def _validate_surface(cls, v: Any) -> str | None:
        return None if v is None else _surface(v)


class UserPromptNew(EntityModel):
    user_id: str
    site_id: str
    surface: str
    label: str
    prompt: str


class UserPromptChanges(EntityModel):
    label: str | None = None
    prompt: str | None = None

    def is_empty(self) -> bool:
        return self.label is None and self.prompt is None


class UserPromptLabelKey(EntityModel):
    site_id: str
    surface: str
    label: str


class UserPromptRecord(EntityModel):
    id: str
    site_id: str
    surface: str
    label: str
    prompt: str
    created_at: JsDateTime
    updated_at: JsDateTime


class UserPromptResponse(EntityModel):
    id: str
    site_id: str
    surface: str
    label: str
    prompt: str
    created_at: JsDateTime
    updated_at: JsDateTime


class UserPromptListItemResponse(UserPromptResponse):
    pass


class UserPromptDeleteResponse(EntityModel):
    id: str
    deleted: bool = Field(default=True)
