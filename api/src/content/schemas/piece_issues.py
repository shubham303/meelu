from typing import Any

from pydantic import field_validator

from src.core.schemas import EntityModel, JsDateTime, RequestModel

ISSUE_STATES = ("open", "fixed", "dismissed")
TOOL_MAX = 40


class ContentPieceIssueInput(RequestModel):
    code: str
    title: str
    detail: str | None = None
    anchor_text: str | None = None
    suggestion: str | None = None

    @field_validator("code", "title", mode="before")
    @classmethod
    def _required(cls, v: Any) -> str:
        value = ("" if v is None else str(v)).strip()
        if not value:
            raise ValueError("Each issue needs a code and a title.")
        return value

    @field_validator("detail", mode="before")
    @classmethod
    def _validate_detail(cls, v: Any) -> str | None:
        return None if v is None else (str(v).strip() or None)

    @field_validator("anchor_text", "suggestion", mode="before")
    @classmethod
    def _validate_optional(cls, v: Any) -> str | None:
        return None if v is None else (str(v) or None)


class ContentPieceIssuesReplaceRequest(RequestModel):
    tool: str
    issues: list[ContentPieceIssueInput]

    @field_validator("tool", mode="before")
    @classmethod
    def _validate_tool(cls, v: Any) -> str:
        tool = ("" if v is None else str(v)).strip()
        if not tool or len(tool) > TOOL_MAX:
            raise ValueError("tool is required.")
        return tool


class ContentPieceIssueUpdateRequest(RequestModel):
    state: str

    @field_validator("state", mode="before")
    @classmethod
    def _validate_state(cls, v: Any) -> str:
        if v not in ISSUE_STATES:
            raise ValueError(f"state must be one of {', '.join(ISSUE_STATES)}.")
        return v


class ContentPieceIssueRecord(EntityModel):
    id: str
    piece_id: str
    tool: str
    code: str
    title: str
    detail: str | None
    anchor_text: str | None
    suggestion: str | None
    state: str
    run_id: str
    created_at: JsDateTime
    updated_at: JsDateTime


class ContentPieceIssuesReplaceResult(EntityModel):
    run_id: str
    tool: str
    issues: list[ContentPieceIssueRecord]


class ContentPieceIssueResponse(EntityModel):
    id: str
    piece_id: str
    tool: str
    code: str
    title: str
    detail: str | None
    anchor_text: str | None
    suggestion: str | None
    state: str
    run_id: str
    created_at: JsDateTime
    updated_at: JsDateTime


class ContentPieceIssueListItemResponse(ContentPieceIssueResponse):
    pass


class ContentPieceIssuesReplaceResponse(EntityModel):
    run_id: str
    tool: str
    issues: list[ContentPieceIssueResponse]
