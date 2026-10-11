import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import HTTPException
from fastapi.responses import JSONResponse, Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import unit_of_work
from src.core.logging import get_logger
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.credits.service import InsufficientCreditsError, credit_service
from src.llm.catalog import model_catalog
from src.llm.repositories.calls import llm_calls
from src.llm.repositories.preferences import llm_preferences
from src.llm.schemas import (
    LlmCallResponse,
    LlmModelResponse,
    LlmPreferenceResponse,
    LlmPreferenceUpdateRequest,
    Purpose,
)
from src.llm.stream import SseMeter, Usage
from src.providers.errors import ProviderRequestError
from src.providers.http import client
from src.settings import settings

log = get_logger("llm")

DEFAULT_ANTHROPIC_VERSION = "2023-06-01"
STREAM_HEADERS = {"cache-control": "no-cache, no-transform", "x-accel-buffering": "no"}


def anthropic_error(status: int, kind: str, message: str) -> JSONResponse:
    return JSONResponse(
        {"type": "error", "error": {"type": kind, "message": message}}, status_code=status
    )


@dataclass(frozen=True)
class CallContext:
    user_id: str
    site_id: str | None
    purpose: Purpose
    model: LlmModelResponse
    started: float


class LlmService:
    async def models(self) -> list[LlmModelResponse]:
        return await model_catalog.models()

    async def preference(self, db: AsyncSession, user_id: str) -> LlmPreferenceResponse:
        chosen = await llm_preferences.get(db, user_id)
        return LlmPreferenceResponse(default_model=chosen or settings.llm_default_model)

    async def set_preference(
        self, db: AsyncSession, user_id: str, body: LlmPreferenceUpdateRequest
    ) -> LlmPreferenceResponse:
        if await model_catalog.get(body.default_model) is None:
            raise HTTPException(400, f"Meelu does not offer the model {body.default_model}.")
        await llm_preferences.upsert(db, user_id, body.default_model)
        return LlmPreferenceResponse(default_model=body.default_model)

    async def list_calls(
        self, db: AsyncSession, user_id: str, model: str | None, paging: PaginationParams
    ) -> PaginatedApiResponse[LlmCallResponse]:
        page = await llm_calls.page(db, user_id, model, paging)
        return PaginatedApiResponse[LlmCallResponse](
            data=[LlmCallResponse.model_validate(r) for r in page.data],
            pagination=page.pagination,
        )

    async def messages(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str | None,
        purpose: Purpose,
        headers: dict[str, str],
        body: dict[str, Any],
    ) -> Response:
        model_id = body.get("model") or (await self.preference(db, user_id)).default_model
        if not isinstance(model_id, str):
            return anthropic_error(400, "invalid_request_error", "model must be a string.")
        try:
            model = await model_catalog.get(model_id)
        except ProviderRequestError as exc:
            log.error("llm_catalog_unavailable", error=str(exc))
            return anthropic_error(503, "api_error", "The model list is unavailable. Try again.")
        if model is None:
            return anthropic_error(
                400, "invalid_request_error", f"Meelu does not offer the model {model_id}."
            )
        try:
            await credit_service.require_balance(db, user_id)
        except InsufficientCreditsError as exc:
            return anthropic_error(402, "billing_error", str(exc))

        call = CallContext(user_id, site_id, purpose, model, time.monotonic())
        upstream = {
            "authorization": f"Bearer {settings.openrouter_api_key}",
            "content-type": "application/json",
            "anthropic-version": headers.get("anthropic-version") or DEFAULT_ANTHROPIC_VERSION,
            **(
                {"anthropic-beta": headers["anthropic-beta"]}
                if headers.get("anthropic-beta")
                else {}
            ),
        }
        request = client().build_request(
            "POST",
            f"{settings.openrouter_base_url}/v1/messages",
            headers=upstream,
            json={**body, "model": model.id},
            timeout=httpx.Timeout(settings.llm_stream_timeout_seconds, connect=15.0),
        )
        if body.get("stream"):
            return await self._stream(call, request)
        return await self._single(call, request)

    async def _single(self, call: CallContext, request: httpx.Request) -> Response:
        try:
            response = await client().send(request)
        except httpx.HTTPError as exc:
            await self._record(call, Usage(error=str(exc)), "error")
            return anthropic_error(502, "api_error", "The model provider is unreachable.")
        usage = Usage()
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if response.status_code < 400 and isinstance(payload, dict):
            usage.absorb_message(payload)
            status = "ok"
        else:
            usage.error = response.text[:2000]
            status = "error"
        await self._record(call, usage, status)
        return Response(
            response.content,
            status_code=response.status_code,
            media_type=response.headers.get("content-type", "application/json"),
        )

    async def _stream(self, call: CallContext, request: httpx.Request) -> Response:
        try:
            response = await client().send(request, stream=True)
        except httpx.HTTPError as exc:
            await self._record(call, Usage(error=str(exc)), "error")
            return anthropic_error(502, "api_error", "The model provider is unreachable.")
        if response.status_code >= 400:
            raw = await response.aread()
            await response.aclose()
            await self._record(call, Usage(error=raw.decode("utf-8", "replace")[:2000]), "error")
            return Response(
                raw,
                status_code=response.status_code,
                media_type=response.headers.get("content-type", "application/json"),
            )
        return StreamingResponse(
            self._relay(call, response),
            media_type="text/event-stream",
            headers=STREAM_HEADERS,
        )

    async def _relay(self, call: CallContext, response: httpx.Response) -> AsyncIterator[bytes]:
        meter = SseMeter()
        status = "cancelled"
        try:
            async for chunk in response.aiter_bytes():
                out = meter.feed(chunk)
                if out:
                    yield out
            tail = meter.flush()
            if tail:
                yield tail
            if meter.usage.error:
                status = "error"
            elif meter.usage.stopped:
                status = "ok"
            else:
                status = "error"
                meter.usage.error = "The stream ended before the message did."
        except httpx.HTTPError as exc:
            status = "error"
            meter.usage.error = str(exc)
        finally:
            await asyncio.shield(self._finish(call, response, meter.usage, status))

    async def _finish(
        self, call: CallContext, response: httpx.Response, usage: Usage, status: str
    ) -> None:
        await response.aclose()
        await self._record(call, usage, status)

    async def _record(self, call: CallContext, usage: Usage, status: str) -> None:
        cost = (
            usage.cost_micros
            if usage.cost_micros is not None
            else usage.estimate_micros(
                call.model.input_usd_per_million, call.model.output_usd_per_million
            )
        )
        try:
            async with unit_of_work() as db:
                row = await llm_calls.create(
                    db,
                    call.user_id,
                    {
                        "site_id": call.site_id,
                        "model": call.model.id,
                        "purpose": call.purpose,
                        "generation_id": usage.generation_id,
                        "input_tokens": usage.input_tokens,
                        "output_tokens": usage.output_tokens,
                        "cache_read_tokens": usage.cache_read_tokens,
                        "cache_write_tokens": usage.cache_write_tokens,
                        "cost_micros": cost,
                        "status": status,
                        "error": usage.error,
                        "duration_ms": int((time.monotonic() - call.started) * 1000),
                    },
                )
                charged = await credit_service.charge_vendor_call(
                    db, call.user_id, "llm", call.model.id, cost, None
                )
                await llm_calls.set_charged(db, row.id, charged)
        except Exception as exc:
            log.error(
                "llm_call_not_recorded",
                user_id=call.user_id,
                model=call.model.id,
                cost_micros=cost,
                error=str(exc),
            )


llm_service = LlmService()
