# RFC — SEO Desk

This is the technical design for `seo-desk-prd.md`. It is a greenfield
rewrite of `api/src/seo`. Nothing is deployed, so we delete the old package
and do not migrate it. A technical review re-verified the platform claims
with file and line evidence, and an adversarial review shaped the rest.

## 0. Verified platform facts, and the two inversions this design makes

These conventions were confirmed in the tree: `EntityMixin` and
`SiteScopedMixin` (`api/src/core/orm.py:21,29`). TEXT by default through the
`type_annotation_map`, with no `sa.Enum` anywhere. `Index(..., unique=True)`
in `__table_args__`, with `postgresql_where` for partial indexes. The
claimable-job pattern: a partial unique index on the active row, plus
`heartbeat_at` and a reap endpoint (`api/src/analysis_jobs/`). The
`x-meelu-scope` header, the registry `WRITE_TOOLS` union, and per-desk write
filtering. RLS grants happen at agent-app startup, so the agent service must
restart after the migration. `settings.agent_data_dir` exists. The e5
embedder with the `query:` prefix and Vector(384) is importable in-process.
It is serialized behind a mutex, which is fine for 500 keywords. The app
poll-loop pattern exists (`app/src/main/rank-schedule.js`), and so does the
harness scope mechanism (`GET /agent/scope` plus the runner).

One caution: CSV download tools are doctrine in CLAUDE.md, but no
implemented example exists. `meelu_site_download_data` appears only in
prose. Our download tools are the first of their kind, so keep them boring.

**Inversion 1 — the vendor client moves to the server.** Today the
DataForSEO client and its Basic-auth credentials live in Electron main
(`app/src/main/providers/seo-data/dataforseo.js`, with credentials entered
in the Connections screen). The `api/src/seo/vendor` package only stores
results. This design's budget, ledger, and cache must be server-side. So
the Connections screen posts credentials to a new api endpoint, api stores
them encrypted at rest with the other site secrets, and api owns all vendor
HTTP. The app-side provider files are deleted.

**Inversion 2 — api gets no scheduler.** api stays request-driven. The only
background process in the repo is the embed worker. All recurring execution
is app-polled: the app loop calls `GET /seo/schedules/due` and
`POST /seo/vendor/tick`, which drives the standard-queue task poller
(§3.2). In-flight vendor tasks survive an app restart, because they are
rows. The next tick collects them.

## 1. Component placement

| Work | Runs in |
|---|---|
| Vendor client, ledger, cache, budget reservation, task-poller state | api |
| Signal battery, calibration, clustering, share of voice, dedupe, queue | api |
| LLM filter job, mission sessions | App (harness) |
| Screens | dashboard `seo/*` |
| Desk tools | Agent server |

## 2. Data architecture: three storage classes

**Facts, free and existing:** `site_search_daily` and `site_traffic_*`.
One caveat: Search Console rows are averaged, so detectors apply the PRD's
gates (brand, dispersion, country, page age). When `site.gsc_property` is
unset, the detectors and measurement that read Search Console are disabled,
and the UI says so. The desk degrades to snapshot-only signals plus the
setup mission. It is never silently empty.

**Dimensions and snapshots, normalized:** see §3.1. A size check for the
JSONB snapshots: 500 keywords × 52 weeks × about 2 to 5 KB is about 50 to
130 MB per year per site, which is fine forever.

**Research pulls, as CSV:** expansions, ranked keywords, and gap matrices
go to `agent_data_dir`, and the Analytics desk ingests them on demand.
Every Labs pull carries an explicit `limit`. Labs is a database that
refreshes about monthly. The guide topic states the rule: never diff Labs
at a faster cadence. Snapshots are truth for current SERPs. Search Console
is truth for our own rankings.

## 3. New api package: `api/src/seo` (rewritten)

Subpackages: `vendor/`, `keywords/`, `serps/`, `competitors/`,
`backlinks/`, `signals/`, `actions/`, `memory/`, and `missions/`, with a
shared `models/`. One flat `tools.py` at the package root imports the
subpackage services, so the registry has a single import point.

### 3.1 Tables (`EntityMixin + SiteScopedMixin`; TEXT plus Literal throughout)

**`seo_markets`** — `location_code INT, language_code TEXT, device TEXT
server_default 'desktop', is_primary BOOL`. A plain unique index on
`(site_id, location_code, language_code, device)`, plus a one-primary
partial unique index. Version 1 ships exactly one row per site. The
multi-market UI comes later, but the foreign key exists from day one. It
is cheap now and painful later.

**`seo_keywords`** — `market_id FK, keyword TEXT, state` (candidate,
tracked, dismissed), `tier` (standard, priority, watch, where watch
carries `watch_until DATE`), `is_branded BOOL, cluster_id FK NULL, source`
(user, gsc, expansion, competitor, agent), `intent TEXT NULL, is_question
BOOL, embedding VECTOR(384) NULL, dismissed_reason`. Unique on `(site_id,
market_id, keyword)`.

**`seo_keyword_metrics`** — the monthly dimension history: `keyword_id FK
CASCADE, month DATE, search_volume INT, cpc NUMERIC, competition REAL,
difficulty INT, serp_item_types JSONB, avg_backlinks_top10 REAL,
volume_trend JSONB`. Unique on `(keyword_id, month)`. Volume and
difficulty refresh monthly. Intent refreshes quarterly, because it rarely
moves.

**`seo_ctr_curves`** — the calibration table, in v0: `bucket` (intent ×
branded × aio_state), `position INT, ctr REAL, sample_impressions BIGINT,
source` (published_prior, calibrated), `computed_at`. Unique on
`(site_id, bucket, position, source)`. The calibration job is SQL over
Search Console observed CTR by rounded position per bucket, with an
impressions floor. Detectors read the calibrated row where the sample is
large enough, and the prior otherwise. The read function resolves this per
bucket and position.

**`seo_clusters`** — `label, head_keyword_id FK NULL, page_id FK NULL`
(to `site_pages`), `method` (serp_overlap, embedding, user),
`overlap_band` (strong means 4 or more shared URLs, weak means exactly 3),
`reclustered_at`.

**`seo_serp_snapshots`** — `keyword_id FK CASCADE, captured_at, item_types
JSONB, results JSONB` (the top-10 typed items), `ai_overview JSONB`
(a present flag plus the references array), `our_position INT NULL,
our_url TEXT NULL, featured_snippet_domain TEXT NULL, se_results_count
BIGINT`. Index on `(keyword_id, captured_at DESC)`, which serves both
latest-per-keyword reads and consecutive diffs.

**`seo_competitors`** — `domain, state` (auto, confirmed, ignored),
`overlap_score REAL, notes`. Gap generation reads `confirmed` rows only.

**`seo_backlink_snapshots`** — `target_domain, month, rank INT, backlinks
BIGINT, referring_domains INT, referring_main_domains INT, new_lost JSONB,
dofollow_ratio REAL`. Unique on `(site_id, target_domain, month)`.
Competitor trendlines come from one monthly `domain_rank_overview` call
per confirmed competitor. That is cheaper than rebuilding the trend from
our own snapshots.

**`seo_actions`** — `kind` (create, update, consolidate, links,
investigate), `target_key TEXT NOT NULL`, which is the deterministic
identity: the page id for page-targeted kinds, and the cluster id or
normalized head keyword for creates. This plain column replaces a
coalesce-expression unique index. Expression indexes have no precedent in
this codebase and Alembic does not autogenerate them reliably. Then:
`target_page_id FK NULL, cluster_id FK NULL, keyword_ids JSONB, title,
rationale, evidence JSONB` (per-signal values, which signals were live,
and a `confidence` field), `expected_tier` (small, medium, large, with
ranges in the evidence), `effort` (s, m, l), `score REAL, state`
(proposed, llm_rejected, accepted, rejected, snoozed, done, measured),
`state_reason, business_fit INT NULL` (NULL means unscored), `run_id FK,
done_at, measure_from, measure_until, measured JSONB`
(difference-in-differences delta against the control set, plus volatility
stamps).
Partial unique index on `(site_id, kind, target_key) WHERE state IN
('proposed','llm_approved','accepted','snoozed')`. Index on `(site_id,
state, score DESC)` for the queue screen. Re-emission suppression:
generation anti-joins targets with `done_at` inside 8 weeks, or with an
open measurement window. Rejection memory per kind: page-scoped for update
and links, lifted on a content-hash change. Page-pair-scoped for
consolidate. Cluster-or-keyword-scoped for create.

State transitions: `proposed → llm_rejected`, or (fit at least 2, or
unscored) `proposed → accepted | rejected | snoozed`. `snoozed → proposed`
at `snooze_until_run`. `accepted → done` by the user. `done → measured` by
a schedule when `measure_until` passes, which is a dueness row (§3.6).
There are no other transitions.

**`seo_vendor_ledger`** — `endpoint, queue_type` (standard, priority,
live), `cost NUMERIC, rows INT, trigger` (schedule, mission, user),
`mission_id FK NULL, request_hash, cached BOOL, task_ref TEXT NULL,
state` (posted, collected, failed). Aggregation rule: sums exclude
`cached` rows.
**`seo_budgets`** — `month, cap_usd, spent_usd, committed_usd`. The
committed column holds in-flight posted tasks. The vendor bills at post
time, so a crash between post and get must not desync us from vendor
billing. Unique on `(site_id, month)`.

**`seo_memory`** — desk memory. The filter reads only the structured
fields: `brand_terms`, `products`, `priorities`, `fit_rules`, and
`competitor_notes`. The `freeform` field is for missions only. Columns:
`field, content, source, updated_at`.

**`seo_signal_runs`** — in-process bookkeeping: `trigger, status,
counters`. It is not claimable and not reaped. The app reaps only
`seo_filter_jobs` (claimable, analysis-job pattern) and stale missions.
**`seo_missions`** — `instruction, template` (setup, research,
competitive, diagnostic, custom), `state` (draft, approved, running,
complete, failed, cancelled), `cap_usd NUMERIC, spent_usd, max_turns INT,
endpoint_ceilings JSONB, result_summary, artifacts JSONB, heartbeat_at`.

### 3.2 Vendor layer (`vendor/`)

`call(endpoint, payload, *, site_id, trigger, mission_id=None)` does:
1. Atomic budget reservation, never read-then-execute:
   `UPDATE seo_budgets SET committed_usd = committed_usd + :est WHERE
   site_id=... AND month=... AND spent_usd + committed_usd + :est <=
   cap_usd RETURNING id`. No row back means a typed refusal. On
   completion, the committed amount moves to spent at the actual cost. On
   failure, it is released. Missions reserve against their own `cap_usd`
   the same way.
2. A cache read by `request_hash`, with per-endpoint lifetimes: Labs 30
   days, volume 30 days, backlinks 30 days. SERPs are never cached,
   because the snapshots are the record. Cache hits write ledger rows with
   `cached=true` and cost 0.
3. Execution. The queue type is pinned per caller: scheduled SERPs use the
   standard queue, and mission SERPs use the priority queue at most. The
   `queue_type` is written to the ledger.

The task poller for the standard queue: `task_post` writes a `posted`
ledger row with a `task_ref` and commits `committed_usd`.
`POST /seo/vendor/tick`, polled by the app in the same loop as the
schedules, lists pending refs, calls `task_get`, stores the results, marks
the rows `collected`, and settles the budget.

The endpoint budget: three metric tasks per site per month (volume at
1,000 keywords per task, difficulty at 700 per task, intent quarterly at
1,000 per task). The weekly SERP batch runs with
`load_async_ai_overview: true`, booked as its own ledger line because it
roughly doubles the per-SERP cost. Backlinks run monthly.
`include_clickstream_data` is never used. It doubles the cost for nothing
we need.

### 3.3 Signal battery (`signals/`)

Shared modules. `curves.py` reads `seo_ctr_curves` and resolves calibrated
rows first, then the prior, per bucket. `gates.py` holds the shared
filters: the branded filter from the memory `brand_terms` plus
`is_branded`; the dispersion gate, where a 28-day daily-position standard
deviation above 3 lowers confidence; the page-age guard, which skips pages
under 90 days everywhere and under 15 months for decay; and the country
filter to the primary market, where the ingested grain allows it. If
`site_search_daily` carries no country dimension, the detectors state that
in their evidence, and confidence drops one grade.

Detectors emit `{kind, target_key, evidence (with confidence),
raw_score}`:
- **striking_distance** — gated Search Console 28 days, position 4.9 to
  15.1, CTR below curve times 0.6, cross-checked against
  `serp_item_types`. Below-curve because a feature sits above is not a
  weak snippet.
- **ctr_gap** — calibrated curves, on tracked keywords with snapshot
  positions.
- **visibility_no_clicks** — impressions up, clicks down, position stable,
  and an AI overview appeared in the snapshot diff.
- **decay** — position stability is ruled out first. The changepoint runs
  on the year-over-year ratio series (clicks divided by clicks one year
  ago, weekly). Implementation note: add `ruptures` to `api/pyproject.toml`
  and call it directly on the ratio array. The `data_analytics`
  `detect_changepoints` wrapper takes a Store or DataFrame, not a plain
  series, and its lazy `ruptures` import currently fails with a stale
  `tabint[insights]` message. Do not route through it.
- **cannibalization** — a per-URL impression floor, no URL above 70%,
  positions crossed, a same-intent check through top-query overlap of both
  URLs, and URL-pattern heuristics that exclude pagination and parameter
  twins. Three or more queries produce consolidate, fewer produce
  investigate.
- **serp_shift** — diffs that persist across 2 snapshots. The priority
  tier gets a next-day confirming SERP, written to the ledger.
- **keyword_gap** (v1.1) — confirmed competitors, inside a cluster or a
  named topic, top N per run.
- **link_deficit** (v1.1) — `referring_main_domains` plus `dofollow_ratio`
  against the top-10 median. A gap of 30 or less produces a links action.
  A larger gap suppresses the expected tier of other actions.
- **rank_alert** (v1.5) — 5 or more positions across 2 or more snapshots.
  The volatility index is the median absolute movement across the tracked
  set that week. A spike produces one informational alert, and individual
  alerts are logged, not raised.

Dedupe runs deterministically before the LLM: group by `target_key`, merge
evidence, take the maximum score. Per-signal-type caps apply per run,
before the global drain. The clustering job runs quarterly: an embedding
agglomerative pass first, then SERP overlap, with 4 or more shared URLs as
strong and exactly 3 as weak. The calibration job recomputes
`seo_ctr_curves` monthly.

### 3.4 LLM filter (app job)

A `seo_filter_jobs` claim returns the candidates, the structured memory
fields only, and per-target Search Console context. Empty or thin memory
completes the job with `business_fit=NULL` (unscored) and makes no model
calls. Otherwise the job makes one schema-constrained call per candidate:
fit 0 to 3 against the anchored rubric. Run-level distribution guards sit
on the job row. More than 90% scored 2 or higher, or more than 70%
rejected, marks the run `flagged`. The queue then falls back to
deterministic order, and the UI says so.

### 3.5 Missions

Missions use an approved-cap model. Estimating the cost of an open-ended
agent plan is not possible. A cap is. The template sets `cap_usd`,
`max_turns`, and `endpoint_ceilings`. The user approves the cap, and the
auto-approve floor covers small ones, for missions only.

The runner wiring has no precedent, so it is specified here. The app poll
loop lists missions with `state=approved`. For each one, it launches a
harness session through the existing scope mechanism, with
`action=seo-mission` and the mission id passed as a query parameter to
`GET /agent/scope`. The endpoint bakes the id into the returned system
prompt and into the scope's MCP headers as `x-meelu-mission`. The agent
server resolves that header exactly like `x-meelu-scope` and hands the
mission id to the purchase tools. The tools validate `state=running` and
reserve against the mission cap. Sessions run through `runAgentTurnOnce`
from the main process, which is its first main-process caller. The chat UI
shows the transcript read-only on the missions screen, not as a live chat
session. The mission row carries a heartbeat, and stale missions are
reaped to `failed`.

The canned setup mission is `template=setup` with a fixed tool plan and a
fixed cap, so pricing it is trivial. It ships in version 1.

### 3.6 Endpoints

CRUD and list per table, plus: `GET /seo/overview`.
`GET /seo/schedules/due` returns typed rows: volume_refresh, serp_check,
backlinks, clustering, calibration, signal_run, measure_close, and
vendor_tick. Dueness is computed from data maxima: `max(month)`,
`max(captured_at)`, `reclustered_at`, `measure_until`, and pending task
refs. There is no schedules table. Also: `POST /seo/runs`, the filter-job
claim, patch, and reap routes,
`POST /seo/actions/{id}/accept|reject|snooze|done`, `POST /seo/missions`
plus `/{id}/approve|cancel`, `POST /seo/vendor/tick`,
`GET /seo/export?dataset=`, `GET/PUT /seo/memory`, `GET/PUT /seo/budget`,
and `POST /seo/credentials` for the vendor credentials from the
Connections screen.

## 4. Deletion list (the blast radius of the rewrite — delete all of it)

- `api/src/app.py:17-29` — the 13 old seo router mounts. Replaced.
- `api/src/agent_scope/registry.py:15` — the old `seo.keywords.tools`
  import. The agent server fails at import the moment the package is
  deleted, so the registry and desks edits land in the same change as the
  package swap.
- `api/src/agent_scope/desks.py:19-50` — about 30 old seo model imports.
- `api/src/agent_scope/seo/` — the old scopes (`ask_seo`,
  `keyword_research`, `plan`, `spec`), replaced by `ask-seo` and
  `seo-mission`. Check `ACTION_ALIASES` in `app/src/main/agent/runner.js`
  for references.
- `api/src/agent_plans/library.py:136,143,284,291` — literal SQL against
  old tables. These break silently at agent runtime, so rewrite the
  entries.
- The seo topic in `api/src/agent/tools/guides.py` — rewrite.
- `dashboard/src/app/dashboard/seo/{findings,intent-map,plan,rank-tracker,
  vitals}`, plus `seo-ask.tsx` and `plan-button.tsx` — deleted or replaced
  by the screens in §5. If page vitals survives at all, it belongs to the
  Site desk.
- `app/src/main/rank-schedule.js` (replaced by the schedules-due loop),
  and `app/src/main/providers/seo-data/dataforseo.js` with its provider
  catalog entries (the client moves server-side).

## 5. Dashboard — `dashboard/src/app/dashboard/seo/`

Overview: the share-of-voice and visibility trends, alerts including the
volatility line, and the budget bar with committed spend and
saved-by-cache. Keywords: the tracked set, tiers, branded flags, and
clusters. Opportunities: the grouped queue with evidence and confidence
visible, accept, reject-with-reason, and snooze, plus banners for
unscored-fit and flagged runs. Competitors: confirm and ignore, with the
gap buckets. AI Visibility: the AI-overview keywords and the citation
timeline. Results (v1.5): difference-in-differences deltas with volatility
stamps. Missions: caps, approval, transcripts, and artifacts.

## 6. Agent server (SEO desk)

- All tables from §3.1 go on the SEO desk. Restart the agent service after
  the migration.
- `api/src/seo/tools.py`, added to the registry import and the
  `WRITE_TOOLS` union:
  - `seo_download_data(dataset)` writes a CSV under `agent_data_dir` and
    returns the path plus a row count.
  - The purchase tools `seo_fetch_serp`, `seo_expand_keywords`, and
    `seo_competitor_pull` are mission-gated through `x-meelu-mission`.
    Row limits are mandatory. The priority queue is the maximum. Each
    returns a CSV path plus the charged cost.
  - The writes: `seo_track_keywords`, `seo_dismiss_keyword`,
    `seo_create_action`, `seo_update_action_state`, and
    `seo_save_memory`.
- The guide topic `seo` covers the grain, the curve caveats, the truth
  rules ("Search Console for our own rankings, snapshots for everyone
  else's, Labs is a monthly database"), and the budget and mission
  protocol. The scopes are `ask-seo` (Ask-shaped) and `seo-mission`.

## 7. Decisions and alternatives

- Snapshots as JSONB documents, not normalized result rows. The reads are
  latest-per-keyword and consecutive-diff only, and the size math in §2
  closes the question. Research goes through CSV export.
- A `target_key` column instead of coalesce-expression unique indexes.
  Expression indexes have no precedent here and do not autogenerate. A
  plain deterministic column is boring and greppable.
- Caps, not estimates, for missions. Open-ended agent plans cannot be
  priced. A cap with a live ledger tells the same trust story, honestly.
- Curves as a calibrated table in v0. Every third detector reads them, and
  published priors alone overpromise. The 2025 curve flattening and the
  intent-variable AI-overview penalties are the evidence.
- An app-polled vendor tick. api stays request-driven like the rest of the
  platform, and in-flight tasks are rows that survive app restarts.
- Delete-and-rewrite with the explicit blast-radius list in §4. The
  registry import alone makes a naive delete take the agent server down.

## 8. Build order

1. **v0, with no vendor code.** Memory and brand terms. `seo_ctr_curves`
   and calibration. The gates. The striking_distance, decay,
   visibility_no_clicks, and cannibalization detectors. Dedupe,
   `seo_actions`, the filter job, and the Opportunities screen. The desk
   tools (download, queue writes, memory). The §4 deletions.
2. The vendor layer: the credentials endpoint, atomic budgets, the ledger,
   the cache, and the tick. Markets. Tracked keywords seeded from Search
   Console, plus the metrics refresh.
3. The SERP snapshot schedule with AI-overview capture. The ctr_gap and
   serp_shift detectors. The canned setup mission, with the full mission
   plumbing: the header, the runner, and the caps.
4. v1.1: clustering, share of voice, competitors, keyword_gap, backlinks,
   and link_deficit.
5. v1.5: general missions, rank alerts with the volatility index, Results
   with difference-in-differences, the watch tier, and the recalibration
   cadence.
