import json
import os
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.core.pagination import PaginatedApiResponse, PaginationParams, PaginationService
from src.notes.models.notes import Note
from src.notes.schemas import NoteEmbedCoverage, NoteHitRecord, NoteListFilters, NoteRecord

MIN_SIMILARITY = float(os.environ.get("MEELU_SEARCH_MIN_SIMILARITY") or 0.82)

RRF_K = 60


def _order(sort: str | None):
    if sort == "updated":
        return Note.updated_at.desc()
    return Note.created_at.desc()


def _conditions(site_id: str, f: NoteListFilters) -> list[Any]:
    conds: list[Any] = [Note.site_id == site_id]
    if f.kinds:
        conds.append(Note.kind.in_(f.kinds))
    if f.contains:
        conds.append(Note.note.ilike(f"%{f.contains}%"))
    if f.created_after is not None:
        conds.append(Note.created_at > f.created_after)
    if f.created_before is not None:
        conds.append(Note.created_at < f.created_before)
    return conds


async def list_notes(
    db: AsyncSession, site_id: str, filters: NoteListFilters, paging: PaginationParams
) -> PaginatedApiResponse[NoteRecord]:
    query = select(Note).where(*_conditions(site_id, filters)).order_by(_order(filters.sort))
    return await PaginationService.paginate_query(
        db, query, paging.page, paging.page_size, NoteRecord
    )


async def get_note(db: AsyncSession, site_id: str, note_id: str) -> NoteRecord | None:
    row = (
        await db.execute(select(Note).where(Note.site_id == site_id, Note.id == note_id))
    ).scalar_one_or_none()
    return None if row is None else NoteRecord.model_validate(row)


async def create_note(
    db: AsyncSession,
    user_id: str,
    site_id: str,
    note: str,
    kind: str,
    embedding: list[float] | None,
    embed_model: str | None,
) -> NoteRecord:
    now = datetime.now(UTC)
    row = Note(
        id=uid("note"),
        user_id=user_id,
        site_id=site_id,
        note=note,
        kind=kind,
        embedding=embedding,
        embed_model=embed_model,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    await db.flush()
    return NoteRecord.model_validate(row)


async def update_note(db: AsyncSession, note_id: str, values: dict[str, Any]) -> NoteRecord:
    row = (
        await db.execute(
            update(Note)
            .where(Note.id == note_id)
            .values(**values, updated_at=datetime.now(UTC))
            .returning(Note)
        )
    ).scalar_one()
    return NoteRecord.model_validate(row)


async def delete_note(db: AsyncSession, note_id: str) -> None:
    await db.execute(delete(Note).where(Note.id == note_id))
    await db.flush()


async def embed_coverage(db: AsyncSession, site_id: str) -> NoteEmbedCoverage:
    row = (
        await db.execute(
            select(
                func.count().label("total"),
                func.count().filter(Note.embedding.is_not(None)).label("done"),
            )
            .select_from(Note)
            .where(Note.site_id == site_id)
        )
    ).one()
    return NoteEmbedCoverage(done=row.done or 0, total=row.total or 0)


_KEYWORD_LEG = """
        select n.id, row_number() over (
                 order by ts_rank_cd(to_tsvector('simple', n.note),
                                     websearch_to_tsquery('simple', :q)) desc
               ) as rank,
               ts_rank_cd(to_tsvector('simple', n.note), websearch_to_tsquery('simple', :q)) as raw
          from notes n
         where n.site_id = :site_id
           and to_tsvector('simple', n.note) @@ websearch_to_tsquery('simple', :q)
           {kind_filter}
         limit :pool
"""

_SEMANTIC_LEG = """
        select n.id, row_number() over (order by n.embedding <=> cast(:vec as vector)) as rank,
               1 - (n.embedding <=> cast(:vec as vector)) as raw
          from notes n
         where n.site_id = :site_id and n.embedding is not null
           and n.embed_model is not distinct from :model
           and 1 - (n.embedding <=> cast(:vec as vector)) >= :min_similarity
           {kind_filter}
         limit :pool
"""

_EMPTY_LEG = "select null::text as id, 0::bigint as rank, 0::float8 as raw where false"

_FUSED = """
    with kw as ({keyword_leg}),
         sem as ({semantic_leg}),
         fused as (
           select id,
                  sum(score) as score,
                  max(similarity) as similarity
             from (
               select id, 1.0 / (:k + rank) as score, null::float8 as similarity from kw
               union all
               select id, 1.0 / (:k + rank) as score, raw as similarity from sem
             ) x where id is not null group by id
         )
    select n.id, n.site_id, n.note, n.kind, n.created_at, n.updated_at,
           f.score, f.similarity
      from fused f
      join notes n on n.id = f.id
     order by f.score desc
     limit :limit
"""


async def search(
    db: AsyncSession,
    site_id: str,
    query: str,
    embedding: list[float] | None,
    *,
    mode: str,
    kind: str | None,
    limit: int,
    model: str | None,
) -> list[NoteHitRecord]:
    want_keyword = mode != "semantic"
    want_semantic = mode != "keyword" and embedding is not None
    kind_filter = "and n.kind = :kind" if kind else ""

    params: dict[str, Any] = {
        "q": query,
        "site_id": site_id,
        "pool": limit * 8,
        "k": RRF_K,
        "limit": limit,
    }
    if kind:
        params["kind"] = kind

    keyword_leg = _KEYWORD_LEG.format(kind_filter=kind_filter) if want_keyword else _EMPTY_LEG

    if want_semantic:
        semantic_leg = _SEMANTIC_LEG.format(kind_filter=kind_filter)
        params["vec"] = json.dumps(embedding)
        params["model"] = model
        params["min_similarity"] = MIN_SIMILARITY
    else:
        semantic_leg = _EMPTY_LEG

    sql = _FUSED.format(keyword_leg=keyword_leg, semantic_leg=semantic_leg)
    rows = (await db.execute(text(sql), params)).mappings().all()
    return [
        NoteHitRecord(
            id=r["id"],
            site_id=r["site_id"],
            note=r["note"],
            kind=r["kind"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
            score=float(r["score"] or 0),
            similarity=None if r["similarity"] is None else float(r["similarity"]),
        )
        for r in rows
    ]
