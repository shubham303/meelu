from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.embed_worker.models import embed_model, embed_texts
from src.seo.constants import CLUSTER_ATTACH_DISTANCE

BATCH = 300

CONTENT_TOP = 3

LEXICAL_WEIGHT = 0.2

PENDING_SQL = """
select id, keyword from seo_keywords
where site_id = :site_id and embedding is null and embed_error is null
order by seq limit :limit
"""

SET_EMBEDDING_SQL = """
update seo_keywords set embedding = cast(:embedding as vector), embed_model = :model,
  updated_at = now()
where id = :id
"""

CONTENT_SQL = f"""
with lang as (
  select language_code from seo_site_state where site_id = :site_id
),
best as (
  select distinct on (c.page_id) c.page_id,
         1 - (c.embedding <=> k.embedding) as similarity
  from seo_keywords k
  join site_chunks c on c.site_id = k.site_id
  join seo_page_facts f on f.page_id = c.page_id
  where k.id = :keyword_id and c.embedding is not null and f.live
    and (f.lang is null or split_part(f.lang, '-', 1) = (select language_code from lang))
  order by c.page_id, similarity desc
),
scored as (
  select b.page_id, b.similarity,
         (position(k.keyword in lower(coalesce(f.title, ''))) > 0
          or position(k.keyword in lower(coalesce(f.h1, ''))) > 0
          or exists (select 1 from unnest(f.headings) h where position(k.keyword in lower(h)) > 0)
         ) as lexical_hit
  from best b
  join seo_keywords k on k.id = :keyword_id
  join seo_page_facts f on f.page_id = b.page_id
)
insert into seo_keyword_content_pages (id, user_id, site_id, keyword_id, page_id, coverage,
  lexical_hit, computed_at)
select 'kcp_' || substr(md5(random()::text || page_id), 1, 10), :user_id, :site_id,
  :keyword_id, page_id,
  least(1.0, similarity * {1 - LEXICAL_WEIGHT} + case when lexical_hit then {LEXICAL_WEIGHT} else 0 end),
  lexical_hit, :started
from scored
order by similarity desc
limit {CONTENT_TOP}
on conflict (keyword_id, page_id) do update set coverage = excluded.coverage,
  lexical_hit = excluded.lexical_hit, computed_at = excluded.computed_at, updated_at = now()
"""

PRUNE_CONTENT_SQL = """
delete from seo_keyword_content_pages
where keyword_id = :keyword_id and computed_at < :started
"""

GSC_COVERAGE_SQL = f"""
with pairs as (
  select g.id, g.page_id from seo_keyword_gsc_pages g where g.keyword_id = :keyword_id
),
best as (
  select p.id, p.page_id,
         (select max(1 - (c.embedding <=> k.embedding)) from site_chunks c
          where c.page_id = p.page_id and c.embedding is not null) as similarity
  from pairs p, seo_keywords k
  where k.id = :keyword_id
),
scored as (
  select b.id, b.similarity,
         (position(k.keyword in lower(coalesce(f.title, ''))) > 0
          or position(k.keyword in lower(coalesce(f.h1, ''))) > 0
          or exists (select 1 from unnest(f.headings) h where position(k.keyword in lower(h)) > 0)
         ) as lexical_hit
  from best b
  join seo_keywords k on k.id = :keyword_id
  left join seo_page_facts f on f.page_id = b.page_id
)
update seo_keyword_gsc_pages g set
  coverage = least(1.0, coalesce(s.similarity, 0) * {1 - LEXICAL_WEIGHT}
                        + case when s.lexical_hit then {LEXICAL_WEIGHT} else 0 end),
  lexical_hit = coalesce(s.lexical_hit, false), updated_at = now()
from scored s where g.id = s.id
"""

ATTACH_SQL = """
update seo_keywords k set cluster_id = n.id, updated_at = now()
from (
  select c.id from seo_keyword_clusters c, seo_keywords k2
  where k2.id = :keyword_id and c.site_id = k2.site_id and c.centroid is not null
    and (c.centroid <=> k2.embedding) <= :distance
  order by c.centroid <=> k2.embedding
  limit 1
) n
where k.id = :keyword_id and k.cluster_id is null
"""


async def embed_pending(db: AsyncSession, user_id: str, site_id: str) -> int:
    done = 0
    while True:
        rows = (
            (await db.execute(text(PENDING_SQL), {"site_id": site_id, "limit": BATCH}))
            .tuples()
            .all()
        )
        if not rows:
            return done
        vectors = await embed_texts([f"query: {keyword}" for _, keyword in rows])
        if vectors is None:
            return done
        model = embed_model()
        for (row_id, _), vector in zip(rows, vectors, strict=True):
            await db.execute(
                text(SET_EMBEDDING_SQL),
                {"id": row_id, "embedding": str(list(vector)), "model": model},
            )
            await refresh_coverage(db, user_id, site_id, row_id)
            done += 1


async def refresh_coverage(db: AsyncSession, user_id: str, site_id: str, keyword_id: str) -> None:
    started = datetime.now(UTC)
    params = {
        "user_id": user_id,
        "site_id": site_id,
        "keyword_id": keyword_id,
        "started": started,
    }
    await db.execute(text(CONTENT_SQL), params)
    await db.execute(text(PRUNE_CONTENT_SQL), {"keyword_id": keyword_id, "started": started})
    await db.execute(text(GSC_COVERAGE_SQL), {"keyword_id": keyword_id})
    await db.execute(
        text(ATTACH_SQL), {"keyword_id": keyword_id, "distance": CLUSTER_ATTACH_DISTANCE}
    )
