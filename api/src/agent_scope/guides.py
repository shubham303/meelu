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

Read freely with SQL. Rejections are the user's standing decisions — never
reject without their instruction, and surface existing rejection reasons
before re-recommending the same fix.
""",
    "pages": """\
## Page corpus

- `site_pages`: one row per crawled URL with everything the crawl parsed.
  Columns: status, title, meta_description, h1, headings, body_text.
  Also out_links, canonical, robots directives, depth, inlinks. Also
  in_sitemap and word_count.
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
  `body_markdown`, `word_count`. `status` is draft, blocked, scheduled, posted
  or failed. `checks` holds the channel's hard-limit findings. `scheduled_at`
  is an hourly slot in the channel's timezone. `posted_at` and `posted_url`
  fill once it went out. The `media_*` fields hold the attached image.
  `parent_piece_id` points at the piece it came from. `source_page_id` points
  at the site page that prompted it.
- `site_channels`: the site's own copy of each channel's writing `rules`,
  `enabled`, `timezone`, `posting_windows` and `min_gap_hours`.
- `content_piece_issues`: findings from the checks run on a piece. The checks
  cover reading ease, overlap with the site's crawled pages, and the AI
  detector. `anchor_text` is the flagged passage word for word. For overlap
  that is the whole paragraph, and `detail` names the page and quotes the
  shared wording. `suggestion` is a proposed fix when the checker had one.
  `state` is open, fixed or dismissed.
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
