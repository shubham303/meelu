from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.pagination import PaginatedApiResponse, PaginationParams
from src.social_listening import repository as repo
from src.social_listening.schemas import (
    MENTION_CLASSES,
    POST_KINDS,
    POST_SORTS,
    POST_STATUSES,
    RUN_STATUSES,
    TARGET_KINDS,
    BulkUpsertResponse,
    ConfigResponse,
    ConfigUpdateRequest,
    GateResponse,
    KeptQueryCount,
    MentionClassCounts,
    PostFilters,
    PostPatchRequest,
    PostResponse,
    PostsBulkRequest,
    PostsClassifyRequest,
    QueryPatchRequest,
    QueryResponse,
    QueryUpsertItem,
    RunResponse,
    RunUpdateRequest,
    SentimentCounts,
    SummaryResponse,
    TargetPatchRequest,
    TargetResponse,
    TargetUpsertItem,
)

POST_UPSERT_FIELDS = (
    "platform",
    "kind",
    "title",
    "text",
    "author_handle",
    "author_name",
    "posted_at",
    "engagement",
    "context",
    "matched_targets",
    "query_id",
)

POST_CLASSIFY_FIELDS = (
    "intent",
    "sentiment",
    "is_question",
    "classes",
    "relevance",
    "composite_score",
    "keep_reason",
)

CLASSIFY_STATUSES = ("needs_reply", "filtered")


async def get_config(db: AsyncSession, user_id: str, site_id: str) -> ConfigResponse:
    row = await repo.get_config(db, site_id)
    if row is None:
        row = await repo.create_config(db, user_id, site_id)
    return ConfigResponse.model_validate(row)


async def update_config(
    db: AsyncSession, user_id: str, site_id: str, body: ConfigUpdateRequest
) -> ConfigResponse:
    row = await repo.get_config(db, site_id)
    if row is None:
        row = await repo.create_config(db, user_id, site_id)
    return await repo.merge_config(db, row, body.changes())


async def list_queries(db: AsyncSession, site_id: str) -> list[QueryResponse]:
    return await repo.list_queries(db, site_id)


async def upsert_queries(
    db: AsyncSession, user_id: str, site_id: str, items: list[QueryUpsertItem]
) -> BulkUpsertResponse:
    deduped: dict[str, QueryUpsertItem] = {}
    for item in items:
        text = " ".join(item.text.split())
        if text:
            deduped[text] = item
    existing = await repo.existing_query_texts(db, site_id, list(deduped))
    values = [
        {"text": text, "enabled": item.enabled, "source": item.source}
        for text, item in deduped.items()
    ]
    await repo.upsert_queries(db, user_id, site_id, values)
    return BulkUpsertResponse(inserted=len(deduped) - len(existing), updated=len(existing))


async def patch_query(
    db: AsyncSession, site_id: str, query_id: str, body: QueryPatchRequest
) -> QueryResponse:
    row = await repo.query_by_id(db, site_id, query_id)
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
    merged = await repo.merge_row(db, row, values)
    return repo.query_response(merged)


async def delete_query(db: AsyncSession, site_id: str, query_id: str) -> str:
    row = await repo.query_by_id(db, site_id, query_id)
    if row is None:
        raise HTTPException(404, "Not found")
    await repo.delete_row(db, row)
    return query_id


async def list_targets(db: AsyncSession, site_id: str) -> list[TargetResponse]:
    return await repo.list_targets(db, site_id)


async def upsert_targets(
    db: AsyncSession, user_id: str, site_id: str, items: list[TargetUpsertItem]
) -> BulkUpsertResponse:
    deduped: dict[tuple[str, str], TargetUpsertItem] = {}
    for item in items:
        if item.kind not in TARGET_KINDS:
            raise HTTPException(400, f"kind must be one of {', '.join(TARGET_KINDS)}.")
        name = item.name.strip()
        if name:
            deduped[(item.kind, name)] = item
    existing = await repo.existing_target_keys(db, site_id, list(deduped))
    values = [
        {"kind": kind, "name": name, "enabled": item.enabled, "source": item.source}
        for (kind, name), item in deduped.items()
    ]
    await repo.upsert_targets(db, user_id, site_id, values)
    return BulkUpsertResponse(inserted=len(deduped) - len(existing), updated=len(existing))


async def patch_target(
    db: AsyncSession, site_id: str, target_id: str, body: TargetPatchRequest
) -> TargetResponse:
    row = await repo.target_by_id(db, site_id, target_id)
    if row is None:
        raise HTTPException(404, "Not found")
    merged = await repo.merge_row(db, row, body.changes())
    return TargetResponse.model_validate(merged)


async def delete_target(db: AsyncSession, site_id: str, target_id: str) -> str:
    row = await repo.target_by_id(db, site_id, target_id)
    if row is None:
        raise HTTPException(404, "Not found")
    await repo.delete_row(db, row)
    return target_id


async def create_run(db: AsyncSession, user_id: str, site_id: str) -> RunResponse:
    return await repo.create_run(db, user_id, site_id)


async def patch_run(
    db: AsyncSession, site_id: str, run_id: str, body: RunUpdateRequest
) -> RunResponse:
    row = await repo.run_by_id(db, site_id, run_id)
    if row is None:
        raise HTTPException(404, "Not found")
    values = body.changes()
    status = values.get("status")
    if status is not None and status not in RUN_STATUSES:
        raise HTTPException(400, f"status must be one of {', '.join(RUN_STATUSES)}.")
    if status in ("done", "stopped", "error") and values.get("finished_at") is None:
        values["finished_at"] = datetime.now(UTC)
    merged = await repo.merge_row(db, row, values)
    return RunResponse.model_validate(merged)


async def list_runs(
    db: AsyncSession, site_id: str, paging: PaginationParams
) -> PaginatedApiResponse[RunResponse]:
    return await repo.list_runs(db, site_id, paging)


async def get_run(db: AsyncSession, site_id: str, run_id: str) -> RunResponse:
    row = await repo.run_by_id(db, site_id, run_id)
    if row is None:
        raise HTTPException(404, "Not found")
    return RunResponse.model_validate(row)


async def bulk_upsert_posts(
    db: AsyncSession, user_id: str, site_id: str, body: PostsBulkRequest
) -> BulkUpsertResponse:
    if body.run_id is not None and await repo.run_by_id(db, site_id, body.run_id) is None:
        raise HTTPException(404, f"No listening run {body.run_id} for this website.")
    deduped = {item.url.strip(): item for item in body.posts if item.url.strip()}
    existing = await repo.posts_by_urls(db, site_id, list(deduped))
    inserted = 0
    for url, item in deduped.items():
        if item.status is not None and item.status not in POST_STATUSES:
            raise HTTPException(400, f"status must be one of {', '.join(POST_STATUSES)}.")
        if url in existing:
            continue
        values = {field: getattr(item, field) for field in POST_UPSERT_FIELDS}
        values["run_id"] = body.run_id
        values["status"] = item.status or "fetched"
        values["keep_reason"] = item.keep_reason
        repo.add_post(db, user_id, site_id, {"url": url, **values})
        inserted += 1
    await db.flush()
    return BulkUpsertResponse(inserted=inserted, updated=len(existing))


async def gate_posts(db: AsyncSession, user_id: str, site_id: str) -> GateResponse:
    config = await get_config(db, user_id, site_id)
    await repo.gate_targets(db, site_id)
    counts = await repo.gate_by_similarity(db, site_id, config.min_similarity)
    stuck = await repo.gate_unembeddable(db, site_id)
    pending = await repo.pending_gate_count(db, site_id)
    kept = counts.get("matched", 0)
    filtered = counts.get("filtered", 0) + stuck
    return GateResponse(pending=pending, scored=kept + filtered, kept=kept, filtered=filtered)


async def classify_posts(
    db: AsyncSession, site_id: str, body: PostsClassifyRequest
) -> BulkUpsertResponse:
    rows = await repo.posts_by_ids(db, site_id, [item.id for item in body.posts])
    updated = 0
    for item in body.posts:
        if item.status not in CLASSIFY_STATUSES:
            raise HTTPException(400, f"status must be one of {', '.join(CLASSIFY_STATUSES)}.")
        row = rows.get(item.id)
        if row is None:
            raise HTTPException(404, f"No post {item.id} for this website.")
        values = {field: getattr(item, field) for field in POST_CLASSIFY_FIELDS}
        values["status"] = item.status
        await repo.merge_row(db, row, values)
        updated += 1
    return BulkUpsertResponse(inserted=0, updated=updated)


async def list_posts(
    db: AsyncSession, site_id: str, filters: PostFilters, paging: PaginationParams
) -> PaginatedApiResponse[PostResponse]:
    if filters.sort is not None and filters.sort not in POST_SORTS:
        raise HTTPException(400, f"sort must be one of {', '.join(POST_SORTS)}.")
    if filters.kind is not None and filters.kind not in POST_KINDS:
        raise HTTPException(400, f"kind must be one of {', '.join(POST_KINDS)}.")
    if filters.status is not None and filters.status not in POST_STATUSES:
        raise HTTPException(400, f"status must be one of {', '.join(POST_STATUSES)}.")
    return await repo.list_posts(db, site_id, filters, paging)


async def get_post(db: AsyncSession, site_id: str, post_id: str) -> PostResponse:
    row = await repo.post_by_id(db, site_id, post_id)
    if row is None:
        raise HTTPException(404, "Not found")
    return PostResponse.model_validate(row)


async def patch_post(
    db: AsyncSession, site_id: str, post_id: str, body: PostPatchRequest
) -> PostResponse:
    row = await repo.post_by_id(db, site_id, post_id)
    if row is None:
        raise HTTPException(404, "Not found")
    values = body.changes()
    status = values.get("status")
    if status is not None:
        if status not in POST_STATUSES:
            raise HTTPException(400, f"status must be one of {', '.join(POST_STATUSES)}.")
        if status == "replied" and row.status != "replied":
            values["replied_at"] = datetime.now(UTC)
    merged = await repo.merge_row(db, row, values)
    return PostResponse.model_validate(merged)


async def delete_post(db: AsyncSession, site_id: str, post_id: str) -> str:
    row = await repo.post_by_id(db, site_id, post_id)
    if row is None:
        raise HTTPException(404, "Not found")
    await repo.delete_row(db, row)
    return post_id


async def summary(db: AsyncSession, site_id: str) -> SummaryResponse:
    statuses = await repo.status_counts(db, site_id)
    kinds = await repo.kind_counts(db, site_id)
    classes = await repo.class_counts(db, site_id, MENTION_CLASSES)
    sentiments = await repo.sentiment_counts(db, site_id)
    kept = await repo.kept_by_query(db, site_id)
    return SummaryResponse(
        unprocessed=statuses.get("fetched", 0) + statuses.get("matched", 0),
        needs_reply=statuses.get("needs_reply", 0),
        drafted=statuses.get("drafted", 0),
        replied=statuses.get("replied", 0),
        skipped=statuses.get("skipped", 0),
        brand_mentions=kinds.get("brand", 0),
        competitor_mentions=kinds.get("competitor", 0),
        last_run=await repo.latest_run(db, site_id),
        kept_by_query=[KeptQueryCount(id=i, text=t, kept=n) for i, t, n in kept],
        mention_classes=MentionClassCounts(
            praise=classes.get("praise", 0),
            complaint=classes.get("complaint", 0),
            feature_request=classes.get("feature_request", 0),
            question=classes.get("question", 0),
            switch_opportunity=classes.get("switch_opportunity", 0),
        ),
        sentiment=SentimentCounts(
            positive=sentiments.get("positive", 0),
            neutral=sentiments.get("neutral", 0),
            negative=sentiments.get("negative", 0),
        ),
    )


async def export_posts(db: AsyncSession, site_id: str, filters: PostFilters):
    if filters.kind is not None and filters.kind not in POST_KINDS:
        raise HTTPException(400, f"kind must be one of {', '.join(POST_KINDS)}.")
    if filters.status is not None and filters.status not in POST_STATUSES:
        raise HTTPException(400, f"status must be one of {', '.join(POST_STATUSES)}.")
    return await repo.all_posts(db, site_id, filters)


async def known_urls(db: AsyncSession, site_id: str, urls: list[str]) -> list[str]:
    cleaned = list(dict.fromkeys(u.strip() for u in urls if u.strip()))
    return await repo.known_urls(db, site_id, cleaned)
