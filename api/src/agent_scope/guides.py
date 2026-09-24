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

- `site_search_daily`: one row per (day, query, page) with clicks, impressions,
  position. The grain is query x page x day — aggregate before comparing.
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
- `site_page_links`: one row per link found on a page, and the only place
  link data lives. `src_page_id` is the page holding the link, `dst_url` the
  normalised target, `dst_page_id` the page it resolves to (null for
  external links and for internal targets not in the corpus), `external`
  says which. Also `region` (body, breadcrumb, nav, header, footer, aside,
  pagination — only body links are editorial), `anchor`, `rel`, `count`,
  `followable` and `dst_canonical`.
- `site_chunks`: passages with embeddings behind the site's hybrid search.
- `site`: one row per website. Columns: domain, summary, sitemap_urls,
  gsc_property, last_crawled_at.

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
  job that made it. `action` is 'create', 'delete' or 'edit'; `from_chunk_id`
  points at the `site_chunks` passage the link belongs in, when known;
  `suggestion` is the text a person acts on. `search_score` is the retrieval
  score it was found with, `confidence` the screening model's, `score` the
  importance rank sets (the Structure screen sorts by it).
- `state` is the row's life: 'draft' (saved, not yet screened or ranked),
  'ready' (shown on the Structure screen), 'llm_rejected' (screened, reviewed
  or ranked out; never shown), 'user_rejected' (turned down by the user),
  'done' (the crawl found the link on the page), 'stale' (a page in the edge
  is gone). Unique per (from_page_id, to_page_id, action).
- For `action` 'delete' the edge is a link the crawl found (`from_chunk_id`
  is the passage holding the anchor when it could be located) and
  `search_score` is how related the anchor's passage is to the target: low
  means the link is a stronger removal candidate.
- `pillar_page_suggestions`: one row per proposed pillar page, the same
  `state` values. `action` is 'create' (a new hub) or 'expand'
  (`covering_page_id` partly covers the group already); `member_page_ids`
  are the pages the hub should introduce and link; `topic` and `suggestion`
  are what the reviewer wrote; `search_score` is the group's cohesion.
- `site_page_links` holds the links that exist today. At the start of the
  next job a 'create' suggestion whose edge appears there, a 'delete'
  suggestion whose edge is gone, and a pillar suggestion whose members a
  page newer than it now links are marked done.

Rejections are the user's standing decisions — surface the reason before
re-recommending the same link, and never reject or mark done without their
instruction.
""",
    "seo": """\
## SEO desk tables

- `seo_site_state`: one row per site — locale, `brand_terms`, `ctr_curve`
  (median CTR by rounded position from the site's own non-branded queries),
  and three timestamps: `rollup_at` (Search Console roll-up), `embedded_at`
  (keyword embeddings, coverage and clusters), `precompute_requested_at`.
- `seo_page_facts`: a snapshot of every crawled page the desk reads —
  `page_id` matches `site_pages.id` but rows are never deleted: `live` is
  false when the page is gone or not 2xx, `indexable` when robots allow it.
  Carries title, h1, headings, meta, word count, inlinks, link_score,
  `page_type`, `first_seen_at`, `content_hash`, `is_home`, and the page's own 28-day impressions and clicks.
- `seo_keywords`: the site's keyword universe, unique per `keyword`
  (lowercased). `first_source` says how it entered (gsc, ideas, ranked,
  competitor, serp_paa, serp_related, user). `volume`, `difficulty`, `cpc`,
  `intent` are vendor facts, null until fetched. `branded` matches the site's
  brand terms. Site-wide Search Console counts for the last 28 days, the 28
  before, and the same window last year (`_ly_`, null when no data). 
  `cluster_id` is advisory and reassigned on rebuild; `our_position`/`our_url`
  come from the vendor's ranked-keywords view.
- `seo_keyword_clusters`: keyword groups by meaning; `head_keyword_id` is
  the highest-volume member and its text is the cluster's identity;
  `owner_page_id` and `owner_coverage` say which page covers it best.
- `seo_keyword_gsc_pages`: one row per (keyword, page) Search Console
  saw in 90 days — impression-weighted `position`, 28-day and previous
  counts, `ctr`, `ctr_gap` (expected minus actual from the site curve),
  `leader_days_90d` (days this page led the query), `coverage` (how well
  the page's text matches the keyword, 0–1, raw) and `lexical_hit`.
- `seo_keyword_content_pages`: the three pages whose text best matches
  each keyword, same `coverage` meaning.
- `seo_competitors` (state candidate, confirmed, ignored; only confirmed
  feed generators), `seo_competitor_keywords`, `seo_serp_snapshots` +
  `seo_serp_results`: filled by collect tools; empty until they run.
- `seo_jobs`: one row per prompt run; `vendor_micros` against
  `vendor_ceiling_micros` is the job's spend.
- `seo_page_suggestions`: the output. `action` add, edit or delete;
  `page_id` null for add; `topic_key` is the head keyword text the row is
  about (page-level edits use the page's leading query's head);
  `strategies` lists every generator that produced or re-hit it;
  `evidence` is display-only; `pair_id` links a cannibalisation edit to its
  delete; `merge_into_page_id` on a delete. `state`: draft (saved, not
  screened), reviewed (judge kept it, not yet ranked), ready (on the SEO
  screen), llm_rejected (screen, review or rank dropped it), user_rejected
  (turned down by the user; permanent), done, stale (set by reconcile at
  job start). Unique per (action, page_id, topic_key); a new draft on a
  live row appends its strategy instead of duplicating.
- `seo_page_suggestion_keywords`: the evidence keywords per suggestion.

## Generator filters (service code, every caller)

- Branded keywords are excluded. Only live, indexable pages get edits.
- gsc edits: position 4–20, impressions above the floor, coverage below
  0.55 with no lexical hit. ctr edits: position ≤10, `ctr_gap × impressions`
  in the site's top quarter. questions: question-form queries at 5–20, at
  least three per page. decay: clicks down 30%
  against the previous window (and last year when known), both windows
  above the impressions floor. cluster: owner page missing members with
  volume.
- cannibalisation: two live pages both led the same query ≥10 days of 90,
  shared impressions above the floor, compatible page types. The stronger
  page (clicks, inlinks, link_score) gets the edit, the weaker the delete.
  Never deleted: home, money and hub pages, pages with inlinks above the
  site median, pages younger than 90 days, pages with clicks in the last 28
  days. No Search Console data means no deletes at all.
- An add on a topic an owner page of compatible type already covers ≥0.7
  becomes an edit on that page.

## Pipeline

start_seo_job → generators → screen → review (the only step that rewrites
the suggestion; adds with no search snapshot come back as needs_serp and
stay draft) → rank (per-action budgets, pair counts once) →
finish_seo_job. Second runs collide with standing rows: read `collided`
and present the ready rows already there rather than reporting nothing.

## Canned queries

- Top queries: `select keyword, impressions_28d, clicks_28d from
  seo_keywords where site_id = :site and not branded order by
  impressions_28d desc limit 50`.
- A page's queries: `select k.keyword, g.position, g.impressions_28d,
  g.ctr_gap, g.coverage from seo_keyword_gsc_pages g join seo_keywords k
  on k.id = g.keyword_id where g.page_id = :page order by g.impressions_28d
  desc`.
- A job's drafts: `select id, action, page_id, topic_key, search_score
  from seo_page_suggestions where job_id = :job and state = 'draft'`.

Rejections are the user's standing decisions — surface the reason before
re-recommending the same change, and never reject or mark done without
their instruction.
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

- `content_pieces`: one row per piece, each for exactly ONE channel.
  `channel_key` is website, linkedin, twitter, instagram and so on. `title`,
  `body_markdown`, `word_count`. `status` is draft or blocked. `checks` holds
  the channel's hard-limit findings. Meelu never posts a piece; the user
  copies it out themselves. The `media_*` fields hold the attached image.
  `parent_piece_id` points at the piece it came from. `source_page_id` points
  at the site page that prompted it.
- `site_channels`: the site's own copy of each channel's writing `rules` and
  whether it is `enabled`.
- `content_piece_issues`: findings from the checks run on a piece. The checks
  cover reading ease, overlap with the site's crawled pages, and the AI
  detector. `anchor_text` is the flagged passage word for word. For overlap
  that is the whole paragraph, and `detail` names the page and quotes the
  shared wording. `suggestion` is a proposed fix when the checker had one.
  `state` is open, fixed or dismissed.
""",
    "leads": """\
## Lead management

- `lead_campaign`: one standing search per row — `audience` (who to look
  for), `sources` (enabled discovery source keys), `schedule` (daily, weekly
  or null). `status` is active, paused or archived.
- `lead`: one person per row, deduped across the whole site. `fit_score` is
  0-1 against the campaign brief and the site profile; `fit_reason` says why,
  `evidence` holds [{quote, url}] from pages the pipeline actually read.
  `email` is only ever a found address — `email_verified` true means it
  appeared on the lead's own page; `channel_handles` carries platform
  handles. `stage` is the filter funnel: found (raw), qualified (passed the
  fit check), shortlisted (the curated list); `stage_changed_at` tracks
  movement. `campaign_id` null = a one-off manual lead; `note` is the user's
  own "why them".
- `lead_run`: one discovery run per row with per-source `source_stats`
  ({source: {found, qualified, error?}}) and counts.
""",
    "social-listening": """\
## Social listening

- `social_listening_post`: one row per found post, unique by `url` per site.
  `kind` is topic (found by a query, `query_id`), brand or competitor (matched
  a watched name in `matched_targets`). Every fetched post is stored and moves
  through `status`: fetched (saved, awaiting the embedding gate), matched
  (close enough to its query, awaiting the LLM), filtered (dropped by the gate
  or the LLM, `keep_reason` says why), then needs_reply, drafted, replied or
  skipped. `similarity` is the 0-1 cosine score against the query embedding;
  `relevance` and `composite_score` are the LLM's 0-1 verdicts. `intent` is
  seeking_tool, seeking_help, complaining, recommending, praising, discussion
  or other; `sentiment` is positive, neutral or negative. `classes` holds
  mention labels: praise, complaint, feature_request, question,
  switch_opportunity. `suggested_angle` is the agent's reply angle,
  `reply_text` the user's own words. `run_id` points at the run that found it.
- `social_listening_query`: the sentences the user wants to listen for.
  `enabled` gates one; `source` is user or suggested; `keywords` and
  `negative_keywords` are the search terms the run expanded it into;
  `embedding` is what posts are gated against.
- `social_listening_target`: watched names, `kind` brand or competitor,
  `source` user, profile or suggested.
- `social_listening_config`: one row per site — the `platforms` list, run
  limits, `min_similarity` for the gate, `min_relevance` for the LLM,
  `schedule`.
- `social_listening_run`: one row per run with per-platform `platform_stats`
  ({platform: {fetched, kept, error?}}), counts and terminal status.
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
