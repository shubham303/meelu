# SEO desk — plan (generators + filter chain, strategies as prompts)

Written 2026-09-20 against the rebuilt structure desk
(`api/src/site_structure`), revised through two review rounds the same day
(structure-code audit, SEO domain, architecture/cost, agent workflow; then
three final reviews). The old SEO desk was deleted on 2026-09-13; nothing
here reuses it. The SEO desk is its own desk: package `api/src/seo`, its own
tables (all prefixed `seo_`), scope, guide and dashboard section. It is not
part of the site desk.

## 0. The one-sentence version

Every prompt on the SEO desk ends in a row of one table,
`seo_page_suggestions`, whose `action` is `add`, `edit` or `delete`. Tools
generate many such rows cheaply, a chain of filters throws most away, and
the user sees only what survives. The strategy — competitor gap,
cannibalisation, striking distance, "content for topic X" — is the prompt.
The tools never encode it.

```
collect ──► precompute ──► generate ──► filters ──► screen ──► review ──► rank ──► user
(vendor,     (api rollup +  (draft)     (in the      (cheap    (judge,    (job-scoped
 GSC, crawl)  worker)                    generator)   choice)   live rows) budget → ready)
```

Recall first, precision from each later step, every step cheaper than the
one after it. A bare LLM reading the site sees no volumes, re-reads the
corpus per question, and has no memory of what it already suggested or what
the user turned down.

## 1. What exists (build on it)

| Capability | Where |
|---|---|
| Vendor data, one server account, cached, credit-charged | `api/src/providers/seo_data` facade. Verified: `ranked_keywords` items carry `keyword_info`/`keyword_properties`/`search_intent_info`; SERP advanced returns `people_also_ask` (question in `items[].title`), `related_searches`, per-result `description`, `item_types`. `keyword_ideas` has no `competition`. |
| Search Console | `site_search_daily(day, query, page, clicks, impressions, position)` |
| Page corpus, page type, chunks | `site_pages`, `site_page_llm_extraction.page_type`, `site_chunks` (e5-small 384, `passage:` prefix). The embedder is loadable in-process (`embed_worker/models.py`); the worker is a psycopg polling loop with no event channel. |
| Cheap choice model / judge model | `providers/json_data_extractor.decide`, `providers/llm_judge.judge` |
| Job, suggestion, revive-on-conflict, `stopped` on no credits, `{inserted, skipped: {reason}}` results, workspace-table bulk input | `site_structure` — copy these |

Structure-desk bugs the audit found; do not inherit them and fix them there:
rank runs site-wide and demotes `ready` rows of earlier jobs; screen/review
with explicit `ids` skip the state filter and overwrite `user_rejected`/
`done`; the provider cache subject omits the suggestion text so a revived
row reuses a stale verdict; one transaction wraps 200 model calls.

## 2. Tables (`api/src/seo/models`, all `EntityMixin + SiteScopedMixin`)

Distilled facts only. Everything generators, filters, review and reconcile
read lives here; the only module that imports another desk's tables is
`api/src/seo/precompute/`. Single locale per site in v1.

### 2.1 `seo_jobs`
`prompt`, `status` (RUNNING, COMPLETED, FAILED), `vendor_calls INT`,
`vendor_micros BIGINT`, `vendor_ceiling_micros BIGINT` (copied from
`settings.SEO_JOB_VENDOR_CEILING_MICROS` at start). A job stays RUNNING
across turns when a user decision is pending and is reused by id;
`start_seo_job` marks any older RUNNING job of the site FAILED.

### 2.2 `seo_site_state`
One row per site: `location_code`, `language_code`, `brand_terms TEXT[]`,
`precompute_requested_at`, `rollup_at`, `embedded_at`, `ctr_curve JSONB`
(`{position: median_ctr}`, non-branded, positions with ≥ `CTR_MIN_SAMPLE`
rows; missing positions interpolate).

### 2.3 `seo_page_facts`
Snapshot of the page fields the desk reads. `page_id` unique, **no FK to
`site_pages`**; a gone page is `live=false`, rows are never deleted.
`url, status, redirect_to, page_type, kind, lang, title, h1, headings
TEXT[], meta_description, title_pixels, word_count, inlinks, link_score,
published_at, first_seen_at, content_hash, questions_answered TEXT[],
indexable, live, is_home, impressions_28d, clicks_28d, impressions_ly_28d,
clicks_ly_28d`.

### 2.4 `seo_keywords`
| column | note |
|---|---|
| `keyword` | normalized text; the identity everything keys on. Unique `(site_id, keyword)` |
| `volume`, `difficulty`, `cpc`, `intent`, `facts_fetched_at` | nullable until fetched |
| `first_source` | `gsc`, `ideas`, `ranked`, `competitor`, `serp_paa`, `serp_related`, `user` |
| `seed_keyword_id` | nullable |
| `cluster_id` | FK `seo_keyword_clusters`, advisory, reassigned on rebuild |
| `branded BOOL` | |
| `our_position`, `our_url` | from `ranked_keywords` for our domain |
| `embedding Vector(384)`, `embed_model`, `embed_error` | `query:` prefix; written at insert time by the api |
| `impressions_28d`, `clicks_28d`, `impressions_prev_28d`, `clicks_prev_28d`, `impressions_ly_28d`, `clicks_ly_28d` | site-wide GSC roll-up |

Indexes `(site_id, cluster_id)`, `(site_id, branded)`, HNSW on `embedding`.

### 2.5 `seo_keyword_clusters`
`head_keyword_id`, `centroid Vector(384)`, `size`, `volume_sum`,
`difficulty_median`, `owner_page_id` (→ `seo_page_facts.page_id`, nullable),
`owner_coverage`, `site_similarity`, `rebuilt_at`. Identity for suggestions
is the head keyword's text, never the row id.

### 2.6 `seo_keyword_gsc_pages`
Per `(keyword_id, page_id)`: `position` (impression-weighted 28d),
`impressions_28d`, `clicks_28d`, `impressions_prev_28d`, `clicks_prev_28d`,
`impressions_ly_28d`, `clicks_ly_28d`, `ctr`, `ctr_gap`, `leader_days_90d`,
`coverage` (raw cosine of the keyword to the page's best chunk, blended
with `lexical_hit`; stored raw, never as a percentile, so "rose" is stable),
`lexical_hit`, `computed_at`. Indexes `(site_id, page_id)`,
`(site_id, keyword_id)`.

### 2.7 `seo_keyword_content_pages`
Top 3 pages per keyword by raw coverage, same language only: `coverage`,
`lexical_hit`, `computed_at`.

### 2.8 `seo_competitors`
`domain`, `brand_terms TEXT[]` (≤8, guessed from the domain, editable on
the tab), `first_source` (`rival`, `serp`, `user`), `intersections`,
`avg_position`, `state` (`candidate`, `confirmed`, `ignored`),
`fetched_at`. Confirmation is a tab action only. Only `confirmed` domains
feed generators.

### 2.9 `seo_competitor_keywords`
`competitor_id`, `keyword_id`, `position`, `url`, `etv`, `fetched_at`.
Unique `(competitor_id, keyword_id)`, index `(keyword_id)`.

### 2.10 `seo_serp_snapshots`, `seo_serp_results`
Snapshots: `keyword_id`, `device`, `fetched_at`, `features TEXT[]`. Latest
3 per `(keyword_id, device)`; the collect tool prunes. Results:
`snapshot_id`, `rank`, `domain`, `url`, `title`, `description`, `is_ours`.
PAA questions and related searches become `seo_keywords` rows
(`first_source = serp_paa|serp_related`, `seed_keyword_id` = the snapshot's
keyword). Never pass `stop_on_domain` (it truncates the top 10).

### 2.11 `seo_page_suggestions`
| column | note |
|---|---|
| `job_id` | FK `seo_jobs` |
| `action` | `add`, `edit`, `delete` |
| `page_id` | → `seo_page_facts.page_id`, null for `add` |
| `topic_key` | normalized head-keyword text of the evidence cluster. For page-level edits (ctr, decay, questions) it is the cluster head of the page's leading query by impressions. For a cannibalisation pair it is the cluster head of the shared queries; one pair per (strong, weak) page pair |
| `cluster_id` | advisory |
| `pair_id` | self-FK linking the two rows of a cannibalisation pair |
| `merge_into_page_id` | required for `delete` |
| `strategies TEXT[]` | every generator that produced or re-hit the row |
| `suggestion` | title + brief (add), change list (edit), redirect target and reason (delete); rewritten by review |
| `evidence JSONB` | display only, refreshed on every collision; review never reads it |
| `coverage_at_creation`, `impressions_at_creation`, `target_position` | reconcile baselines |
| `state` | `draft`, `reviewed`, `ready`, `llm_rejected`, `user_rejected`, `done`, `stale` |
| `search_score`, `confidence`, `score`, `verified_at` | |

Partial unique indexes `(site_id, action, topic_key) WHERE page_id IS NULL`
and `(site_id, action, page_id, topic_key) WHERE page_id IS NOT NULL`.
`create_many`: revives `llm_rejected`/`stale` (new job, back to `draft`,
strategy appended); on a live row (`draft`, `reviewed`, `ready`) appends the
strategy and refreshes `evidence` without changing state; never touches
`user_rejected`/`done`. A pair is created or revived only when both sides
are creatable, else both are skipped; `user_rejected` on either side
rejects both; reconcile closes both together. A second pair on the same
weak page with a different `merge_into_page_id` is skipped and reported.
Result: `{drafts, collided: [{id, state, strategies}], filtered: {reason:
count}}`.

`seo_page_suggestion_keywords(suggestion_id, keyword_id)` with cascade.

## 3. Precompute (deterministic, no LLM, no agent)

`api/src/seo/precompute/` is the only module that reads `site_pages`,
`site_page_llm_extraction`, `site_search_daily`, `site_chunks`.

**Rollup** — api process, SQL, triggered by `site_search/service` when a
sync lands `completed` and by `start_seo_job`:
1. Refresh `seo_page_facts` (incl. page-level GSC numbers).
2. GSC → `seo_keywords` (`gsc`, `IMPRESSIONS_FLOOR`) and
   `seo_keyword_gsc_pages`, impression-weighted position, `leader_days_90d`.
3. CTR curve; `ctr_gap`. 4. `branded`. 5. Reconcile (§3.1).

**Embed at insert** — api process, every path that inserts `seo_keywords`
rows (rollup, collect tools, `terms` arguments) embeds them inline with the
in-process embedder (batches ≤300), computes their `coverage` rows
(pgvector top-3 per keyword plus every GSC pair) and attaches each to the
nearest existing centroid within `CLUSTER_ATTACH_DISTANCE`, else leaves
`cluster_id` null. A chain that collects then generates therefore works in
one turn.

**Cluster rebuild** — embed worker, polled from `seo_site_state WHERE
precompute_requested_at > coalesce(embedded_at, '-infinity')`; stamped by
`crawl_jobs/service.settle_crawl` beside `page_classification.start` and
by `POST /precompute`:
6. Recompute coverage for the whole corpus (content changed).
7. Agglomerative over keywords with volume or impressions, cap
   `CLUSTER_MAX_KEYWORDS`; rest attach to the nearest centroid.
   `owner_page_id` = highest mean coverage over members, `site_similarity`
   from the centroid of money+hub chunk-0 vectors. 8. Stamp `embedded_at`.
`embed_worker/db.missing_columns()` gains the `seo_keywords` columns.

### 3.1 Reconcile (job start, after rollup; reports `pending_precompute` when `embedded_at` predates the last crawl settle)
- `add` → `done` when a page with `first_seen_at` after the suggestion,
  indexable and live, has coverage ≥ `OWNER_COVERAGE` for `topic_key`.
- `edit` → `done` per strategy: `ctr` when title or meta changed;
  `questions` when `questions_answered` gained the listed questions;
  `gsc`/`cluster`/`decay` when `content_hash` changed and coverage rose by
  `COVERAGE_MARGIN` over `coverage_at_creation`. Never on position. `stale`
  when the page is not live.
- `delete` → `done` on redirect or 410; 404 → `stale`; `stale` when the
  page's `impressions_28d` grew past `impressions_at_creation`.

## 4. Tools (`api/src/seo/tools.py`, desk `seo`) — 14

Reads need no tools: direct SQL plus the guide's canned queries.
Docstrings are 2–3 sentences; every filter rule below goes in the `seo`
guide, not the docstring. `job_id` is required on every generator and
settle tool. Narrowing: `page_ids` applies to `propose_page_edits` and
`propose_cannibalisation`; `keyword_ids` to `propose_page_edits(gsc|cluster)`,
`propose_gap_pages` and the collect tools; `source_table` is a workspace
table with a `keyword` (resolved, fact-less rows created), `keyword_id` or
`page_id` column. `ids` in settle tools are suggestion ids.

### 4.1 Job
- `start_seo_job(prompt)` → job_id, reconcile counts, `pending_precompute`,
  and the site's standing `ready` counts per action.
- `finish_seo_job(job_id, status)`.

### 4.2 Collect
`ProviderFacade.fetch` gains a `Caller.spend` meter (charged micros, calls,
cache hits); the desk sums it onto the job and refuses a call when
`vendor_micros` would exceed the ceiling (one chunk overshoot accepted).
Dedupe before the request: drop rows fresher than the window, sort, chunk,
so the facade cache key repeats. Returns `{added, refreshed, vendor_calls,
spent_micros}`; `dry_run=true` returns the calls it would make.

- `collect_keywords(job_id, seeds?, keyword_ids?, source_table?, from_gsc = true, from_ranked = true, max_seeds = 10, ideas_per_seed = 30, dry_run = false)`
  Seeds default to top non-branded GSC queries and cluster heads with an
  owner. Ranked keywords for our domain (→ `our_position`), ideas per seed,
  facts only for rows lacking them (30-day window).
- `collect_competitors(job_id, limit = 10, keyword_ids?)`
  `rival_domains` + `serp_competitors` over top non-branded keywords →
  `candidate` rows with guessed brand terms. Returns the ≤10 candidates.
  The user confirms on the tab; the job stays RUNNING.
- `collect_competitor_keywords(job_id, competitor_ids?, limit = 300)`
  `ranked_keywords` per confirmed competitor, its brand terms excluded,
  navigational intent dropped (14-day window).
- `collect_serps(job_id, keyword_ids? | terms? | suggestion_ids? | source_table?, device = desktop, max = 30)`
  `suggestion_ids` means the head keyword of each row, ordered by
  `search_score`; the `needs_serp` list from review feeds straight in.
  Refuses when more than `max` are asked. Writes snapshots and results,
  promotes PAA and related, prunes to 3 (7-day window; the facade's 1-day
  TTL is not the spend guard).

### 4.3 Generate
- `propose_gap_pages(job_id, keyword_ids?, min_volume = 50, max_difficulty = 60)`
  → `add`. Clusters with no owner or `owner_coverage < OWNER_COVERAGE`
  where ≥2 confirmed competitors rank top 10, or one does and volume ≥
  floor; `site_similarity` above `SITE_SIMILARITY_PCT`; adjacency bonus
  when `our_position` or a GSC position ≤30 exists in a cluster whose
  centroid is within `ADJACENT_DISTANCE`; navigational and competitor-brand
  keywords out.
- `propose_topic_pages(job_id, topic, source_table?, dry_run = false)`
  → `add`. Creates the topic keyword, grows ideas through the same collect
  path (ceiling, spend meter, dry run), which embeds and attaches them;
  groups by attached cluster, or by nearest-neighbour among the new rows
  when unattached; drops groups whose head has a page in
  `seo_keyword_content_pages` at ≥ `OWNER_COVERAGE`; keeps long-tail by
  `volume/(difficulty+1)`.
- `propose_page_edits(job_id, evidence: gsc|cluster|ctr|questions|decay|all = all, page_ids?, keyword_ids?, min_position = 4, max_position = 20, min_impressions = 100)`
  → `edit`, one row per (page, topic_key). `gsc`: ranks in the window with
  impressions and `coverage < WEAK_COVERAGE`. `cluster`: owner page missing
  member keywords with volume. `ctr`: `ctr_gap × impressions` above the
  site percentile, position ≤10; a snippet or AI overview feature lowers the
  score. `questions`: question-form GSC queries at 5–20 absent from
  `questions_answered`, plus PAA rows when present. `decay`: clicks down ≥
  `DECAY_DROP` vs previous window, and vs last year when present, both
  windows above the floor. Conversions, in order: owner (an `add`-shaped
  need on a topic an owner page of compatible type covers → `edit` on it),
  then intent (`keywords.intent` incompatible with the page type → `add`
  with the right type in the brief).
- `propose_cannibalisation(job_id, page_ids?, min_shared_impressions = 50)`
  → one `edit` on the stronger page (clicks, inlinks, link_score) and a
  paired `delete` on the weaker with `merge_into_page_id`, linked by
  `pair_id`. Definition: the same GSC query with impressions on ≥2 pages and
  `leader_days_90d ≥ LEADER_MIN_DAYS` on both; page types compatible
  (money vs blog on one keyword is intent split). Protections: never delete
  money, hub, `is_home`, inlinks above median, `first_seen_at` < 90 days,
  or `clicks_28d ≥ CLICKS_FLOOR`. The only source of `delete` rows in v1.
- `save_page_suggestion(job_id, action, topic_key, page_id?, keyword_ids? | terms?, suggestion, merge_into_page_id?)`
  The agent's own row, written straight to `ready` (the agent is the
  reviewer). Same guarded create and protections.

### 4.4 Settle (job-scoped, per-row commit, cache subject includes a hash of suggestion + evidence)
- `screen_page_suggestions(job_id, ids?, question?, limit = 200)` — cheap
  choice model over the job's `draft` rows; confident no → `llm_rejected`.
- `review_page_suggestions(job_id, prompt, ids?, limit = 200)` — judge model
  over `draft` rows; survivors → `reviewed` with a rewritten `suggestion`,
  losers → `llm_rejected`. Reads live tables per row, never `evidence`:
  edit — page facts (title, h1, headings, meta), the page's best chunk per
  missing keyword, each query's position/impressions/ctr_gap, top-3 SERP
  titles/descriptions/features when a snapshot exists; add — the cluster's
  members with volumes, PAA rows, competitor URLs and positions, the
  nearest own page with its coverage; pair — both pages' facts, the shared
  queries with `leader_days_90d`, judged as one item. An `add` with no
  snapshot for its head is left `draft` and returned in `needs_serp`.
- `rank_page_suggestions(job_id, budget_add = 10, budget_edit = 20, budget_delete = 5)`
  Over the job's `reviewed` rows per action, ordered by `search_score`
  (defined per action in the guide: add = `volume_sum × competitor_evidence
  / (difficulty+1)`; edit = `impressions × (1 − coverage)` or `ctr_gap ×
  impressions`; pair = the weaker page's shared impressions); a pair counts
  once against `budget_delete`. Winners → `ready`, losers → `llm_rejected`.
  Rows outside the job are never touched; standing `ready` rows are capped
  by the dashboard, not by rank.

### 4.5 Bulk out
- `seo_download_data(dataset: keywords|gsc_pages|content_pages|competitor_keywords|serps|suggestions)` → CSV path + rows.

The raw `meelu/provider` seo-data tools are not in the SEO scope's
`providers`; the desk has one path to the vendor.

## 5. Constants (`api/src/seo/constants.py`, initial values)
`IMPRESSIONS_FLOOR 20`, `CLICKS_FLOOR 5`, `WEAK_COVERAGE 0.55`,
`OWNER_COVERAGE 0.7`, `COVERAGE_MARGIN 0.05`, `SITE_SIMILARITY_PCT 25`,
`ADJACENT_DISTANCE 0.25`, `CLUSTER_ATTACH_DISTANCE 0.2`,
`CLUSTER_MAX_KEYWORDS 5000`, `LEADER_MIN_DAYS 10`, `DECAY_DROP 0.3`,
`CTR_MIN_SAMPLE 30`, `SCREEN_CONFIDENCE 0.8`, `SERP_KEEP 3`, freshness
windows facts 30d / ranked 14d / serps 7d / rivals 30d. Raw cosines
everywhere; percentiles only where named.

## 6. Deterministic filters (service code, every caller)
Branded (ours and each competitor's) out unless the prompt opts in; same-
language matching; intent → page type compatibility (transactional/
commercial → money, informational → informational/hub) applied after the
owner conversion; `delete` only through a pair with protections and no GSC
90-day window → no deletes; existing-row memory and pair rules of §2.11;
evidence floors (an `add` needs ≥1 keyword with facts, a GSC edit needs
impressions above the floor); caps, dry run and the per-job ceiling on
every vendor path.

## 7. Why this beats a bare LLM
| | bare LLM | this desk |
|---|---|---|
| Volume, difficulty, competitor positions, CTR baseline | no | stored, joinable, fresh-windowed |
| Cost per question | re-reads the corpus | SQL over precomputed rows |
| Memory of decisions | none | `user_rejected` permanent, `done` verified with `verified_at` |
| Consistency | new list every time | generators deterministic |
| Spend control | none | caps, dry run, per-job ceiling, facade cache |
| "Why is X ahead" | guesses | snapshot titles/descriptions/features vs our coverage, title, age, inlinks |

## 8. Guide, chips, runner

The `seo` guide carries: tables and grain, states, the constants, the
pipeline order (generate → screen → review → rank), spend rules (one
collect per turn unless the user asked for breadth; `dry_run` first when
the set is large), the per-action `search_score`, the canned SQL (top
non-branded queries; a page's queries; a job's drafts → head keywords; the
"why ahead" comparison with a lexical fallback for a keyword with no
coverage row yet), and what to do on `collided`: present the standing
`ready` rows instead of reporting nothing.

Chips (`dashboard/src/features/prompt-chips/seo.ts`, tool names imported
from one place) carry strategy, sets, pass rule, review rule, cap, and
where the user decision falls. Chains below are the guide's; each chip
adds a pass rule and a review rule.

| chip | chain (start/finish implied) | pass rule / review rule |
|---|---|---|
| **What should I do?** (no spend) | `propose_page_edits(all)` + `propose_cannibalisation` → screen → review → rank. 6 calls | passes when the fix is one page's work; review keeps the few with the most impressions at stake. `needs_serp` rows stay draft and are listed for the user |
| **…with keyword research** | `collect_keywords` first, then the above plus `propose_gap_pages` when confirmed competitors exist | |
| **Analyse competitors** | `collect_competitors` → stop, user confirms on the Keywords screen (job stays RUNNING) → `collect_competitor_keywords` → `propose_gap_pages` → `collect_serps(suggestion_ids)` → screen → review → rank | passes when two competitors rank top 10 and no page of ours is within 30; review rejects topics off the site's business |
| **Content for topic X** | `propose_topic_pages(topic)` → `collect_serps(suggestion_ids)` → review → rank | passes when long-tail volume exists that no page owns; review writes one brief per group |
| **Improve this page** | `propose_page_edits(all, page_ids=[p])` → `collect_serps` on its top queries → review | rows are per query; review consolidates into one brief per page for this chip |
| **Impressions but no clicks** | `propose_page_edits(ctr)` → review | passes when `ctr_gap` is not explained by a SERP feature; review: titles and snippets first |
| **Why is competitor ahead for Q** | `collect_serps(terms=[Q])` → SQL comparison → `save_page_suggestion` | the agent writes the row itself |
| **Which pages cannibalise** | `propose_cannibalisation` → review → rank | review prefers merge; delete only when the weaker page adds no query the stronger lacks |
| **What to prune** | same; only the delete side is presented | |

Runner: the scope response gains `silentWrites` (generate, screen, review,
rank, finish of this desk); `runner.js` `canUseTool` skips `askPermission`
for those names once the first write of a job was approved. Collect tools
always ask because they spend.

## 9. Endpoints (`/api/v1/seo/...`)
Get/list/patch per table; `POST /page-suggestions/{id}/reject|done`;
`POST /competitors/{id}/confirm|ignore` (with brand terms);
`POST /precompute` (sets the flag); `GET /export?dataset=`; `GET /overview`.
httpx tests incl. revive/`user_rejected` survival, pair atomicity, ceiling
refusal, job-scoped rank.

## 10. Dashboard (`dashboard/src/app/dashboard/seo/`)
v1: **Suggestions** (grouped by action then page, pairs shown together,
evidence chips, done/reject, per-strategy acceptance and before/after
position) and **Keywords** (universe, clusters, owner, coverage, GSC,
competitor confirm/ignore list). SERPs tab later.

## 11. Build plan (migration in step 1 declares the full model set; squash at the end)
1. Package, all tables, `seo_page_facts` + rollup + CTR curve, embed-at-
   insert, endpoints, tests.
2. `seo_page_suggestions`, guarded create with pair rules, reconcile,
   `save_page_suggestion`, Suggestions tab.
3. `propose_page_edits`, `propose_cannibalisation`, screen, review, rank;
   `silentWrites` in the runner; the no-spend chip. Until step 4,
   `coverage` is the lexical hit only.
4. Cluster rebuild in the embed worker, `missing_columns`, corpus coverage.
5. `Caller.spend` in `providers/registry.py`; `collect_keywords`,
   `collect_competitors`, `collect_competitor_keywords`; extend
   `shape.ranked_row`; ceiling.
6. `collect_serps` (service extended for PAA, related, descriptions),
   `propose_gap_pages`, `propose_topic_pages`; competitor and topic chips.
7. Download tool, Keywords tab, guide, remaining chips.

## 12. Cut from v1
SERP result classification and a content-type generator; standalone dead-
page deletion (needs a backlink source); snapshot rank as our position (GSC
only); seasonality months; per-tool locale; SERPs tab; automatic hand-off
of `add` briefs to the Content desk; `domain_overview` per competitor.

## 13. Open decisions
- `SEO_JOB_VENDOR_CEILING_MICROS` default value.
- "Improve this page": fetch competitor page text (Apify) for a term diff,
  or snapshot titles/descriptions only in v1.
