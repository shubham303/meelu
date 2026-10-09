from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.social_listening.identity import content_hash, native_id, post_key
from src.social_listening.models.config import SocialListeningConfig
from src.social_listening.models.query import SocialListeningQuery
from src.social_listening.repositories.config import social_listening_configs
from src.social_listening.repositories.posts import social_listening_posts
from src.social_listening.repositories.queries import social_listening_queries
from src.social_listening.repositories.runs import social_listening_runs
from src.social_listening.schemas import (
    DONE_STATUSES,
    INGEST_DROP_REASONS,
    JUDGE_DROP_REASONS,
    JUDGE_STATUSES,
    POST_SORTS,
    POST_STATUSES,
    RUN_STATUSES,
    STRICTNESS_THRESHOLDS,
    USER_STATUSES,
    BulkInsertResponse,
    ConfigResponse,
    ConfigUpdateRequest,
    GateResponse,
    JudgeResponse,
    PostFilters,
    PostPatchRequest,
    PostResponse,
    PostsBulkRequest,
    PostsJudgeRequest,
    QueryPatchRequest,
    QueryResponse,
    QueryUpsertItem,
    RunResponse,
    RunUpdateRequest,
    SummaryResponse,
    UpsertResponse,
)

INGEST_FIELDS = (
    "url",
    "platform",
    "title",
    "text",
    "author_handle",
    "author_name",
    "posted_at",
    "engagement",
    "context",
    "query_id",
)

JUDGE_FIELDS = ("relevance", "composite_score", "keep_reason", "suggested_angle")

EMBED_MAX_ATTEMPTS = 3

MAX_AGE_DAYS_LIMIT = 3650


class SocialListeningService:
    def _config_response(self, row: SocialListeningConfig) -> ConfigResponse:
        min_similarity, min_relevance = STRICTNESS_THRESHOLDS[row.strictness]
        return ConfigResponse(
            id=row.id,
            site_id=row.site_id,
            platforms=row.platforms,
            results_per_keyword=row.results_per_keyword,
            strictness=row.strictness,
            max_age_days=row.max_age_days,
            min_similarity=min_similarity,
            min_relevance=min_relevance,
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
        strictness = values.get("strictness")
        if strictness is not None and strictness not in STRICTNESS_THRESHOLDS:
            raise HTTPException(
                400, f"strictness must be one of {', '.join(STRICTNESS_THRESHOLDS)}."
            )
        days = values.get("max_age_days")
        if days is not None and not 1 <= days <= MAX_AGE_DAYS_LIMIT:
            raise HTTPException(400, f"maxAgeDays must be between 1 and {MAX_AGE_DAYS_LIMIT}.")
        per_keyword = values.get("results_per_keyword")
        if per_keyword is not None and per_keyword < 1:
            raise HTTPException(400, "resultsPerKeyword must be at least 1.")
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
            negative_keywords=row.negative_keywords,
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
        values = [
            {"text": text, "enabled": item.enabled, "source": item.source}
            for text, item in deduped.items()
        ]
        await social_listening_queries.upsert_many(db, user_id, site_id, values)
        return UpsertResponse(inserted=len(deduped) - len(existing), updated=len(existing))

    async def patch_query(
        self, db: AsyncSession, site_id: str, query_id: str, body: QueryPatchRequest
    ) -> QueryResponse:
        row = await social_listening_queries.get(db, site_id, query_id)
        if row is None:
            raise HTTPException(404, "Not found")
        values = body.changes()
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
                    negative_keywords=[],
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

    async def create_run(self, db: AsyncSession, user_id: str, site_id: str) -> RunResponse:
        return await social_listening_runs.create(db, user_id, site_id)

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
        if status in ("done", "stopped", "error") and values.get("finished_at") is None:
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
        return RunResponse.model_validate(row)

    async def ingest_posts(
        self, db: AsyncSession, user_id: str, site_id: str, body: PostsBulkRequest
    ) -> BulkInsertResponse:
        if (
            body.run_id is not None
            and await social_listening_runs.get(db, site_id, body.run_id) is None
        ):
            raise HTTPException(404, f"No listening run {body.run_id} for this website.")
        query_ids = sorted({item.query_id for item in body.posts if item.query_id is not None})
        unknown = set(query_ids) - await social_listening_queries.existing_ids(
            db, site_id, query_ids
        )
        if unknown:
            raise HTTPException(
                404, f"No listening query {', '.join(sorted(unknown))} for this website."
            )
        candidates: dict[str, dict] = {}
        received = 0
        for item in body.posts:
            url = item.url.strip()
            if not url:
                continue
            received += 1
            if item.drop_reason is not None and item.drop_reason not in INGEST_DROP_REASONS:
                raise HTTPException(
                    400, f"dropReason must be one of {', '.join(INGEST_DROP_REASONS)}."
                )
            key = post_key(item.platform, item.external_id, url)
            if key in candidates:
                continue
            values = {field: getattr(item, field) for field in INGEST_FIELDS}
            values.update(
                url=url,
                post_key=key,
                external_id=native_id(item.platform, item.external_id, url),
                content_hash=content_hash(item.title, item.text),
                run_id=body.run_id,
                status="dropped" if item.drop_reason else "fetched",
                drop_reason=item.drop_reason,
            )
            candidates[key] = values
        known = await social_listening_posts.existing_keys(db, site_id, list(candidates))
        fresh = [v for k, v in candidates.items() if k not in known]
        seen_hashes = await social_listening_posts.existing_hashes(
            db, site_id, [v["content_hash"] for v in fresh if v["content_hash"]]
        )
        duplicates = 0
        for values in fresh:
            digest = values["content_hash"]
            if digest is None:
                continue
            if digest in seen_hashes and values["status"] == "fetched":
                values.update(status="dropped", drop_reason="duplicate")
                duplicates += 1
            seen_hashes.add(digest)
        inserted = await social_listening_posts.create_many(db, user_id, site_id, fresh)
        return BulkInsertResponse(
            inserted=inserted,
            known=received - inserted,
            duplicates=duplicates,
        )

    async def gate_posts(self, db: AsyncSession, user_id: str, site_id: str) -> GateResponse:
        config = await self.get_config(db, user_id, site_id)
        states = await social_listening_queries.embedding_states(db, site_id)
        orphaned = await social_listening_posts.drop_orphaned(db, site_id, list(states))
        vectors = await social_listening_queries.embeddings_by_ids(
            db, site_id, [qid for qid, (has, _) in states.items() if has]
        )
        counts = await social_listening_posts.apply_similarity(
            db, site_id, vectors, config.min_similarity
        )
        stuck = await social_listening_posts.drop_unembeddable(
            db,
            site_id,
            [qid for qid, (_, attempts) in states.items() if attempts >= EMBED_MAX_ATTEMPTS],
            EMBED_MAX_ATTEMPTS,
        )
        pending = await social_listening_posts.count_pending_gate(
            db,
            site_id,
            [qid for qid, (_, attempts) in states.items() if attempts < EMBED_MAX_ATTEMPTS],
            [qid for qid, (has, _) in states.items() if not has],
        )
        kept = counts.get("matched", 0)
        dropped = counts.get("dropped", 0) + stuck + orphaned
        return GateResponse(pending=pending, scored=kept + dropped, kept=kept, dropped=dropped)

    async def judge_posts(
        self, db: AsyncSession, site_id: str, body: PostsJudgeRequest
    ) -> JudgeResponse:
        rows = await social_listening_posts.get_many(db, site_id, [item.id for item in body.posts])
        updated = 0
        for item in body.posts:
            if item.status not in JUDGE_STATUSES:
                raise HTTPException(400, f"status must be one of {', '.join(JUDGE_STATUSES)}.")
            if item.status == "dropped" and item.drop_reason not in JUDGE_DROP_REASONS:
                raise HTTPException(
                    400, f"dropReason must be one of {', '.join(JUDGE_DROP_REASONS)}."
                )
            row = rows.get(item.id)
            if row is None:
                raise HTTPException(404, f"No post {item.id} for this website.")
            if row.status != "matched":
                continue
            values = {field: getattr(item, field) for field in JUDGE_FIELDS}
            values["status"] = item.status
            values["drop_reason"] = item.drop_reason if item.status == "dropped" else None
            await social_listening_posts.update(db, row, values)
            updated += 1
        return JudgeResponse(updated=updated)

    def _check_filters(self, filters: PostFilters) -> None:
        if filters.sort is not None and filters.sort not in POST_SORTS:
            raise HTTPException(400, f"sort must be one of {', '.join(POST_SORTS)}.")
        for status in filters.statuses or []:
            if status not in POST_STATUSES:
                raise HTTPException(400, f"status must be one of {', '.join(POST_STATUSES)}.")

    async def list_posts(
        self, db: AsyncSession, site_id: str, filters: PostFilters, paging: PaginationParams
    ) -> PaginatedApiResponse[PostResponse]:
        self._check_filters(filters)
        return await social_listening_posts.list(db, site_id, filters, paging)

    async def get_post(self, db: AsyncSession, site_id: str, post_id: str) -> PostResponse:
        row = await social_listening_posts.get(db, site_id, post_id)
        if row is None:
            raise HTTPException(404, "Not found")
        return PostResponse.model_validate(row)

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
        return await social_listening_posts.update(db, row, values)

    async def summary(self, db: AsyncSession, site_id: str) -> SummaryResponse:
        statuses = await social_listening_posts.status_counts(db, site_id)
        return SummaryResponse(
            to_reply=statuses.get("to_reply", 0),
            drafted=statuses.get("drafted", 0),
            replied=statuses.get("replied", 0),
            skipped=statuses.get("skipped", 0),
            rejected=statuses.get("rejected", 0),
            done=sum(statuses.get(s, 0) for s in DONE_STATUSES),
            unprocessed=statuses.get("fetched", 0) + statuses.get("matched", 0),
            last_run=await social_listening_runs.latest(db, site_id),
        )

    async def export_posts(self, db: AsyncSession, site_id: str, filters: PostFilters):
        self._check_filters(filters)
        return await social_listening_posts.list_all(db, site_id, filters)


social_listening_service = SocialListeningService()
