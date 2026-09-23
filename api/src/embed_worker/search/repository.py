import json
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

RRF_K = 60
MAX_TEXT_TERMS = 32

_TOKEN = re.compile(r"[^\W\d_]{3,}", re.UNICODE)


def or_tsquery_terms(source: str) -> str:
    seen: dict[str, None] = {}
    for token in _TOKEN.findall(source.lower()):
        if token not in seen:
            seen[token] = None
        if len(seen) >= MAX_TEXT_TERMS:
            break
    return " | ".join(seen)


_TSV = "to_tsvector('simple', coalesce(c.heading_path, '') || ' ' || c.text)"

_KEYWORD_LEG = f"""
    select id, page_id, heading_path, text, raw from (
      select c.id, c.page_id, c.heading_path, c.text,
             ts_rank_cd({_TSV}, {{tsquery}}) as raw,
             row_number() over (
               partition by c.page_id order by ts_rank_cd({_TSV}, {{tsquery}}) desc
             ) as per_page
        from site_chunks c
       where c.site_id = :site_id
         and {_TSV} @@ {{tsquery}}
    ) x where per_page = 1
    order by raw desc
    limit :pool
"""

_SEMANTIC_LEG = """
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

_EMPTY_LEG = """
    select null::text as id, null::text as page_id, null::text as heading_path,
           null::text as text, 0::float8 as raw where false
"""

_FUSED = """
    with kw_hits as ({keyword_leg}),
         kw as (select *, row_number() over (order by raw desc) as rank from kw_hits),
         sem_hits as ({semantic_leg}),
         sem as (select *, row_number() over (order by raw desc) as rank from sem_hits),
         fused as (
           select page_id,
                  sum(score) as score,
                  max(similarity) as similarity,
                  min(keyword_rank) as keyword_rank
             from (
               select page_id, 1.0 / (:k + rank) as score,
                      null::float8 as similarity, rank as keyword_rank from kw
               union all
               select page_id, 1.0 / (:k + rank) as score,
                      raw as similarity, null::bigint as keyword_rank from sem
             ) x where page_id is not null group by page_id
         )
    select f.page_id, p.url, p.title, f.score, f.similarity, f.keyword_rank,
           coalesce(sem.id, kw.id) as chunk_id,
           coalesce(sem.heading_path, kw.heading_path) as heading_path,
           coalesce(sem.text, kw.text) as snippet
      from fused f
      join site_pages p on p.id = f.page_id
      left join sem on sem.page_id = f.page_id
      left join kw on kw.page_id = f.page_id
     order by f.score desc, f.similarity desc nulls last
     limit :limit
"""


async def fused_page_hits(
    db: AsyncSession,
    site_id: str,
    *,
    keyword: str | None,
    keyword_as_terms: bool,
    embedding: list[float] | None,
    model: str | None,
    min_similarity: float,
    pool: int,
    limit: int,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"site_id": site_id, "k": RRF_K, "pool": pool, "limit": limit}

    keyword_leg = _EMPTY_LEG
    if keyword:
        if keyword_as_terms:
            terms = or_tsquery_terms(keyword)
            if terms:
                params["q"] = terms
                keyword_leg = _KEYWORD_LEG.format(tsquery="to_tsquery('simple', :q)")
        else:
            params["q"] = keyword
            keyword_leg = _KEYWORD_LEG.format(tsquery="websearch_to_tsquery('simple', :q)")

    semantic_leg = _EMPTY_LEG
    if embedding is not None:
        params["vec"] = json.dumps(embedding)
        params["model"] = model
        params["min_similarity"] = min_similarity
        semantic_leg = _SEMANTIC_LEG

    if keyword_leg is _EMPTY_LEG and semantic_leg is _EMPTY_LEG:
        return []

    sql = _FUSED.format(keyword_leg=keyword_leg, semantic_leg=semantic_leg)
    rows = (await db.execute(text(sql), params)).mappings().all()
    return [dict(r) for r in rows]


async def chunk_coverage(db: AsyncSession, site_id: str) -> tuple[int, int]:
    row = (
        await db.execute(
            text(
                """
    select count(*) as total, count(embedding) as embedded
      from site_chunks where site_id = :site_id
    """
            ),
            {"site_id": site_id},
        )
    ).one()
    return int(row.total or 0), int(row.embedded or 0)
