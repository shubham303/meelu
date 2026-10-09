import json
from datetime import UTC, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Integer, bindparam, cast, delete, func, insert, select, text, update
from sqlalchemy.dialects.postgresql import ARRAY, TEXT
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.ids import uid
from src.site_pages.models.site_chunk import SiteChunk
from src.site_pages.schemas import ChunkCounts, ChunkHit, PhraseHit, SiteChunkRecord

EMBEDDING_DIMENSIONS = 384
MAX_ERROR_CHARS = 500

CHUNK_COLUMNS = (
    SiteChunk.id,
    SiteChunk.site_id,
    SiteChunk.page_id,
    SiteChunk.ordinal,
    SiteChunk.heading_path,
    SiteChunk.text,
    SiteChunk.embed_model,
    SiteChunk.embed_attempts,
    SiteChunk.embed_error,
    SiteChunk.from_hash,
    SiteChunk.created_at,
    SiteChunk.updated_at,
)

TSV_SQL = "to_tsvector('simple', coalesce(c.heading_path, '') || ' ' || c.text)"

KEYWORD_HITS_SQL = f"""
    select id, page_id, heading_path, text, raw from (
      select c.id, c.page_id, c.heading_path, c.text,
             ts_rank_cd({TSV_SQL}, {{tsquery}}) as raw,
             row_number() over (
               partition by c.page_id order by ts_rank_cd({TSV_SQL}, {{tsquery}}) desc
             ) as per_page
        from site_chunks c
       where c.site_id = :site_id
         and {TSV_SQL} @@ {{tsquery}}
    ) x where per_page = 1
    order by raw desc
    limit :pool
"""

SEMANTIC_HITS_SQL = """
    select id, page_id, heading_path, text, raw from (
      select c.id, c.page_id, c.heading_path, c.text,
             1 - (c.embedding <=> cast(:vec as vector)) as raw,
             row_number() over (
               partition by c.page_id order by c.embedding <=> cast(:vec as vector)
             ) as per_page
        from site_chunks c
       where c.site_id = :site_id
         and c.embedding is not null
         and c.embed_model is not distinct from cast(:model as text)
         and 1 - (c.embedding <=> cast(:vec as vector)) >= :min_similarity
    ) x where per_page = 1
    order by raw desc
    limit :pool
"""

FIRST_IDS_CONTAINING_SQL = text(
    """
    select distinct on (i.page_id, i.needle) i.page_id, i.needle, c.id
    from unnest(cast(:page_ids as text[]), cast(:needles as text[])) as i(page_id, needle)
    join site_chunks c
      on c.site_id = :site_id and c.page_id = i.page_id and c.text ilike '%' || i.needle || '%'
    order by i.page_id, i.needle, c.ordinal
    """
).bindparams(bindparam("page_ids", type_=ARRAY(TEXT)), bindparam("needles", type_=ARRAY(TEXT)))

PHRASE_HITS_SQL = text(
    """
    with needles as (
      select * from unnest(cast(:keys as text[]), cast(:phrases as text[]))
        with ordinality as n(key, phrase, rank)
    ),
    excluded as (
      select * from unnest(cast(:excluded_keys as text[]), cast(:excluded_pages as text[]))
        as e(key, page_id)
    ),
    hits as (
      select distinct on (n.key, c.page_id) n.key, c.page_id, c.id as chunk_id, n.phrase, n.rank
        from needles n
        join site_chunks c
          on c.site_id = :site_id
         and c.text ilike '%' || replace(replace(replace(n.phrase, '\\', '\\\\'),
                                         '%', '\\%'), '_', '\\_') || '%'
       where not exists (
         select 1 from excluded e where e.key = n.key and e.page_id = c.page_id
       )
       order by n.key, c.page_id, n.rank, c.ordinal
    ),
    ranked as (
      select *, row_number() over (partition by key order by rank, page_id) as slot
        from hits
    )
    select key, page_id, chunk_id, phrase from ranked
     where slot <= :limit_per_key
     order by key, slot
    """
).bindparams(
    bindparam("keys", type_=ARRAY(TEXT)),
    bindparam("phrases", type_=ARRAY(TEXT)),
    bindparam("excluded_keys", type_=ARRAY(TEXT)),
    bindparam("excluded_pages", type_=ARRAY(TEXT)),
)

CHUNK_PAGE_SIMILARITY_SQL = text(
    """
    with pairs as (
      select * from unnest(cast(:chunk_ids as text[]), cast(:page_ids as text[]))
        as p(chunk_id, page_id)
    )
    select p.chunk_id, p.page_id, 1 - min(c.embedding <=> t.embedding) as similarity
      from pairs p
      join site_chunks c on c.id = p.chunk_id and c.site_id = :site_id
                        and c.embedding is not null
      join site_chunks t on t.site_id = :site_id and t.page_id = p.page_id
                        and t.embedding is not null
     group by p.chunk_id, p.page_id
    """
).bindparams(bindparam("chunk_ids", type_=ARRAY(TEXT)), bindparam("page_ids", type_=ARRAY(TEXT)))

PAGE_SIMILARITY_SQL = text(
    """
    with pairs as (
      select * from unnest(cast(:src_ids as text[]), cast(:dst_ids as text[])) as p(src, dst)
    ),
    means as (
      select page_id, avg(embedding) as vector
        from site_chunks
       where site_id = :site_id and embedding is not null
         and page_id = any(cast(:ids as text[]))
       group by page_id
    )
    select p.src, p.dst, 1 - (a.vector <=> b.vector) as similarity
      from pairs p
      join means a on a.page_id = p.src
      join means b on b.page_id = p.dst
    """
).bindparams(
    bindparam("src_ids", type_=ARRAY(TEXT)),
    bindparam("dst_ids", type_=ARRAY(TEXT)),
    bindparam("ids", type_=ARRAY(TEXT)),
)

BEST_PASSAGE_SQL = text(
    """
    with pairs as (
      select * from unnest(cast(:src_ids as text[]), cast(:dst_ids as text[])) as p(src, dst)
    )
    select distinct on (p.src, p.dst) p.src, p.dst, c.id as chunk_id,
           1 - (c.embedding <=> t.embedding) as similarity
      from pairs p
      join site_chunks t on t.site_id = :site_id and t.page_id = p.dst and t.ordinal = 0
                        and t.embedding is not null
      join site_chunks c on c.site_id = :site_id and c.page_id = p.src and c.ordinal > 0
                        and c.embedding is not null
                        and c.embed_model is not distinct from t.embed_model
     order by p.src, p.dst, c.embedding <=> t.embedding, c.ordinal
    """
).bindparams(bindparam("src_ids", type_=ARRAY(TEXT)), bindparam("dst_ids", type_=ARRAY(TEXT)))


class SiteChunkRepository:
    ID_PREFIX = "chk"

    async def list_for_page(
        self, db: AsyncSession, site_id: str, page_id: str
    ) -> list[SiteChunkRecord]:
        rows = await db.execute(
            select(*CHUNK_COLUMNS)
            .where(SiteChunk.site_id == site_id, SiteChunk.page_id == page_id)
            .order_by(SiteChunk.ordinal.asc())
        )
        return [SiteChunkRecord.model_validate(r) for r in rows.mappings()]

    async def list_by_ids(
        self, db: AsyncSession, site_id: str, ids: list[str]
    ) -> list[SiteChunkRecord]:
        if not ids:
            return []
        rows = await db.execute(
            select(*CHUNK_COLUMNS).where(SiteChunk.site_id == site_id, SiteChunk.id.in_(set(ids)))
        )
        return [SiteChunkRecord.model_validate(r) for r in rows.mappings()]

    async def page_id_of(self, db: AsyncSession, site_id: str, chunk_id: str) -> str | None:
        return (
            await db.execute(
                select(SiteChunk.page_id).where(
                    SiteChunk.site_id == site_id, SiteChunk.id == chunk_id
                )
            )
        ).scalar_one_or_none()

    async def counts(self, db: AsyncSession, site_id: str) -> ChunkCounts:
        row = (
            (
                await db.execute(
                    select(
                        cast(func.count(), Integer).label("total"),
                        cast(func.count().filter(SiteChunk.embedding.is_not(None)), Integer).label(
                            "embedded"
                        ),
                        cast(
                            func.count().filter(SiteChunk.embed_error.is_not(None)), Integer
                        ).label("failed"),
                    )
                    .select_from(SiteChunk)
                    .where(SiteChunk.site_id == site_id)
                )
            )
            .mappings()
            .one()
        )
        return ChunkCounts.model_validate(dict(row))

    async def first_ids_containing(
        self, db: AsyncSession, site_id: str, items: list[tuple[str, str]]
    ) -> dict[tuple[str, str], str]:
        wanted = sorted({(page_id, needle) for page_id, needle in items if needle})
        if not wanted:
            return {}
        rows = await db.execute(
            FIRST_IDS_CONTAINING_SQL,
            {
                "site_id": site_id,
                "page_ids": [page_id for page_id, _ in wanted],
                "needles": [needle for _, needle in wanted],
            },
        )
        return {(r.page_id, r.needle): r.id for r in rows}

    async def phrase_hits(
        self,
        db: AsyncSession,
        site_id: str,
        needles: list[tuple[str, str]],
        excluded: list[tuple[str, str]],
        limit_per_key: int,
    ) -> list[PhraseHit]:
        if not needles:
            return []
        rows = await db.execute(
            PHRASE_HITS_SQL,
            {
                "site_id": site_id,
                "keys": [key for key, _ in needles],
                "phrases": [phrase for _, phrase in needles],
                "excluded_keys": [key for key, _ in excluded],
                "excluded_pages": [page_id for _, page_id in excluded],
                "limit_per_key": limit_per_key,
            },
        )
        return [PhraseHit.model_validate(dict(r)) for r in rows.mappings()]

    async def keyword_hits(
        self, db: AsyncSession, site_id: str, query: str, as_terms: bool, pool: int
    ) -> list[ChunkHit]:
        tsquery = "to_tsquery('simple', :q)" if as_terms else "websearch_to_tsquery('simple', :q)"
        rows = await db.execute(
            text(KEYWORD_HITS_SQL.format(tsquery=tsquery)),
            {"site_id": site_id, "q": query, "pool": pool},
        )
        return [ChunkHit.model_validate(dict(r)) for r in rows.mappings()]

    async def semantic_hits(
        self,
        db: AsyncSession,
        site_id: str,
        vector: list[float],
        model: str | None,
        min_similarity: float,
        pool: int,
    ) -> list[ChunkHit]:
        rows = await db.execute(
            text(SEMANTIC_HITS_SQL),
            {
                "site_id": site_id,
                "vec": json.dumps(vector),
                "model": model,
                "min_similarity": min_similarity,
                "pool": pool,
            },
        )
        return [ChunkHit.model_validate(dict(r)) for r in rows.mappings()]

    async def chunk_page_similarities(
        self, db: AsyncSession, site_id: str, pairs: list[tuple[str, str]]
    ) -> dict[tuple[str, str], float]:
        if not pairs:
            return {}
        rows = await db.execute(
            CHUNK_PAGE_SIMILARITY_SQL,
            {
                "site_id": site_id,
                "chunk_ids": [p[0] for p in pairs],
                "page_ids": [p[1] for p in pairs],
            },
        )
        return {(r.chunk_id, r.page_id): float(r.similarity) for r in rows}

    async def page_similarities(
        self, db: AsyncSession, site_id: str, pairs: list[tuple[str, str]]
    ) -> dict[tuple[str, str], float]:
        if not pairs:
            return {}
        rows = await db.execute(
            PAGE_SIMILARITY_SQL,
            {
                "site_id": site_id,
                "src_ids": [p[0] for p in pairs],
                "dst_ids": [p[1] for p in pairs],
                "ids": list({i for p in pairs for i in p}),
            },
        )
        return {(r.src, r.dst): float(r.similarity) for r in rows}

    async def best_passages(
        self, db: AsyncSession, site_id: str, pairs: list[tuple[str, str]]
    ) -> dict[tuple[str, str], tuple[str, float]]:
        if not pairs:
            return {}
        rows = await db.execute(
            BEST_PASSAGE_SQL,
            {
                "site_id": site_id,
                "src_ids": [p[0] for p in pairs],
                "dst_ids": [p[1] for p in pairs],
            },
        )
        return {(r.src, r.dst): (r.chunk_id, float(r.similarity)) for r in rows}

    async def page_vectors(self, db: AsyncSession, site_id: str) -> dict[str, list[float]]:
        rows = await db.execute(
            select(
                SiteChunk.page_id,
                func.avg(SiteChunk.embedding, type_=Vector(EMBEDDING_DIMENSIONS)).label("vector"),
            )
            .where(SiteChunk.site_id == site_id, SiteChunk.embedding.is_not(None))
            .group_by(SiteChunk.page_id)
        )
        return {r.page_id: [float(v) for v in r.vector] for r in rows}

    async def best_similarity_by_page(
        self,
        db: AsyncSession,
        site_id: str,
        embedding: list[float],
        page_ids: list[str] | None = None,
        limit: int | None = None,
    ) -> dict[str, float]:
        if page_ids is not None and not page_ids:
            return {}
        similarity = func.max(1 - SiteChunk.embedding.cosine_distance(embedding)).label(
            "similarity"
        )
        conds: list[Any] = [SiteChunk.site_id == site_id, SiteChunk.embedding.is_not(None)]
        if page_ids is not None:
            conds.append(SiteChunk.page_id.in_(set(page_ids)))
        query = (
            select(SiteChunk.page_id, similarity)
            .where(*conds)
            .group_by(SiteChunk.page_id)
            .order_by(similarity.desc())
        )
        if limit is not None:
            query = query.limit(limit)
        rows = await db.execute(query)
        return {r.page_id: float(r.similarity) for r in rows}

    async def mean_embedding(
        self, db: AsyncSession, site_id: str, page_ids: list[str], ordinal: int = 0
    ) -> list[float] | None:
        if not page_ids:
            return None
        found = (
            await db.execute(
                select(func.avg(SiteChunk.embedding, type_=Vector(EMBEDDING_DIMENSIONS))).where(
                    SiteChunk.site_id == site_id,
                    SiteChunk.page_id.in_(set(page_ids)),
                    SiteChunk.ordinal == ordinal,
                    SiteChunk.embedding.is_not(None),
                )
            )
        ).scalar_one_or_none()
        return None if found is None else [float(v) for v in found]

    async def replace_for_page(
        self,
        db: AsyncSession,
        user_id: str,
        site_id: str,
        page_id: str,
        from_hash: str | None,
        chunks: list[dict[str, Any]],
    ) -> int:
        await db.execute(delete(SiteChunk).where(SiteChunk.page_id == page_id))
        if not chunks:
            await db.flush()
            return 0
        now = datetime.now(UTC)
        await db.execute(
            insert(SiteChunk),
            [
                {
                    "id": uid(self.ID_PREFIX),
                    "user_id": user_id,
                    "site_id": site_id,
                    "page_id": page_id,
                    "ordinal": c["ordinal"],
                    "heading_path": c["heading_path"],
                    "text": c["text"],
                    "from_hash": from_hash,
                    "embed_attempts": 0,
                    "created_at": now,
                    "updated_at": now,
                }
                for c in chunks
            ],
        )
        await db.flush()
        return len(chunks)

    async def delete_by_page_ids(self, db: AsyncSession, page_ids: list[str]) -> int:
        if not page_ids:
            return 0
        result = await db.execute(
            delete(SiteChunk).where(SiteChunk.page_id.in_(set(page_ids))).returning(SiteChunk.id)
        )
        return len(result.scalars().all())

    async def list_pending_embeddings(
        self, db: AsyncSession, max_attempts: int, limit: int
    ) -> list[SiteChunkRecord]:
        rows = await db.execute(
            select(*CHUNK_COLUMNS)
            .where(SiteChunk.embedding.is_(None), SiteChunk.embed_attempts < max_attempts)
            .order_by(SiteChunk.embed_attempts.asc(), SiteChunk.seq.asc())
            .limit(limit)
        )
        return [SiteChunkRecord.model_validate(r) for r in rows.mappings()]

    async def write_embedding(
        self,
        db: AsyncSession,
        chunk_id: str,
        from_hash: str | None,
        vector: list[float],
        model: str,
    ) -> None:
        await db.execute(
            update(SiteChunk)
            .where(SiteChunk.id == chunk_id, SiteChunk.from_hash.is_not_distinct_from(from_hash))
            .values(
                embedding=vector,
                embed_model=model,
                embed_error=None,
                updated_at=datetime.now(UTC),
            )
        )
        await db.flush()

    async def mark_embed_failed(
        self, db: AsyncSession, chunk_id: str, message: str
    ) -> tuple[str, int] | None:
        row = (
            await db.execute(
                update(SiteChunk)
                .where(SiteChunk.id == chunk_id)
                .values(
                    embed_attempts=SiteChunk.embed_attempts + 1,
                    embed_error=message[:MAX_ERROR_CHARS],
                    updated_at=datetime.now(UTC),
                )
                .returning(SiteChunk.page_id, SiteChunk.embed_attempts)
            )
        ).first()
        await db.flush()
        return None if row is None else (row.page_id, int(row.embed_attempts))

    async def page_ids_with_unembedded(self, db: AsyncSession, page_ids: list[str]) -> set[str]:
        if not page_ids:
            return set()
        rows = await db.execute(
            select(SiteChunk.page_id)
            .where(SiteChunk.page_id.in_(set(page_ids)), SiteChunk.embedding.is_(None))
            .distinct()
        )
        return set(rows.scalars().all())


site_chunks = SiteChunkRepository()
