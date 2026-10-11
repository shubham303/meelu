from typing import Literal

from pydantic import Field

from src.core.schemas import EntityModel, JsDateTime, RequestModel

Purpose = Literal["agent", "social_listening", "page_review", "site_summary"]
Tier = Literal["featured", "well_known", "other"]


class LlmModelResponse(EntityModel):
    id: str
    name: str
    provider: str
    tier: Tier
    input_usd_per_million: float
    output_usd_per_million: float
    context_length: int


class LlmPreferenceResponse(EntityModel):
    default_model: str


class LlmPreferenceUpdateRequest(RequestModel):
    default_model: str = Field(min_length=1, max_length=200)


class LlmCallRecord(EntityModel):
    id: str
    user_id: str
    site_id: str | None
    model: str
    purpose: str
    generation_id: str | None
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    cost_micros: int
    charged_micros: int
    status: str
    error: str | None
    duration_ms: int
    created_at: JsDateTime


class LlmCallResponse(EntityModel):
    id: str
    site_id: str | None
    model: str
    purpose: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    cost_micros: int
    charged_micros: int
    status: str
    error: str | None
    duration_ms: int
    created_at: JsDateTime
