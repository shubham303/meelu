import asyncio
from collections.abc import Coroutine
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.credits.service import credit_service
from src.geo.check import geo_checker
from src.geo.models.check import GeoCheck
from src.geo.models.query import GeoQuery
from src.geo.repositories.checks import geo_checks
from src.geo.repositories.queries import geo_queries
from src.geo.schemas import (
    CHECK_CONCURRENCY,
    MAX_QUERIES_PER_SITE,
    MAX_QUERY_CHARS,
    QUERY_SOURCES,
    RUNNING_TIMEOUT_MINUTES,
    STALE_DAYS,
    CheckResponse,
    ChecksStartResponse,
    ChecksStopResponse,
    QueryPatchRequest,
    QueryResponse,
    QueryUpsertItem,
    SummaryResponse,
    UpsertResponse,
)

TIMED_OUT = "The check stopped reporting, most likely because the server restarted. Check again."


def clean_text(raw: str) -> str:
    return " ".join(str(raw or "").split())


class GeoService:
    def __init__(self) -> None:
        self._running: dict[str, asyncio.Task] = {}
        self._gates: dict[asyncio.AbstractEventLoop, asyncio.Semaphore] = {}

    def _spawn(self, check_id: str, work: Coroutine[Any, Any, None]) -> None:
        task = asyncio.create_task(work)
        self._running[check_id] = task
        task.add_done_callback(lambda _: self._running.pop(check_id, None))

    def _gate(self) -> asyncio.Semaphore:
        loop = asyncio.get_running_loop()
        if loop not in self._gates:
            self._gates = {loop: asyncio.Semaphore(CHECK_CONCURRENCY)}
        return self._gates[loop]

    async def _gated(self, user_id: str, site_id: str, check_id: str) -> None:
        async with self._gate():
            await geo_checker.run(user_id, site_id, check_id)

    def _query_response(self, row: GeoQuery, latest: GeoCheck | None) -> QueryResponse:
        return QueryResponse(
            id=row.id,
            site_id=row.site_id,
            text=row.text,
            source=row.source,
            enabled=row.enabled,
            latest_check=CheckResponse.model_validate(latest) if latest is not None else None,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def _close_timed_out(self, db: AsyncSession) -> None:
        cutoff = datetime.now(UTC) - timedelta(minutes=RUNNING_TIMEOUT_MINUTES)
        await geo_checks.fail_running_before(db, cutoff, TIMED_OUT)

    async def list_queries(self, db: AsyncSession, site_id: str) -> list[QueryResponse]:
        await self._close_timed_out(db)
        latest = await geo_checks.latest_by_query(db, site_id)
        return [
            self._query_response(r, latest.get(r.id))
            for r in await geo_queries.list_for_site(db, site_id)
        ]

    async def get_query(self, db: AsyncSession, site_id: str, query_id: str) -> QueryResponse:
        await self._close_timed_out(db)
        row = await self._query_row(db, site_id, query_id)
        latest = await geo_checks.latest_by_query(db, site_id)
        return self._query_response(row, latest.get(row.id))

    async def _query_row(self, db: AsyncSession, site_id: str, query_id: str) -> GeoQuery:
        row = await geo_queries.get(db, site_id, query_id)
        if row is None:
            raise HTTPException(404, f"No question {query_id} for this website.")
        return row

    async def upsert_queries(
        self, db: AsyncSession, user_id: str, site_id: str, items: list[QueryUpsertItem]
    ) -> UpsertResponse:
        cleaned: dict[str, dict[str, Any]] = {}
        for item in items:
            text = clean_text(item.text)
            if not text:
                raise HTTPException(400, "A question must not be empty.")
            if len(text) > MAX_QUERY_CHARS:
                raise HTTPException(
                    400, f"A question must be at most {MAX_QUERY_CHARS} characters."
                )
            if item.source not in QUERY_SOURCES:
                raise HTTPException(400, f"source must be one of {', '.join(QUERY_SOURCES)}.")
            cleaned[text] = {"text": text, "enabled": item.enabled, "source": item.source}
        existing = await geo_queries.existing_texts(db, site_id, list(cleaned))
        new = len(cleaned) - len(existing)
        if await geo_queries.count(db, site_id) + new > MAX_QUERIES_PER_SITE:
            raise HTTPException(
                409, f"A website can track at most {MAX_QUERIES_PER_SITE} questions."
            )
        await geo_queries.upsert_many(db, user_id, site_id, list(cleaned.values()))
        return UpsertResponse(inserted=new, updated=len(existing))

    async def patch_query(
        self, db: AsyncSession, site_id: str, query_id: str, body: QueryPatchRequest
    ) -> QueryResponse:
        row = await self._query_row(db, site_id, query_id)
        values = body.changes()
        if "text" in values:
            text = clean_text(values["text"] or "")
            if not text:
                raise HTTPException(400, "A question must not be empty.")
            if len(text) > MAX_QUERY_CHARS:
                raise HTTPException(
                    400, f"A question must be at most {MAX_QUERY_CHARS} characters."
                )
            other = await geo_queries.get_by_text(db, site_id, text)
            if other is not None and other.id != row.id:
                raise HTTPException(409, "That question is already tracked.")
            values["text"] = text
        if values.get("enabled") is None:
            values.pop("enabled", None)
        row = await geo_queries.update(db, row, values)
        latest = await geo_checks.latest_by_query(db, site_id)
        return self._query_response(row, latest.get(row.id))

    async def delete_query(self, db: AsyncSession, site_id: str, query_id: str) -> str:
        row = await self._query_row(db, site_id, query_id)
        await geo_queries.delete(db, row)
        return query_id

    async def delete_queries(self, db: AsyncSession, site_id: str, ids: list[str]) -> list[str]:
        rows = await geo_queries.list_by_ids(db, site_id, ids)
        for row in rows:
            await geo_queries.delete(db, row)
        return [r.id for r in rows]

    async def start_checks(
        self, db: AsyncSession, user_id: str, site_id: str, query_ids: list[str] | None
    ) -> ChecksStartResponse:
        await credit_service.require_balance(db, user_id)
        await self._close_timed_out(db)
        if query_ids:
            rows = await geo_queries.list_by_ids(db, site_id, query_ids)
            missing = set(query_ids) - {r.id for r in rows}
            if missing:
                raise HTTPException(
                    404, f"No question {', '.join(sorted(missing))} for this website."
                )
        else:
            rows = await self._stale(db, site_id)
        running = await geo_checks.running_query_ids(db, site_id)
        started = []
        for row in rows:
            if row.id in running:
                continue
            started.append(await geo_checks.create(db, user_id, site_id, row.id))
        await db.commit()
        for check in started:
            self._spawn(check.id, self._gated(user_id, site_id, check.id))
        return ChecksStartResponse(
            started=[CheckResponse.model_validate(c) for c in started],
            already_running=sum(1 for r in rows if r.id in running),
        )

    async def stop_checks(self, db: AsyncSession, site_id: str) -> ChecksStopResponse:
        stopped = await geo_checks.stop_running(db, site_id)
        await db.commit()
        for check_id in stopped:
            task = self._running.get(check_id)
            if task is not None:
                task.cancel()
        return ChecksStopResponse(stopped=len(stopped))

    async def _stale(self, db: AsyncSession, site_id: str) -> list[GeoQuery]:
        cutoff = datetime.now(UTC) - timedelta(days=STALE_DAYS)
        finished = await geo_checks.latest_finished_by_query(db, site_id)
        return [
            r
            for r in await geo_queries.list_enabled(db, site_id)
            if r.id not in finished or finished[r.id].started_at < cutoff
        ]

    async def get_check(self, db: AsyncSession, site_id: str, check_id: str) -> CheckResponse:
        await self._close_timed_out(db)
        row = await geo_checks.get(db, site_id, check_id)
        if row is None:
            raise HTTPException(404, f"No check {check_id} for this website.")
        return CheckResponse.model_validate(row)

    async def list_checks(
        self, db: AsyncSession, site_id: str, query_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[CheckResponse]:
        await self._query_row(db, site_id, query_id)
        return await geo_checks.list_for_query(db, site_id, query_id, paging)

    async def delete_check(self, db: AsyncSession, site_id: str, check_id: str) -> str:
        row = await geo_checks.get(db, site_id, check_id)
        if row is None:
            raise HTTPException(404, f"No check {check_id} for this website.")
        if row.status == "running":
            raise HTTPException(409, "This check is still running.")
        await geo_checks.delete(db, row)
        return check_id

    async def summary(self, db: AsyncSession, site_id: str) -> SummaryResponse:
        await self._close_timed_out(db)
        queries = await geo_queries.list_for_site(db, site_id)
        latest = await geo_checks.latest_by_query(db, site_id)
        finished = await geo_checks.latest_finished_by_query(db, site_id)
        verdicts = [finished[q.id].verdict for q in queries if q.id in finished]
        return SummaryResponse(
            queries=len(queries),
            unchecked=sum(1 for q in queries if q.id not in finished),
            running=sum(1 for q in queries if q.id in latest and latest[q.id].status == "running"),
            no_page=verdicts.count("no_page"),
            partial=verdicts.count("partial"),
            low_rank=verdicts.count("low_rank"),
            covered=verdicts.count("covered"),
            cited=sum(
                1
                for q in queries
                if q.id in finished
                and any(a.get("citedUs") for a in finished[q.id].ai_answers or [])
            ),
            last_checked_at=max(
                (c.finished_at for c in finished.values() if c.finished_at), default=None
            ),
        )


geo_service = GeoService()
