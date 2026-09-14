# Search-data API reference

The routes under `dashboard/src/app/api/v1/site/search-data/` expose the Search Console
data stored in `dashboard/src/lib/schema/site/search-console.ts` — three tables:

- `site_search_daily` — one row per (day, query, page) with clicks, impressions and position.
- `site_page_index_status` — per-page indexation state from URL inspection (index state, coverage state, Google's canonical, last crawl time).
- `site_search_syncs` — the lifecycle and progress of each sync run that pulls data from Search Console.

Every route requires an authenticated user and a `siteId`; all data is scoped to that site.
Time-windowed endpoints accept a `days` parameter clamped to 7–480 (default 90) and anchor
the window to the most recent day of stored data, not today.

## Read endpoints — search performance

### GET `/api/v1/site/search-data`

The desk's overview. Exposes: whether a Search Console property is connected and which one,
whether any data is stored and its date coverage (first day, last day, days stored), 28-day
totals for the current and previous window, twelve weeks of weekly click counts, indexation
counts grouped by state (indexed, crawled-not-indexed, …), how many pages were never
inspected, how many pages Google canonicalises elsewhere, a content-quality verdict line
when crawled-not-indexed pages pile up, and the latest / currently active sync.
An `operatingBlind` flag marks sites with too few impressions to reason from.

### GET `/api/v1/site/search-data/series`

Daily time series for charting. Exposes one point per day — clicks, impressions, CTR,
position — over the requested window, plus window totals for the current and previous
period. With `pages` (comma-separated, up to 5) it returns one series per page for
comparison; without it, one site-wide series.

### GET `/api/v1/site/search-data/pages`

Per-page rollup over the window. Exposes one row per page with its search totals and
indexation status, sortable (`clicks`, `delta`, `impressions`, `ctr`, `position`, `page`,
`index`, `crawled`, `inspected`), searchable, and paged with `limit`/`offset` plus a total
count.

With `?url=` it becomes a single-page detail instead: the top queries (up to 100) that page
ranked for in the window.

### GET `/api/v1/site/search-data/queries`

Per-query rollup over the window. Exposes one row per query with its totals, paged and
searchable. `view=top` (default, 90 days) lists the biggest queries; `view=striking`
(28 days) lists striking-distance opportunities. `pages` (up to 5) narrows the rollup to
queries hitting those pages.

### GET `/api/v1/site/search-data/changes`

Movers over the window (default 90 days). Exposes two lists — pages trending `up` and
`down` — comparing the current window against the previous one.

### GET `/api/v1/site/search-data/inspections`

Work queue for URL inspection. Exposes the list of page URLs most worth inspecting next
(`limit`, default 300) — pages that were never checked or are stalest.

## Write endpoints — fed by the app's sync worker

### POST `/api/v1/site/search-data/rows`

Bulk ingestion of daily performance rows. Accepts `days: [{ day, rows }]` (at most 31 days
per batch); each day's rows replace what was stored for that day in `site_search_daily`.
Returns how many days and rows were stored.

### POST `/api/v1/site/search-data/inspections`

Ingestion of URL-inspection results. Accepts `inspections: [...]` with per-URL verdict,
coverage state, Google canonical and last crawl time; upserts them into
`site_page_index_status`. Returns how many were applied.

### POST `/api/v1/site/search-data/property`

Sets which Search Console property this site reads from. Stores it on the website record
and returns the cleaned property string.

## Sync-job endpoints — over `site_search_syncs`

### GET `/api/v1/site/search-data/sync-jobs`

Exposes `{ latest, active }` — the most recent sync run and the one currently queued or
running (null when idle).

### POST `/api/v1/site/search-data/sync-jobs`

Starts a sync. Returns 202 with the new queued sync, or 409 with the already-active one
when a sync is running. Stalled syncs that stopped heartbeating are reaped first.

### GET `/api/v1/site/search-data/sync-jobs/[id]`

One sync run by id: status, trigger, property, timestamps, progress counters (days done /
total, rows stored, pages inspected), date range covered, error and notes.

### POST `/api/v1/site/search-data/sync-jobs/[id]/claim`

The worker claims a queued sync and receives its plan: the property and domain, the date
range to fetch (16-month backfill window, ending 3 days ago to allow for GSC lag), the
resume point when earlier days are already stored, and the total day count.

### PATCH `/api/v1/site/search-data/sync-jobs/[id]`

Progress reporting from the worker. Accepts updated counters, an optional property, and a
terminal status (`completed`, `failed`, `cancelled`) with error and notes; every call
refreshes the heartbeat. Returns the updated sync.
