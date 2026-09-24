"""site_page_links is the only home for link data

Revision ID: a1c7f4e93b20
Revises: 9a3a5c9251f5
"""

from alembic import op

revision = "a1c7f4e93b20"
down_revision = "9a3a5c9251f5"
branch_labels = None
depends_on = None

NORM = """coalesce(
  lower(substring(u from '^([A-Za-z][A-Za-z0-9+.-]*://[^/]*)')) ||
  coalesce(substring(u from '^[A-Za-z][A-Za-z0-9+.-]*://[^/]*(/.*)$'), '/'),
  u)"""

REBUILD = f"""
insert into site_page_links
  (id, user_id, site_id, src_page_id, dst_page_id, dst_url, external, region, rel, anchor,
   count, followable, dst_canonical, created_at, updated_at)
select 'spl_' || substr(md5(random()::text || clock_timestamp()::text || src || dst_url || region), 1, 10),
       user_id, site_id, src, null, dst_url, external, region, rel, anchor, count,
       followable, true, now(), now()
  from (
    select p.id as src, p.user_id, p.site_id,
           {NORM} as dst_url,
           external,
           coalesce(nullif(l->>'region', ''), 'body') as region,
           min(l->>'rel') as rel,
           min(l->>'anchor') as anchor,
           sum(greatest(coalesce((l->>'count')::int, 1), 1))::int as count,
           bool_or(coalesce(l->>'rel', '') !~* 'nofollow') as followable
      from site_pages p,
           lateral (
             select l, false as external from jsonb_array_elements(p.out_links) l
             union all
             select l, true as external from jsonb_array_elements(p.external_links) l
           ) links,
           lateral (
             select regexp_replace(regexp_replace(l->>'url', '#.*$', ''), '/+$', '') as u
           ) x
     where l->>'url' is not null and l->>'url' <> ''
     group by p.id, p.user_id, p.site_id, {NORM}, external, coalesce(nullif(l->>'region', ''), 'body')
  ) edges
"""

RESOLVE = """
update site_page_links e
   set dst_page_id = t.id
  from site_pages t
 where not e.external
   and t.site_id = e.site_id
   and regexp_replace(t.url, '/+$', '') = e.dst_url
   and t.id <> e.src_page_id
"""


def upgrade() -> None:
    op.execute("alter table site_page_links add column dst_url text")
    op.execute("alter table site_page_links add column external boolean not null default false")
    op.execute("alter table site_page_links alter column dst_page_id drop not null")
    op.execute("alter table site_page_links drop column weight")
    op.execute("drop index if exists site_page_links_edge_idx")
    op.execute("delete from site_page_links")
    op.execute(REBUILD)
    op.execute(RESOLVE)
    op.execute("alter table site_page_links alter column dst_url set not null")
    op.execute(
        "create unique index site_page_links_edge_idx"
        " on site_page_links (site_id, src_page_id, dst_url, region)"
    )
    op.execute(
        "create index site_page_links_dst_url_idx on site_page_links (site_id, dst_url)"
    )
    op.execute(
        "create index site_page_links_unresolved_idx"
        " on site_page_links (site_id, external, dst_page_id)"
    )

    for column in (
        "out_links",
        "external_links",
        "inbound_anchors",
        "has_viewport",
        "external_link_density",
        "keywords",
        "questions_answered",
        "editorial_inlinks",
        "editorial_score",
    ):
        op.execute(f"alter table site_pages drop column {column}")

    op.execute("alter table site_chunks drop column embedded_from_hash")
    op.execute("alter table site_chunks drop column chunk_strategy")
    op.execute("alter table seo_page_facts drop column questions_answered")


def downgrade() -> None:
    raise NotImplementedError("Link data only lives in site_page_links now.")
