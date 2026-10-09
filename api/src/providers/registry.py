import hashlib
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import unit_of_work
from src.credits.service import InsufficientCreditsError, credit_service
from src.providers.errors import (
    NoProviderError,
    NotSupportedError,
    ProviderRequestError,
    SpendCeilingError,
)
from src.providers.models.provider_cache import ProviderCache
from src.providers.repository import provider_caches, provider_calls
from src.providers.schemas import AdapterStatus, DomainStatus


@dataclass
class SpendMeter:
    ceiling_micros: int = 0
    calls: int = 0
    micros: int = 0
    cache_hits: int = 0

    def check(self) -> None:
        if self.ceiling_micros and self.micros >= self.ceiling_micros:
            raise SpendCeilingError(self.micros, self.ceiling_micros)


@dataclass(frozen=True)
class Caller:
    user_id: str
    site_id: str | None = None
    spend: SpendMeter | None = None


@dataclass(frozen=True)
class VendorResponse:
    data: Any
    cost_micros: int = 0


class ProviderAdapter:
    id: str = ""
    name: str = ""
    capabilities: frozenset[str] = frozenset()
    charges: bool = True

    def configured(self) -> bool:
        return True

    def unsupported(self, capability: str) -> NotSupportedError:
        return NotSupportedError(self.id, capability)


def cache_key(domain: str, capability: str, request: dict[str, Any]) -> str:
    body = json.dumps([domain, capability, request], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode()).hexdigest()


class ProviderFacade:
    domain: str = ""
    label: str = ""

    def __init__(self, adapters: list[ProviderAdapter]):
        self.adapters = adapters

    def available(self) -> list[ProviderAdapter]:
        return [a for a in self.adapters if a.configured()]

    def adapters_for(self, capability: str) -> list[ProviderAdapter]:
        return [a for a in self.available() if capability in a.capabilities]

    def supports(self, capability: str) -> bool:
        return bool(self.adapters_for(capability))

    def status(self) -> DomainStatus:
        return DomainStatus(
            domain=self.domain,
            label=self.label,
            adapters=[
                AdapterStatus(
                    id=a.id,
                    name=a.name,
                    configured=a.configured(),
                    capabilities=sorted(a.capabilities),
                )
                for a in self.adapters
            ],
        )

    async def fetch(
        self,
        db: AsyncSession,
        caller: Caller,
        capability: str,
        request: Callable[[Any], dict[str, Any]],
        call: Callable[[Any], Awaitable[VendorResponse]],
        ttl: timedelta | None,
    ) -> Any:
        started = time.monotonic()
        if ttl is not None:
            hit = await self._cached(db, capability, request)
            if hit is not None:
                await self._log(
                    db,
                    caller,
                    capability,
                    hit.provider,
                    hit.cache_key,
                    True,
                    0,
                    0,
                    "ok",
                    None,
                    started,
                )
                if caller.spend is not None:
                    caller.spend.cache_hits += 1
                return hit.response

        candidates = self.adapters_for(capability)
        if not candidates:
            raise NoProviderError(self.domain, self.label, capability)

        last: ProviderRequestError | None = None
        for adapter in candidates:
            query = request(adapter)
            key = cache_key(self.domain, capability, query)
            if adapter.charges:
                if caller.spend is not None:
                    caller.spend.check()
                try:
                    await credit_service.require_balance(db, caller.user_id)
                except InsufficientCreditsError as exc:
                    await self._log_failure(caller, capability, adapter.id, key, str(exc), started)
                    raise
            try:
                result = await call(adapter)
            except ProviderRequestError as exc:
                last = exc
                continue
            if ttl is not None:
                await provider_caches.upsert(
                    db,
                    cache_key=key,
                    domain=self.domain,
                    capability=capability,
                    provider=adapter.id,
                    request=query,
                    response=result.data,
                    vendor_cost_micros=result.cost_micros,
                    ttl=ttl,
                )
            row = await self._log(
                db,
                caller,
                capability,
                adapter.id,
                key,
                False,
                result.cost_micros,
                0,
                "ok",
                None,
                started,
            )
            charged = (
                await credit_service.charge_vendor_call(
                    db, caller.user_id, self.domain, capability, result.cost_micros, row.id
                )
                if adapter.charges
                else 0
            )
            await provider_calls.set_charged_micros(db, row, charged)
            if caller.spend is not None:
                caller.spend.calls += 1
                caller.spend.micros += int(charged or 0)
            return result.data

        assert last is not None
        await self._log_failure(caller, capability, last.provider_id, key, str(last), started)
        raise last

    async def _cached(
        self, db: AsyncSession, capability: str, request: Callable[[Any], dict[str, Any]]
    ) -> ProviderCache | None:
        keys = dict.fromkeys(
            cache_key(self.domain, capability, request(adapter))
            for adapter in self.adapters
            if capability in adapter.capabilities
        )
        for key in keys:
            hit = await provider_caches.get_fresh(db, key)
            if hit is not None:
                return hit
        return None

    async def _log_failure(self, caller, capability, provider, key, error, started) -> None:
        async with unit_of_work() as db:
            await self._log(
                db, caller, capability, provider, key, False, 0, 0, "error", error, started
            )

    async def _log(
        self,
        db: AsyncSession,
        caller: Caller,
        capability: str,
        provider: str | None,
        key: str,
        hit: bool,
        cost: int,
        charged: int,
        status: str,
        error: str | None,
        started: float,
    ):
        return await provider_calls.create(
            db,
            user_id=caller.user_id,
            site_id=caller.site_id,
            domain=self.domain,
            capability=capability,
            provider=provider,
            cache_key=key,
            cache_hit=hit,
            vendor_cost_micros=cost,
            charged_micros=charged,
            status=status,
            error=error,
            duration_ms=int((time.monotonic() - started) * 1000),
        )
