GUIDES: dict[str, str] = {
    "workflow": """\
## Analysis workflow

0. Read the user's notes before any task: `SELECT note, kind FROM notes WHERE
   site_id = '...'`. They are standing rules and past corrections; a note that
   contradicts your plan is the answer, not an obstacle.
1. This prompt lists the tables you can query, and their columns, under
   "The database". You need no discovery call before writing SQL.
2. Call `find_plans` before inventing SQL for a non-trivial question. The plan
   library holds vetted approaches for common questions. Read a match with
   `get_plan`. That is faster and safer than deriving the approach yourself.
3. Explore with `run_sql`. Canonical tables are read-only and RLS-filtered to this
   user; always filter site-scoped tables by the current `site_id`.
4. For anything beyond plain SQL, make a working table in your workspace
   schema: `CREATE TABLE my_view AS SELECT ... FROM public.some_table WHERE
   site_id = '...'`. Analytics tools that write columns only run on workspace
   tables.
5. Each result carries the method, a summary, a trust block, a declined
   flag, the values and the metadata. When `declined` is true, report the reason. Never put
   in a number of your own. Always pass the trust level and caveats to the user.
6. Save results the user should keep with the write tools. Workspace tables are
   scratch: useful across a conversation, but not product data.
""",
    "search-data": """\
## Search Console data

- `site_search_daily`: one row per (day, query, page, device) with clicks,
  impressions, position; device is desktop, mobile or tablet. The grain is
  query x page x device x day — aggregate before comparing, and filter or group
  by device when the question is about one of them.
- `site_page_index_status`: per-page indexation state from URL inspection.
- `site_search_syncs`: sync-run bookkeeping; check it before trusting freshness.

Rules that keep answers honest:
- Google publishes with ~3 days of lag and syncs may be behind. Always check the
  actual coverage first (`SELECT min(day), max(day) FROM site_search_daily WHERE
  site_id = '...'`) and anchor any "last N days" window to max(day), not today.
- Compare a window against the previous window of equal length for trend claims.
- CTR = sum(clicks)::float / NULLIF(sum(impressions), 0). Weight average
  position by impressions, not a plain AVG.
- Striking-distance queries sit at positions 8-15 with real impressions.
- With very few impressions site-wide, say the data is too thin to reason from
  rather than reporting percentage swings.
""",
    "technical-seo": """\
## Technical SEO issues

- `site_audit_runs`: one row per audit; the latest run (highest seq) is current.
- `site_issues`: site-level findings, unique per (run, kind).
- `site_page_issues`: per-page findings, joined to `site_pages` via page_id.
- States: 'open' and 'rejected'. Severities: p0 (worst) to p3.
- `issue_type` says where a finding came from: 'static' (the raw HTML the
  crawl fetched), 'desktop' (a JavaScript render at desktop width) or
  'mobile' (a JavaScript render at phone width, the version Google indexes
  from). All three are ordinary issues with the same states; renders are a
  separate, slower job the user starts from the app, one device at a time.
- `site_page_renders`: one row per (page_id, device) — what the page looked
  like after JavaScript (title, canonical, h1, word_count, internal_links,
  schema_types) and runtime signals (console_samples, failed_samples,
  blocked_samples, js_bytes, request_count, third_party_hosts). Mobile rows
  also carry hidden_word_count, hidden_internal_links, viewport_overflow_px
  and small_tap_targets. Compare a row against the raw columns on `site_pages`
  to see what JavaScript changed, and the mobile row against the desktop row
  to see what changes on a phone. No row means the page was never rendered
  on that device, not that it is fine.
- Render rows also carry runtime, link, metadata and network measurements
  (status, visible_word_count, internal_link_urls, canonical_hrefs,
  robots_meta_contents, schema_hashes, images, failed_data_samples,
  mixed_content_active, overlay_coverage and more); the rendering rules
  compare those against the raw crawl columns, and each rendering issue's
  text says which measurement tripped it.

Read freely with SQL. Rejections are the user's standing decisions — never
reject without their instruction, and surface existing rejection reasons
before re-recommending the same fix.
""",
    "pages": """\
## Page corpus

- `site_pages`: one row per crawled URL with everything the crawl parsed.
  Columns: status, title, meta_description, h1, headings, body_text.
  Also canonical, robots directives, depth, inlinks, in_sitemap and
  word_count.
- `site_page_links`: one row per internal link between two crawled pages.
  `src_page_id` is the page holding the link, `dst_page_id` the page it
  points at, `dst_url` that page's url. Also `region` (body, breadcrumb, nav,
  header, footer, aside, pagination — only body links are editorial),
  `anchor`, `rel`, `count`, `followable` and `dst_canonical`. Links to other
  sites are not rows here: they sit on the linking page in
  `site_pages.external_links`, a jsonb array of url, region, rel, anchor,
  count and followable.
- `site_chunks`: passages with embeddings behind the site's hybrid search.
- `site`: one row per website. Columns: domain, summary, markets (country
  codes the site sells to), language, sitemap_urls, gsc_property,
  last_crawled_at.

Rules:
- Questions about crawl facts (which pages 404, which are thin, which nothing
  links to, which the sitemap misses) are SQL filters over site_pages, not a
  walk through body_text. Read body_text only for the handful of pages the
  question is actually about.
- Say when the corpus is stale: site.last_crawled_at dates it, and answering
  from a months-old crawl as though it were current is how this data misleads.
""",
    "structure": """\
## Internal link suggestions

- `structure_jobs`: one row per prompt run, `prompt` is the text that ran,
  `status` is RUNNING, COMPLETED or FAILED.
- `link_suggestions`: one row per proposed change to an internal link,
  from_page_id -> to_page_id, both joined to `site_pages`, `job_id` to the
  job that made it. `action` is 'create' or 'delete'; `from_chunk_id`
  points at the `site_chunks` passage the link belongs in, when known;
  `suggestion` is the text a person acts on. `search_score`, `confidence`
  (the screening model's) and `score` (the importance rank sets; the
  Structure screen sorts by it) are all higher-is-better; NULL means not
  measured yet.
- `state` is the row's life: 'draft' (saved, not yet screened),
  'screening_approved' or 'screening_rejected' (the cheap screen's call),
  'review_approved' (review kept it; shown on the Structure screen),
  'review_rejected' (review dropped it; never shown), 'user_rejected'
  (turned down by the user). Each step reads only the rows the previous
  step approved. Unique per (from_page_id, from_chunk_id, to_page_id,
  action): another chunk may suggest the same link, but a suggestion with
  no chunk blocks every other on that pair.
- For `action` 'delete' the edge is a link the crawl found (`from_chunk_id`
  is the passage holding the anchor when it could be located) and
  `search_score` is how unrelated the anchor's passage is to the target:
  high means a stronger removal candidate.
- `pillar_page_suggestions`: one row per proposed pillar page, the same
  `state` values. `action` is 'create' (a new hub) or 'expand'
  (`covering_page_id` partly covers the group already); `member_page_ids`
  are the pages the hub should introduce and link; `topic` and `suggestion`
  are what the reviewer wrote; `search_score` is the group's cohesion.
  Unique per member set.
- Nothing is marked done. Reconciling deletes a suggestion the site has
  outgrown: a 'create' whose link now exists in `site_page_links`, a
  'delete' whose link is gone, a page on either end gone, a pillar whose
  members mostly left the crawl or that a newer page already links, an
  expand whose covering page is gone. Rank deletes review_approved rows
  that miss a page's link budget, so they can come back later.

Rejections are the user's standing decisions — surface the reason before
re-recommending the same link, and never turn a suggestion down or restore
one without their instruction.
""",
    "notes": """\
## Notes

- `notes`: one row per standing note for the current site. `kind` is 'note'
  (a rule about how the user wants things done) or 'feedback' (a correction
  they already made once).

Read them with SQL before doing any task. A note that contradicts your plan
is the answer, not an obstacle, and the user should never have to say a thing
twice. When this task holds the note write tools: save a note only in the
user's words and with their agreement, fold overlap into the existing note
rather than adding a near-duplicate, and delete a note only when the user
asks or confirms it is stale.
""",
    "content": """\
## Content pieces

- `content_pieces`: one row per piece, and every piece is one web page for
  this site. `title` is the SEO title tag, `h1` the on-page headline,
  `meta_description`, `slug` the proposed URL path, `target_keyword` the one
  query the page is written for, `body_markdown` the text after the H1, and
  `word_count`. `checks` holds the page warnings found on save (title length,
  missing H1 or meta description, a stray H1 in the body, keyword placement).
  Meelu never publishes a piece; the user puts it on the site. The `media_*`
  fields hold the featured image. `source_page_id` points at the site page
  that prompted it.
- `content_piece_issues`: findings from the checks run on a piece. The checks
  cover reading ease, overlap with the site's crawled pages, page rules and
  the AI detector. `anchor_text` is the flagged passage word for word. For
  overlap that is the whole paragraph, and `detail` names the page and quotes
  the shared wording. `suggestion` is a proposed fix when the checker had one.
  `state` is open, fixed or dismissed.
""",
    "social-listening": """\
## Social listening

- `social_listening_post`: every post Meelu has ever seen for the site, never
  deleted, so a run never proposes the same post twice. `post_key` is its
  identity, unique per site: the platform plus its native id
  (`external_id`), or a cleaned URL when the platform gives none.
  `content_hash` catches the same text posted twice. `status` is one of:
  fetched (saved, awaiting the embedding check), matched (close in meaning to
  its query, awaiting the LLM judge), dropped (never shown; `drop_reason` is
  too_old, excluded_word, far_in_meaning, judged_off_topic, dead, duplicate,
  unembeddable or line_removed), then the user's own states: to_reply,
  drafted, replied, skipped, rejected (the user marked it not relevant).
  `similarity` is the 0-1 cosine score against the query; `relevance` and
  `composite_score` are the judge's 0-1 verdicts; `keep_reason` is the
  judge's one-line why; `suggested_angle` is a reply angle; `reply_text` is
  the user's own words. `query_id` is the line that found it, `run_id` the run.
- `social_listening_query`: the lines of plain text the user listens for.
  `enabled` gates one; `source` is user or suggested; `keywords` and
  `negative_keywords` are the search terms the run extracted from it;
  `embedding` is what posts are compared against.
- `social_listening_config`: one row per site: the `platforms` list,
  `strictness` (loose, balanced or strict), `max_age_days`, run limits.
- `social_listening_run`: one row per run (always started by the user) with
  `fetched_count`, `matched_count`, `kept_count`, per-platform
  `platform_stats` and its terminal status.
""",
}


def render_guides(topics: tuple[str, ...]) -> str:
    unknown = [t for t in topics if t not in GUIDES]
    if unknown:
        raise KeyError(f"Unknown guide topics: {unknown}. Known: {sorted(GUIDES)}")
    if not topics:
        return ""
    sections = "\n".join(GUIDES[t] for t in topics)
    return f"\n\n# The data under this desk\n\n{sections}"
