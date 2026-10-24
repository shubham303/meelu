import asyncio
from collections.abc import Coroutine
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.credits.service import credit_service
from src.providers.social_search.platforms import PLATFORMS, WEB_SEARCHED_PLATFORMS
from src.providers.social_search.repository import social_posts
from src.providers.social_search.service import social_search
from src.providers.social_search.store import vendor_keywords
from src.social_listening.checking import classify_posts
from src.social_listening.collect import (
    SILENT_ERROR,
    collect_platform,
    is_silent,
    keyword_windows,
    normalize_keyword,
    recently_searched,
    running_stats,
    site_keywords,
)
from src.social_listening.models.config import SocialListeningConfig
from src.social_listening.models.query import SocialListeningQuery
from src.social_listening.models.run import SocialListeningRun
from src.social_listening.repositories.config import social_listening_configs
from src.social_listening.repositories.cursors import social_listening_cursors
from src.social_listening.repositories.posts import social_listening_posts
from src.social_listening.repositories.queries import social_listening_queries
from src.social_listening.repositories.runs import social_listening_runs
from src.social_listening.schemas import (
    DONE_STATUSES,
    KEYWORDS_PER_LINE,
    MAX_LINES_PER_SITE,
    MAX_WEB_POSTS,
    MIN_SIMILARITY,
    MINIMUM_BALANCE_USD,
    PER_KEYWORD,
    POST_STATUSES,
    RUN_STATUSES,
    SKIP_HOURS,
    USER_STATUSES,
    WEB_COST_PER_LINE_MICROS,
    WEB_LOOKBACK_DAYS,
    WEB_PLATFORM,
    CheckRequest,
    CheckResponse,
    ConfigResponse,
    ConfigUpdateRequest,
    EstimateResponse,
    GateResponse,
    JudgeResponse,
    PlatformEstimate,
    PostFilters,
    PostPatchRequest,
    PostResponse,
    PostsJudgeRequest,
    QueryPatchRequest,
    QueryResponse,
    QueryUpsertItem,
    RunResponse,
    RunUpdateRequest,
    SearchResponse,
    SummaryResponse,
    UpsertResponse,
    WebPostsRequest,
)
from src.social_listening.web import web_post_rows, web_stats

EMBED_MAX_ATTEMPTS = 3
CURSOR_RETENTION_DAYS = 30
QUIET_RUN_SECONDS = 120
QUIET_RUN_ERROR = "The app stopped working on this run before it finished, so it was closed."
PLATFORM_IDS = tuple(p["id"] for p in PLATFORMS)
SOURCE_IDS = (*PLATFORM_IDS, WEB_PLATFORM)
WEB_SOURCE_IDS = (WEB_PLATFORM, *WEB_SEARCHED_PLATFORMS)


class SocialListeningService:
    def __init__(self) -> None:
        self._collecting: set[asyncio.Task] = set()

    def _spawn(self, work: Coroutine[Any, Any, None]) -> None:
        task = asyncio.create_task(work)
        self._collecting.add(task)
        task.add_done_callback(self._collecting.discard)

    def _config_response(self, row: SocialListeningConfig) -> ConfigResponse:
        return ConfigResponse(
            id=row.id,
            site_id=row.site_id,
            platforms=[p for p in row.platforms if p in SOURCE_IDS],
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def _config_row(
        self, db: AsyncSession, user_id: str, site_id: str
    ) -> SocialListeningConfig:
        row = await social_listening_configs.get(db, site_id)
        if row is None:
            row = await social_listening_configs.create(db, user_id, site_id)
        return row

    async def get_config(self, db: AsyncSession, user_id: str, site_id: str) -> ConfigResponse:
        return self._config_response(await self._config_row(db, user_id, site_id))

    async def update_config(
        self, db: AsyncSession, user_id: str, site_id: str, body: ConfigUpdateRequest
    ) -> ConfigResponse:
        values = body.changes()
        platforms = values.get("platforms")
        if platforms is not None:
            unknown = [p for p in platforms if p not in SOURCE_IDS]
            if unknown:
                raise HTTPException(400, f"Unknown platform: {', '.join(unknown)}.")
            values["platforms"] = list(dict.fromkeys(platforms))
        row = await self._config_row(db, user_id, site_id)
        row = await social_listening_configs.update(db, row, values)
        return self._config_response(row)

    def _query_response(
        self, row: SocialListeningQuery, found: dict[str, int], kept: dict[str, int]
    ) -> QueryResponse:
        return QueryResponse(
            id=row.id,
            site_id=row.site_id,
            text=row.text,
            enabled=row.enabled,
            source=row.source,
            keywords=row.keywords,
            embedded=row.embedding is not None,
            found=found.get(row.id, 0),
            kept=kept.get(row.id, 0),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def list_queries(self, db: AsyncSession, site_id: str) -> list[QueryResponse]:
        rows = await social_listening_queries.list(db, site_id)
        found = await social_listening_posts.counts_by_query(db, site_id)
        kept = await social_listening_posts.counts_by_query(db, site_id, USER_STATUSES)
        return [self._query_response(row, found, kept) for row in rows]

    async def upsert_queries(
        self, db: AsyncSession, user_id: str, site_id: str, items: list[QueryUpsertItem]
    ) -> UpsertResponse:
        deduped: dict[str, QueryUpsertItem] = {}
        for item in items:
            text = " ".join(item.text.split())
            if text:
                deduped[text] = item
        existing = await social_listening_queries.existing_texts(db, site_id, list(deduped))
        added = len(deduped) - len(existing)
        if added and await social_listening_queries.count(db, site_id) + added > MAX_LINES_PER_SITE:
            raise HTTPException(
                400,
                f"A website can listen for at most {MAX_LINES_PER_SITE} lines. "
                "Remove or edit a line before adding another.",
            )
        values = [
            {"text": text, "enabled": item.enabled, "source": item.source}
            for text, item in deduped.items()
        ]
        await social_listening_queries.upsert_many(db, user_id, site_id, values)
        return UpsertResponse(inserted=added, updated=len(existing))

    def _clean_keywords(self, keywords: list[str]) -> list[str]:
        clean = list(dict.fromkeys(k for k in (normalize_keyword(k) for k in keywords) if k))
        if clean and len(clean) != KEYWORDS_PER_LINE:
            raise HTTPException(
                400, f"A line needs exactly {KEYWORDS_PER_LINE} different keywords."
            )
        return clean

    async def patch_query(
        self, db: AsyncSession, site_id: str, query_id: str, body: QueryPatchRequest
    ) -> QueryResponse:
        row = await social_listening_queries.get(db, site_id, query_id)
        if row is None:
            raise HTTPException(404, "Not found")
        values = body.changes()
        if "keywords" in values:
            values["keywords"] = self._clean_keywords(values["keywords"] or [])
        if "text" in values:
            text = " ".join((values["text"] or "").split())
            if not text:
                raise HTTPException(400, "text must not be empty.")
            if text != row.text:
                values.update(
                    text=text,
                    embedding=None,
                    embed_model=None,
                    embed_attempts=0,
                    embed_error=None,
                    keywords=[],
                )
        row = await social_listening_queries.update(db, row, values)
        found = await social_listening_posts.counts_by_query(db, site_id)
        kept = await social_listening_posts.counts_by_query(db, site_id, USER_STATUSES)
        return self._query_response(row, found, kept)

    async def delete_query(self, db: AsyncSession, site_id: str, query_id: str) -> str:
        row = await social_listening_queries.get(db, site_id, query_id)
        if row is None:
            raise HTTPException(404, "Not found")
        await social_listening_queries.delete(db, row)
        return query_id

    async def _close_quiet_runs(self, db: AsyncSession, user_id: str) -> None:
        await social_listening_runs.fail_quiet_since(
            db,
            datetime.now(UTC) - timedelta(seconds=QUIET_RUN_SECONDS),
            QUIET_RUN_ERROR,
            user_id=user_id,
        )

    async def create_run(self, db: AsyncSession, user_id: str, site_id: str) -> RunResponse:
        await self._close_quiet_runs(db, user_id)
        if await social_listening_runs.running_for_user(db, user_id) is not None:
            raise HTTPException(
                409,
                "Another social listening run is still going on one of your websites. "
                "Wait for it to finish or stop it first.",
            )
        balance = await credit_service.balance(db, user_id)
        if balance.balance_micros < MINIMUM_BALANCE_USD * 1_000_000:
            raise HTTPException(
                402, f"Social listening needs a credit balance of at least ${MINIMUM_BALANCE_USD}."
            )
        try:
            async with db.begin_nested():
                return await social_listening_runs.create(db, user_id, site_id)
        except IntegrityError:
            raise HTTPException(
                409,
                "Another social listening run is still going on one of your websites. "
                "Wait for it to finish or stop it first.",
            ) from None

    async def start_collect(
        self, db: AsyncSession, user_id: str, site_id: str, run_id: str, platform: str
    ) -> RunResponse:
        row = await social_listening_runs.get(db, site_id, run_id)
        if row is None:
            raise HTTPException(404, "Not found")
        if row.status != "running":
            raise HTTPException(409, "This run is no longer going.")
        row = await self._close_silent_collects(db, row)
        if platform not in PLATFORM_IDS or not social_search.supports(f"search.{platform}"):
            raise HTTPException(400, f"{platform} cannot be searched right now.")
        if (row.platform_stats.get(platform) or {}).get("status") == "running":
            return RunResponse.model_validate(row)
        await social_listening_runs.merge_platform_stats(db, run_id, platform, running_stats())
        await db.commit()
        self._spawn(collect_platform(user_id, site_id, run_id, platform))
        row = await social_listening_runs.get(db, site_id, run_id)
        await db.refresh(row)
        return RunResponse.model_validate(row)

    async def save_web_posts(
        self, db: AsyncSession, user_id: str, site_id: str, run_id: str, body: WebPostsRequest
    ) -> RunResponse:
        row = await social_listening_runs.get(db, site_id, run_id)
        if row is None:
            raise HTTPException(404, "Not found")
        if row.status != "running":
            raise HTTPException(409, "This run is no longer going.")
        if body.platform not in WEB_SOURCE_IDS:
            raise HTTPException(400, f"{body.platform} is not searched on the web.")
        now = datetime.now(UTC)
        rows = web_post_rows(
            body.platform,
            body.posts[:MAX_WEB_POSTS],
            now - timedelta(days=WEB_LOOKBACK_DAYS),
            now,
        )
        await social_posts.insert_new(db, rows)
        post_ids = await social_posts.ids_by_keys(db, [r["post_key"] for r in rows])
        candidates = await social_listening_posts.insert_candidates(
            db, user_id, site_id, run_id, post_ids
        )
        stats = web_stats(
            len(rows),
            candidates,
            body.searched_lines,
            body.failed_lines,
            body.error,
            body.skipped_queries,
        )
        await social_listening_runs.merge_platform_stats(
            db, run_id, body.platform, stats, fetched=len(rows)
        )
        searched = list(
            dict.fromkeys(q for q in (normalize_keyword(q) for q in body.searched_queries) if q)
        )
        await social_listening_cursors.advance(db, user_id, site_id, body.platform, searched, now)
        await db.refresh(row)
        return RunResponse.model_validate(row)

    async def list_searches(
        self, db: AsyncSession, site_id: str, platform: str
    ) -> list[SearchResponse]:
        cutoff = datetime.now(UTC) - timedelta(hours=SKIP_HOURS)
        recent = await social_listening_cursors.since(db, site_id, platform, cutoff)
        return [
            SearchResponse(platform=platform, query=query, searched_at=at)
            for query, at in recent.items()
        ]

    async def patch_run(
        self, db: AsyncSession, site_id: str, run_id: str, body: RunUpdateRequest
    ) -> RunResponse:
        row = await social_listening_runs.get(db, site_id, run_id)
        if row is None:
            raise HTTPException(404, "Not found")
        values = body.changes()
        status = values.get("status")
        if status is not None and status not in RUN_STATUSES:
            raise HTTPException(400, f"status must be one of {', '.join(RUN_STATUSES)}.")
        if status in ("done", "stopped", "error"):
            values["finished_at"] = datetime.now(UTC)
        return await social_listening_runs.update(db, row, values)

    async def list_runs(
        self, db: AsyncSession, site_id: str, paging: PaginationParams
    ) -> PaginatedApiResponse[RunResponse]:
        return await social_listening_runs.list(db, site_id, paging)

    async def get_run(self, db: AsyncSession, site_id: str, run_id: str) -> RunResponse:
        row = await social_listening_runs.get(db, site_id, run_id)
        if row is None:
            raise HTTPException(404, "Not found")
        return RunResponse.model_validate(await self._close_silent_collects(db, row))

    async def _close_silent_collects(
        self, db: AsyncSession, row: SocialListeningRun
    ) -> SocialListeningRun:
        now = datetime.now(UTC)
        silent = [p for p, stats in row.platform_stats.items() if is_silent(stats or {}, now)]
        for platform in silent:
            await social_listening_runs.merge_platform_stats(
                db, row.id, platform, {"status": "error", "error": SILENT_ERROR}
            )
        if silent:
            await db.refresh(row)
        return row

    async def estimate(self, db: AsyncSession, site_id: str) -> EstimateResponse:
        lines = await social_listening_queries.list_enabled(db, site_id)
        ready = [line for line in lines if len(line.keywords or []) == KEYWORDS_PER_LINE]
        pending = KEYWORDS_PER_LINE * (len(lines) - len(ready))
        keywords = site_keywords(ready)
        now = datetime.now(UTC)
        out = []
        for platform in social_search.available_platforms():
            if not platform["available"] or platform["id"] in WEB_SEARCHED_PLATFORMS:
                continue
            cursors = await social_listening_cursors.by_keyword(
                db, site_id, platform["id"], keywords
            )
            skipped = {s["query"] for s in recently_searched(cursors, now)}
            windows = keyword_windows([k for k in keywords if k not in skipped], cursors, now)
            searched = len(await vendor_keywords(db, platform["id"], windows)) + pending
            out.append(
                PlatformEstimate(
                    platform=platform["id"],
                    keywords=len(keywords) + pending,
                    vendor_keywords=searched,
                    max_cost_micros=await social_search.max_cost_micros(
                        platform["id"], searched, PER_KEYWORD
                    ),
                )
            )
        line_texts = [normalize_keyword(line.text) for line in lines]
        for source in WEB_SOURCE_IDS:
            web_cursors = await social_listening_cursors.by_keyword(db, site_id, source, line_texts)
            web_skipped = {s["query"] for s in recently_searched(web_cursors, now)}
            web_lines = [text for text in line_texts if text not in web_skipped]
            out.append(
                PlatformEstimate(
                    platform=source,
                    keywords=len(lines),
                    vendor_keywords=len(web_lines),
                    max_cost_micros=len(web_lines) * WEB_COST_PER_LINE_MICROS,
                )
            )
        return EstimateResponse(platforms=out)

    async def gate_posts(self, db: AsyncSession, site_id: str) -> GateResponse:
        waiting_lines = await social_listening_queries.count_waiting_for_embedding(
            db, site_id, EMBED_MAX_ATTEMPTS
        )
        removed = await social_listening_posts.delete_unembeddable_candidates(
            db, site_id, EMBED_MAX_ATTEMPTS
        )
        pending = await social_listening_posts.count_unembedded_candidates(
            db, site_id, EMBED_MAX_ATTEMPTS
        )
        if waiting_lines:
            return GateResponse(pending=pending + waiting_lines, matched=0, removed=removed)
        matched = await social_listening_posts.match_candidates(db, site_id, MIN_SIMILARITY)
        removed += await social_listening_posts.delete_embedded_candidates(db, site_id)
        return GateResponse(pending=pending, matched=matched, removed=removed)

    async def check_posts(
        self, db: AsyncSession, user_id: str, site_id: str, body: CheckRequest
    ) -> CheckResponse:
        rows = [
            row
            for row in await social_listening_posts.get_many_with_posts(db, site_id, body.ids)
            if row[0].status == "matched"
        ]
        lines = {q.id: q.text for q in await social_listening_queries.list(db, site_id)}
        await db.commit()
        verdicts, errors, planned = await classify_posts(user_id, site_id, rows, lines)
        if planned and len(errors) == planned:
            raise HTTPException(502, f"The fit check failed: {errors[0]}")
        fresh = await social_listening_posts.get_many(db, site_id, [own.id for own, _ in verdicts])
        still_matched = [
            (own, keep)
            for own, keep in verdicts
            if own.id in fresh and fresh[own.id].status == "matched"
        ]
        removed = await social_listening_posts.delete_many(
            db, site_id, [own.id for own, keep in still_matched if not keep]
        )
        return CheckResponse(fits=[own.id for own, keep in still_matched if keep], removed=removed)

    async def judge_posts(
        self, db: AsyncSession, site_id: str, body: PostsJudgeRequest
    ) -> JudgeResponse:
        rows = await social_listening_posts.get_many(db, site_id, [item.id for item in body.posts])
        kept, dropped = 0, []
        for item in body.posts:
            row = rows.get(item.id)
            if row is None:
                raise HTTPException(404, f"No post {item.id} for this website.")
            if row.status != "matched":
                continue
            if not item.keep:
                dropped.append(row.id)
                continue
            await social_listening_posts.update(
                db,
                row,
                {
                    "status": "to_reply",
                    "keep_reason": item.keep_reason,
                    "suggested_angle": item.suggested_angle,
                },
            )
            kept += 1
        removed = await social_listening_posts.delete_many(db, site_id, dropped)
        return JudgeResponse(kept=kept, removed=removed)

    async def list_posts(
        self, db: AsyncSession, site_id: str, filters: PostFilters, paging: PaginationParams
    ) -> PaginatedApiResponse[PostResponse]:
        for status in filters.statuses or []:
            if status not in POST_STATUSES:
                raise HTTPException(400, f"status must be one of {', '.join(POST_STATUSES)}.")
        return await social_listening_posts.list(db, site_id, filters, paging)

    async def get_post(self, db: AsyncSession, site_id: str, post_id: str) -> PostResponse:
        post = await social_listening_posts.get_response(db, site_id, post_id)
        if post is None:
            raise HTTPException(404, "Not found")
        return post

    async def patch_post(
        self, db: AsyncSession, site_id: str, post_id: str, body: PostPatchRequest
    ) -> PostResponse:
        row = await social_listening_posts.get(db, site_id, post_id)
        if row is None:
            raise HTTPException(404, "Not found")
        values = body.changes()
        status = values.get("status")
        if status is not None:
            if status not in USER_STATUSES:
                raise HTTPException(400, f"status must be one of {', '.join(USER_STATUSES)}.")
            if row.status not in USER_STATUSES:
                raise HTTPException(409, "This post was never shown for review.")
            if status == "replied" and row.status != "replied":
                values["replied_at"] = datetime.now(UTC)
            if status != "replied":
                values["replied_at"] = None
        await social_listening_posts.update(db, row, values)
        return await self.get_post(db, site_id, post_id)

    async def summary(self, db: AsyncSession, user_id: str, site_id: str) -> SummaryResponse:
        await self._close_quiet_runs(db, user_id)
        statuses = await social_listening_posts.status_counts(db, site_id)
        return SummaryResponse(
            to_reply=statuses.get("to_reply", 0),
            drafted=statuses.get("drafted", 0),
            replied=statuses.get("replied", 0),
            skipped=statuses.get("skipped", 0),
            rejected=statuses.get("rejected", 0),
            done=sum(statuses.get(s, 0) for s in DONE_STATUSES),
            unprocessed=statuses.get("candidate", 0) + statuses.get("matched", 0),
            last_run=await social_listening_runs.latest(db, site_id),
        )

    async def purge(self, db: AsyncSession) -> dict[str, int]:
        now = datetime.now(UTC)
        cutoff = now - timedelta(days=CURSOR_RETENTION_DAYS)
        return {
            "cursors": await social_listening_cursors.delete_older_than(db, cutoff),
            "runs": await social_listening_runs.fail_quiet_since(
                db, now - timedelta(seconds=QUIET_RUN_SECONDS), QUIET_RUN_ERROR
            ),
        }


social_listening_service = SocialListeningService()
