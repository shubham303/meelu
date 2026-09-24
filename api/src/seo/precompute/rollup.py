import json
from datetime import UTC, datetime
from statistics import median

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.seo.constants import CTR_MIN_SAMPLE, IMPRESSIONS_FLOOR

WINDOW_DAYS = 28

LEADER_WINDOW_DAYS = 90

YEAR_DAYS = 365

NORMALIZE_QUERY = r"lower(regexp_replace(btrim(query), '\s+', ' ', 'g'))"

PAGE_FACTS_SQL = f"""
with gsc as (
  select p.id as page_id,
         sum(d.impressions) filter (where d.day > current_date - {WINDOW_DAYS}) as impressions_28d,
         sum(d.clicks) filter (where d.day > current_date - {WINDOW_DAYS}) as clicks_28d,
         sum(d.impressions) filter (where d.day > current_date - {YEAR_DAYS + WINDOW_DAYS}
                                      and d.day <= current_date - {YEAR_DAYS}) as impressions_ly_28d,
         sum(d.clicks) filter (where d.day > current_date - {YEAR_DAYS + WINDOW_DAYS}
                                 and d.day <= current_date - {YEAR_DAYS}) as clicks_ly_28d
  from site_search_daily d
  join site_pages p on p.site_id = d.site_id and p.url = d.page
  where d.site_id = :site_id and d.day > current_date - {YEAR_DAYS + WINDOW_DAYS}
  group by p.id
),
src as (
  select p.id as page_id, p.user_id, p.url, p.status, p.redirect_to, x.page_type, p.lang,
         p.title, p.h1[1] as h1,
         coalesce((select array_agg(h ->> 'text') from jsonb_array_elements(p.headings) h
                   where jsonb_exists(h, 'text')), '{{}}'::text[]) as headings,
         p.meta_description, p.title_pixels, p.word_count, p.inlinks, p.link_score,
         p.published_at, p.created_at as first_seen_at, p.content_hash,
         (p.status between 200 and 299 and not p.blocked_by_robots
            and coalesce(p.robots_directives, '') not ilike '%noindex%'
            and coalesce(p.x_robots_tag, '') not ilike '%noindex%') as indexable,
         (p.status between 200 and 299 and not p.blocked_by_robots) as live,
         (regexp_replace(p.url, '^[a-z]+://[^/]+', '') in ('', '/')) as is_home,
         coalesce(g.impressions_28d, 0) as impressions_28d,
         coalesce(g.clicks_28d, 0) as clicks_28d,
         g.impressions_ly_28d, g.clicks_ly_28d
  from site_pages p
  left join site_page_llm_extraction x on x.page_id = p.id
  left join gsc g on g.page_id = p.id
  where p.site_id = :site_id
)
insert into seo_page_facts (id, user_id, site_id, page_id, url, status, redirect_to, page_type,
  lang, title, h1, headings, meta_description, title_pixels, word_count, inlinks,
  link_score, published_at, first_seen_at, content_hash, indexable, live,
  is_home, impressions_28d, clicks_28d, impressions_ly_28d, clicks_ly_28d)
select 'pf_' || substr(md5(random()::text || page_id), 1, 10), user_id, :site_id, page_id, url,
  status, redirect_to, page_type, lang, title, h1, headings, meta_description,
  title_pixels, word_count, inlinks, link_score, published_at, first_seen_at, content_hash,
  indexable, live, is_home, impressions_28d, clicks_28d,
  impressions_ly_28d, clicks_ly_28d
from src
on conflict (page_id) do update set
  url = excluded.url, status = excluded.status, redirect_to = excluded.redirect_to,
  page_type = excluded.page_type, lang = excluded.lang,
  title = excluded.title, h1 = excluded.h1, headings = excluded.headings,
  meta_description = excluded.meta_description, title_pixels = excluded.title_pixels,
  word_count = excluded.word_count, inlinks = excluded.inlinks, link_score = excluded.link_score,
  published_at = excluded.published_at,
  first_seen_at = coalesce(seo_page_facts.first_seen_at, excluded.first_seen_at),
  content_hash = excluded.content_hash,
  indexable = excluded.indexable, live = excluded.live, is_home = excluded.is_home,
  impressions_28d = excluded.impressions_28d, clicks_28d = excluded.clicks_28d,
  impressions_ly_28d = excluded.impressions_ly_28d, clicks_ly_28d = excluded.clicks_ly_28d,
  updated_at = now()
"""

RETIRE_PAGES_SQL = """
update seo_page_facts f set live = false, indexable = false, updated_at = now()
where f.site_id = :site_id and f.live
  and not exists (select 1 from site_pages p where p.id = f.page_id)
"""

INSERT_KEYWORDS_SQL = f"""
insert into seo_keywords (id, user_id, site_id, keyword, first_source)
select 'kw_' || substr(md5(random()::text || q), 1, 10), :user_id, :site_id, q, 'gsc'
from (
  select {NORMALIZE_QUERY} as q, sum(impressions) as impressions
  from site_search_daily
  where site_id = :site_id and day > current_date - {WINDOW_DAYS}
  group by 1
) s
where impressions >= :floor and q <> ''
on conflict (site_id, keyword) do nothing
"""

KEYWORD_COUNTS_SQL = f"""
with agg as (
  select {NORMALIZE_QUERY} as q,
         sum(impressions) filter (where day > current_date - {WINDOW_DAYS}) as i28,
         sum(clicks) filter (where day > current_date - {WINDOW_DAYS}) as c28,
         sum(impressions) filter (where day > current_date - {2 * WINDOW_DAYS}
                                    and day <= current_date - {WINDOW_DAYS}) as ip,
         sum(clicks) filter (where day > current_date - {2 * WINDOW_DAYS}
                               and day <= current_date - {WINDOW_DAYS}) as cp,
         sum(impressions) filter (where day > current_date - {YEAR_DAYS + WINDOW_DAYS}
                                    and day <= current_date - {YEAR_DAYS}) as ily,
         sum(clicks) filter (where day > current_date - {YEAR_DAYS + WINDOW_DAYS}
                               and day <= current_date - {YEAR_DAYS}) as cly
  from site_search_daily
  where site_id = :site_id and day > current_date - {YEAR_DAYS + WINDOW_DAYS}
  group by 1
)
update seo_keywords k set
  impressions_28d = coalesce(a.i28, 0), clicks_28d = coalesce(a.c28, 0),
  impressions_prev_28d = coalesce(a.ip, 0), clicks_prev_28d = coalesce(a.cp, 0),
  impressions_ly_28d = case when :has_ly then coalesce(a.ily, 0) end,
  clicks_ly_28d = case when :has_ly then coalesce(a.cly, 0) end,
  updated_at = now()
from agg a
where k.site_id = :site_id and k.keyword = a.q
"""

HAS_LAST_YEAR_SQL = f"""
select exists (
  select 1 from site_search_daily
  where site_id = :site_id and day <= current_date - {YEAR_DAYS}
)
"""

KEYWORD_PAGES_SQL = f"""
with daily as (
  select {NORMALIZE_QUERY} as q, d.page, d.day, d.clicks, d.impressions, d.position
  from site_search_daily d
  where d.site_id = :site_id and d.day > current_date - {YEAR_DAYS + WINDOW_DAYS}
),
leaders as (
  select q, page, count(*) as leader_days
  from (
    select q, page, day,
           row_number() over (partition by q, day order by impressions desc, page) as rn
    from daily where day > current_date - {LEADER_WINDOW_DAYS}
  ) r
  where rn = 1
  group by q, page
),
pairs as (
  select q, page,
         sum(impressions) filter (where day > current_date - {WINDOW_DAYS}) as i28,
         sum(clicks) filter (where day > current_date - {WINDOW_DAYS}) as c28,
         sum(position * impressions) filter (where day > current_date - {WINDOW_DAYS}) as pw,
         sum(impressions) filter (where day > current_date - {2 * WINDOW_DAYS}
                                    and day <= current_date - {WINDOW_DAYS}) as ip,
         sum(clicks) filter (where day > current_date - {2 * WINDOW_DAYS}
                               and day <= current_date - {WINDOW_DAYS}) as cp,
         sum(impressions) filter (where day > current_date - {YEAR_DAYS + WINDOW_DAYS}
                                    and day <= current_date - {YEAR_DAYS}) as ily,
         sum(clicks) filter (where day > current_date - {YEAR_DAYS + WINDOW_DAYS}
                               and day <= current_date - {YEAR_DAYS}) as cly,
         sum(impressions) filter (where day > current_date - {LEADER_WINDOW_DAYS}) as i90
  from daily
  group by q, page
)
insert into seo_keyword_gsc_pages (id, user_id, site_id, keyword_id, page_id, position,
  impressions_28d, clicks_28d, impressions_prev_28d, clicks_prev_28d, impressions_ly_28d,
  clicks_ly_28d, ctr, leader_days_90d, computed_at)
select 'kgp_' || substr(md5(random()::text || k.id || p.id), 1, 10), :user_id, :site_id,
  k.id, p.id,
  case when coalesce(x.i28, 0) > 0 then x.pw / x.i28 end,
  coalesce(x.i28, 0), coalesce(x.c28, 0), coalesce(x.ip, 0), coalesce(x.cp, 0),
  case when :has_ly then coalesce(x.ily, 0) end,
  case when :has_ly then coalesce(x.cly, 0) end,
  case when coalesce(x.i28, 0) > 0 then x.c28::real / x.i28 end,
  coalesce(l.leader_days, 0), :started
from pairs x
join seo_keywords k on k.site_id = :site_id and k.keyword = x.q
join site_pages p on p.site_id = :site_id and p.url = x.page
left join leaders l on l.q = x.q and l.page = x.page
where coalesce(x.i90, 0) > 0
on conflict (keyword_id, page_id) do update set
  position = excluded.position, impressions_28d = excluded.impressions_28d,
  clicks_28d = excluded.clicks_28d, impressions_prev_28d = excluded.impressions_prev_28d,
  clicks_prev_28d = excluded.clicks_prev_28d, impressions_ly_28d = excluded.impressions_ly_28d,
  clicks_ly_28d = excluded.clicks_ly_28d, ctr = excluded.ctr,
  leader_days_90d = excluded.leader_days_90d, computed_at = excluded.computed_at,
  updated_at = now()
"""

PRUNE_KEYWORD_PAGES_SQL = """
delete from seo_keyword_gsc_pages g
where g.site_id = :site_id and g.computed_at < :started
"""

BRANDED_SQL = """
update seo_keywords k set branded = exists (
  select 1 from unnest(cast(:terms as text[])) t where k.keyword like '%' || t || '%'
), updated_at = now()
where k.site_id = :site_id
"""

CTR_ROWS_SQL = """
select g.id, g.position, g.ctr, g.impressions_28d
from seo_keyword_gsc_pages g
join seo_keywords k on k.id = g.keyword_id
where g.site_id = :site_id and g.position is not null and g.ctr is not null
  and not k.branded and g.impressions_28d >= :floor
"""

MARK_ROLLUP_SQL = """
update seo_site_state set rollup_at = :now, ctr_curve = cast(:curve as jsonb), updated_at = :now
where site_id = :site_id
"""


def ctr_curve(rows: list[tuple[str, float, float, int]]) -> dict[str, float]:
    by_position: dict[int, list[float]] = {}
    for _, position, ctr, _ in rows:
        by_position.setdefault(max(1, round(position)), []).append(ctr)
    return {
        str(pos): float(median(values))
        for pos, values in sorted(by_position.items())
        if len(values) >= CTR_MIN_SAMPLE
    }


def expected_ctr(curve: dict[str, float], position: float) -> float | None:
    if not curve:
        return None
    known = sorted((int(k), v) for k, v in curve.items())
    target = max(1, round(position))
    nearest = min(known, key=lambda kv: (abs(kv[0] - target), kv[0]))
    return nearest[1]


async def refresh_page_facts(db: AsyncSession, site_id: str) -> int:
    result = await db.execute(text(PAGE_FACTS_SQL), {"site_id": site_id})
    await db.execute(text(RETIRE_PAGES_SQL), {"site_id": site_id})
    return result.rowcount or 0


async def rollup_keywords(db: AsyncSession, user_id: str, site_id: str) -> tuple[int, int]:
    started = datetime.now(UTC)
    has_ly = bool((await db.execute(text(HAS_LAST_YEAR_SQL), {"site_id": site_id})).scalar())
    inserted = await db.execute(
        text(INSERT_KEYWORDS_SQL),
        {"user_id": user_id, "site_id": site_id, "floor": IMPRESSIONS_FLOOR},
    )
    await db.execute(text(KEYWORD_COUNTS_SQL), {"site_id": site_id, "has_ly": has_ly})
    pairs = await db.execute(
        text(KEYWORD_PAGES_SQL),
        {"user_id": user_id, "site_id": site_id, "has_ly": has_ly, "started": started},
    )
    await db.execute(text(PRUNE_KEYWORD_PAGES_SQL), {"site_id": site_id, "started": started})
    return inserted.rowcount or 0, pairs.rowcount or 0


async def mark_branded(db: AsyncSession, site_id: str, terms: list[str]) -> None:
    await db.execute(text(BRANDED_SQL), {"site_id": site_id, "terms": terms})


async def refresh_ctr(db: AsyncSession, site_id: str) -> dict[str, float]:
    rows = list(
        (await db.execute(text(CTR_ROWS_SQL), {"site_id": site_id, "floor": IMPRESSIONS_FLOOR}))
        .tuples()
        .all()
    )
    curve = ctr_curve(rows)
    updates = []
    for row_id, position, ctr, _ in rows:
        expected = expected_ctr(curve, position)
        updates.append({"id": row_id, "gap": None if expected is None else expected - ctr})
    if updates:
        await db.execute(
            text("update seo_keyword_gsc_pages set ctr_gap = :gap where id = :id"), updates
        )
    return curve


async def stamp(db: AsyncSession, site_id: str, curve: dict[str, float]) -> datetime:
    now = datetime.now(UTC)
    await db.execute(
        text(MARK_ROLLUP_SQL), {"site_id": site_id, "now": now, "curve": json.dumps(curve)}
    )
    return now
