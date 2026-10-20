import asyncio
import json
import math
import time
import weakref
from collections.abc import AsyncIterator, Coroutine
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi import HTTPException
from fastapi.responses import JSONResponse, Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import unit_of_work
from src.core.logging import get_logger
from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.credits.limiter import PaidCallsBusyError, paid_calls
from src.credits.service import InsufficientCreditsError, credit_service
from src.llm import request as llm_request
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

log = get_logger()

DEFAULT_ANTHROPIC_VERSION = "2023-06-01"
STREAM_HEADERS = {"cache-control": "no-cache, no-transform", "x-accel-buffering": "no"}
GENERATION_POLL_DELAYS = (1.0, 3.0, 10.0, 30.0)
TOO_LONG = "The answer ran past the longest time Meelu allows for one model call."


def error_body(kind: str, message: str) -> dict[str, Any]:
    return {"type": "error", "error": {"type": kind, "message": message}}


def anthropic_error(status: int, kind: str, message: str) -> JSONResponse:
    return JSONResponse(error_body(kind, message), status_code=status)


def error_frame(kind: str, message: str) -> bytes:
    return f"event: error\ndata: {json.dumps(error_body(kind, message))}\n\n".encode()


@dataclass
class CallContext:
    user_id: str
    site_id: str | None
    purpose: Purpose
    model: LlmModelResponse
    started: float
    slot_open: bool = True


class LlmService:
    def __init__(self) -> None:
        self._settling: set[asyncio.Task] = set()

    def _spawn(self, work: Coroutine[Any, Any, None]) -> asyncio.Task:
        task = asyncio.create_task(work)
        self._settling.add(task)
        task.add_done_callback(self._settling.discard)
        return task

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
            log.error("llm.catalog.unavailable", error=str(exc))
            return anthropic_error(503, "api_error", "The model list is unavailable. Try again.")
        if model is None:
            return anthropic_error(
                400, "invalid_request_error", f"Meelu does not offer the model {model_id}."
            )
        requested = llm_request.max_output_tokens(body)
        if requested is None:
            return anthropic_error(
                400, "invalid_request_error", "max_tokens must be a positive integer."
            )
        max_tokens = min(requested, settings.llm_max_output_tokens)
        await db.commit()
        try:
            await paid_calls.acquire(user_id)
        except PaidCallsBusyError as exc:
            return anthropic_error(429, "rate_limit_error", str(exc))
        call = CallContext(user_id, site_id, purpose, model, time.monotonic())
        try:
            async with unit_of_work() as ledger:
                await credit_service.require_balance(ledger, user_id)
            return await self._send(call, headers, body, max_tokens)
        except InsufficientCreditsError as exc:
            self._free_slot(call)
            return anthropic_error(402, "billing_error", str(exc))
        except BaseException:
            self._free_slot(call)
            raise

    def _free_slot(self, call: CallContext) -> None:
        if call.slot_open:
            call.slot_open = False
            paid_calls.release(call.user_id)

    async def _send(
        self, call: CallContext, headers: dict[str, str], body: dict[str, Any], max_tokens: int
    ) -> Response:
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
            json=llm_request.forwarded(body, call.model.id, max_tokens),
            timeout=httpx.Timeout(settings.llm_stream_timeout_seconds, connect=15.0),
        )
        if body.get("stream"):
            return await self._stream(call, request)
        return await self._single(call, request)

    async def _single(self, call: CallContext, request: httpx.Request) -> Response:
        try:
            response = await client().send(request)
        except httpx.HTTPError as exc:
            self._free_slot(call)
            await self._record(call, Usage(error=str(exc)), "error")
            return anthropic_error(502, "api_error", "The model provider is unreachable.")
        self._free_slot(call)
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
        self._spawn(self._record(call, usage, status))
        return Response(
            response.content,
            status_code=response.status_code,
            media_type=response.headers.get("content-type", "application/json"),
        )

    async def _stream(self, call: CallContext, request: httpx.Request) -> Response:
        try:
            response = await client().send(request, stream=True)
        except httpx.HTTPError as exc:
            self._free_slot(call)
            await self._record(call, Usage(error=str(exc)), "error")
            return anthropic_error(502, "api_error", "The model provider is unreachable.")
        if response.status_code >= 400:
            raw = await response.aread()
            await response.aclose()
            self._free_slot(call)
            await self._record(call, Usage(error=raw.decode("utf-8", "replace")[:2000]), "error")
            return Response(
                raw,
                status_code=response.status_code,
                media_type=response.headers.get("content-type", "application/json"),
            )
        relay = self._relay(call, response)
        weakref.finalize(relay, self._free_slot, call)
        return StreamingResponse(
            relay,
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
                if time.monotonic() - call.started > settings.llm_stream_max_seconds:
                    status = "error"
                    meter.usage.error = TOO_LONG
                    yield error_frame("api_error", TOO_LONG)
                    return
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
            self._spawn(self._finish(call, response, meter.usage, status))

    async def _finish(
        self, call: CallContext, response: httpx.Response, usage: Usage, status: str
    ) -> None:
        await response.aclose()
        self._free_slot(call)
        await self._record(call, usage, status)

    async def _cost(self, call: CallContext, usage: Usage) -> int:
        if usage.cost_micros is not None:
            return usage.cost_micros
        billed = await self._generation_cost(usage.generation_id) if usage.generation_id else None
        if billed is not None:
            return billed
        if usage.generation_id or usage.input_tokens or usage.output_tokens:
            log.error(
                "llm.call.cost_missing",
                user_id=call.user_id,
                model=call.model.id,
                generation_id=usage.generation_id,
            )
        return 0

    async def _generation_cost(self, generation_id: str) -> int | None:
        for delay in GENERATION_POLL_DELAYS:
            await asyncio.sleep(delay)
            try:
                response = await client().get(
                    f"{settings.openrouter_base_url}/v1/generation",
                    params={"id": generation_id},
                    headers={"authorization": f"Bearer {settings.openrouter_api_key}"},
                    timeout=15.0,
                )
                data = response.json().get("data") if response.status_code == 200 else None
            except (httpx.HTTPError, ValueError, AttributeError):
                continue
            cost = data.get("total_cost") if isinstance(data, dict) else None
            if isinstance(cost, (int, float)) and not isinstance(cost, bool):
                return math.ceil(cost * 1_000_000)
        return None

    async def _record(self, call: CallContext, usage: Usage, status: str) -> None:
        try:
            cost = await self._cost(call, usage)
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
                "llm.call.not_recorded",
                user_id=call.user_id,
                model=call.model.id,
                error=str(exc),
            )


llm_service = LlmService()
