# RFC — Site Structure (building blocks, strategies as prompts)

This is the technical design for `site-structure-prd.md`. It is grounded
in the code as of 2026-09-12. A codebase review re-verified the cited
paths on 2026-09-13.

## 0. The architecture rule that this RFC follows

We do not code strategies. A strategy is a prompt given to the agent.
Examples: "find money pages and analyze their link structure", "find
orphan pages and propose links into them", "find pages with too many
outgoing links and suggest trims". The code ships only building blocks,
in four kinds:

1. Precompute functions. These are deterministic algorithms that run on
   crawl end or a button click. They write compact results to the
   database: the edge table, PageRank, roles, defects. The agent never
   triggers page-by-page computation. It reads the precomputed tables
   over direct SQL.
2. Agent tools. These are small primitives on the Site desk that combine
   well: targeted retrieval, guarded writes (create suggestions, review,
   set role), CSV export, and starting item-loop jobs.
3. The item-loop job. This is one generic harness that walks a set of
   rows (suggestions, defects, pages). For each item it makes one
   constrained LLM call in the app, on the local model budget. The server
   validates the output and writes the result back. The context of the
   main agent sees only a summary, never the items.
4. Canonical state. Every suggestion lands in the same suggestions table
   with the same state machine, whatever strategy produced it. So the
   review UI, applied-verification, and rejection memory work the same
   way everywhere.

Guardrails live in service code, never in prompts. The suggestion-create
service enforces eligibility, budget, duplicate, and rejection-memory
checks for every caller. The loop runner owns the prompt frame, and the
server validates every output. The rubber-stamp detector counts approvals
per model. A prompt that forgets a rule cannot break precision.

## 1. What already exists (build on it, do not rebuild it)

| Capability | Where |
|---|---|
| Link capture | Crawler `app/src/main/crawler/extract.js` produces `outLinks: {url, anchor, rel}` and posts them to `POST /site/pages` (`endpoints.py:57`; crawler `index.js:93`) |
| Graph build | `api/src/site_pages/repository.py::rebuild_graph` (`:676-731`). One recursive SQL statement writes `inlinks`, `inbound_anchors` (top 25), and `depth`. `POST /site/pages/graph` triggers it at crawl end, and the same service call also runs `compute_link_scores` (`service.py:216-218`). Normalization to carry over: `OUT_LINK_URL` strips the fragment and trailing slash, `NORM_OUT_LINK` lowercases scheme and host (`repository.py:666-673`), self-links are excluded. `LIVE_PAGE` (`:732`) gates the PageRank edge list (`:756`), not `rebuild_graph` itself |
| PageRank | `api/src/site_pages/pagerank.py`. Edges are unweighted (`src`/`dst` only). A teleport mapping is supported. Output is rescaled to max 100 with one-decimal quantization (`:47-49`). So it is site-relative, not a probability. `service.compute_link_scores` seeds `SEED_FLOOR=0.1` (`service.py:187`) plus GA sessions (`repo.landing_seed`, 90 days, `repository.py:775-790`) |
| Orphan and broken-link rules | `api/src/technical_seo/rules/page.py` (`orphan-page`, `orphan-page-unlisted`, `broken-internal-link`, `internal-link-to-redirect`, `deep-page`, `missing-from-sitemap`) |
| Chunk embeddings | `SiteChunk` (`api/src/site_pages/models/site_chunk.py`), Vector(384), model e5-small with silent truncation at 512 tokens (`embed_worker/embedding.py:28-34`), HNSW cosine index, no per-site partitioning. Chunking lives in `api/src/embed_worker/chunking.py` (`page_chunk` at `:121`). Chunk 0 is a synthetic page summary (`title · h1s · meta · lead · inbound anchors`, `chunking.py:126-139`, `worker.py:18-25`). The query path `semantic_page_matches` (`repository.py:997-1027`) is already an exact per-site scan with a similarity cutoff and a pool clamp. It does not use the HNSW index |
| Page kind | Crawler `extract.js::classify` (`:244`) returns `{kind, format?}`. `shallowReason()` (`:277`) is a separate export. `kind` server-defaults to `'other'` (`site_page.py:83`) |
| GSC and GA | `site_search_daily(day, query, page, clicks, impressions, position)` and `site_traffic_landing_daily`. Local sync code lives in `app/src/main/integrations/` |
| Local LLM jobs | The crawl-job pattern: one table per job type, no lease columns. Mutual exclusion is a partial unique index on the active row (`crawl_jobs/models/site_crawl_job.py`). Liveness is `heartbeat_at` plus `POST …/reap`. Claim is `POST /{id}/claim`. Heartbeat is `PATCH {heartbeat:true}` and it returns `{stop}`. The app reaps at boot with `staleMs: 0` (`orphaned-jobs.js:25`). On the app side, jobs run zero-tool `query()` calls through `llmEnv()` (`technical-seo/check.js:119`) |
| Review-shaped table | `seo_structural_proposals` on the SEO desk. It is a shape reference only. Structure keeps its own tables because of desk isolation |

Facts that constrain the design:

- Raw HTML exists only inside the crawler. Link position must be
  extracted there.
- There is no central models directory. Each package owns `models/`. The
  codebase has no `sa.Enum`. The convention is TEXT with a
  `server_default` and `Literal[...]` validation in schemas (for example
  `seo_structural_proposal.py:27`). Every "enum" column below follows
  that convention.
- Unique constraints are written as `Index(..., unique=True)` in
  `__table_args__`, with `postgresql_where` for partial indexes
  (`crawl_jobs/models/site_crawl_job.py:19-27`).
- Agent scoping is the `x-meelu-scope` header (`agent/auth.py:65`) plus
  write filtering in `api/src/agent/scoping.py`. Write filtering is per
  desk: the union of the writes of all scopes on the desk (`desk_writes`,
  `api/src/agent_scope/registry.py:52-58`). Desks are declared in
  `api/src/agent_scope/desks.py`. Scopes live in `api/src/agent_scope/`.
  Guide topics live in `api/src/agent/tools/guides.py`.
- `settings.agent_data_dir` exists (`settings.py:27`), but today only the
  `data_analytics` model store uses it. The download-as-CSV-path tool
  here is the first of its kind in api. It is a new convention, modeled
  on the desk-download contract in CLAUDE.md, not an existing code
  pattern.
- Site pages are upserted by URL and stay stable across crawls. So
  `ondelete=CASCADE` foreign keys to `site_pages` do not erase suggestion
  history on recrawl, and `never` rows survive.

## 2. Component placement

| Work | Runs in | Why |
|---|---|---|
| Link-context extraction | App crawler | The only place where HTML exists |
| Precompute (edges, PageRank, roles, defects, verification) | api, `site_structure` package | Deterministic. Postgres and pgvector do all of it. It must run without the agent |
| Item-loop LLM job | App local job | The crawl-job pattern, on the local model budget of the user |
| Retrieval, guarded writes, export, loop-start tools | Agent server (Site desk) | The primitives that strategies are built from |
| Review UI | dashboard `site/structure` | Rendered in the App too |
| Strategies | Prompts: guide recipes, plan-library entries, user asks | Never code |

One boundary note: the precompute reads `site_search_daily` and
`site_traffic_landing_daily` for the teleport seed and the deficit. That
is deterministic algorithm input inside api, the same combination that
the agent itself can make. It is deliberate and allowed. No agent tool in
this package reads the tables of another desk.

## 3. Crawler changes (the one prerequisite)

Change `app/src/main/crawler/extract.js` as follows:

- Classify a region per link: `nav | header | footer | aside | breadcrumb
  | body | pagination`. Detection uses the nearest ancestor semantic tag,
  plus heuristics for themes without semantic tags: `[role=navigation]`,
  `[class*=nav]`, `[id*=nav]`, `[class*=footer]`, `[id*=footer]`,
  `[class*=menu]`, `[class*=breadcrumb]`, `[aria-label*=breadcrumb]`.
  Pagination is detected from `rel=next/prev`, `[class*=pagination]`, and
  numbered anchor sequences. The accepted error mode: unmarked templates
  classify as `body`, which inflates the editorial graph.
- Record a block ordinal and context for `body` links. This is a new
  block walk. It must use the same `BLOCK_SELECTOR` pass that produces
  `bodyText` (`extract.js:5,176-191`). Then the ordinals align with the
  text that the chunker later splits. The heading-ordinal scheme
  (`extract.js:116-121`) covers h1 to h6 only and is not reused.
  `context` is the containing block text, cut at a sentence boundary, at
  most 300 characters.
- The entry shape becomes `{url, anchor, rel, region, ordinal?, context?,
  count}`. The same URL in the same region dedupes with `count`.
  Different regions stay separate entries. `externalLinks` gains `region`
  only.
- The crawl frontier loop (`crawler.js:515`) walks `outLinks` and
  enqueues on `rel !== "nofollow"`. The new shape (deduped entries, split
  by region) changes what that loop sees. Update the loop in the same
  change and keep its enqueue behavior identical.

No API schema change is needed: `SitePageWritableFields.out_links` is
`list[Any]` (`site_pages/schemas/__init__.py:165-166`). So the JSONB
shape changes in place. Nothing is deployed. The next full crawl
repopulates the data.

## 4. New api package: `api/src/site_structure`

Subpackages: `graph/` (edges, PageRank, defects), `roles/`,
`suggestions/`, `loop_jobs/`, and a shared `models/`. Keep each one
simple: plain service and repository files, in the shape of
`api/src/keys`. Do not build shared abstraction layers between the
subpackages yet. A little duplication between subpackages is fine.

### 4.1 Tables (all `EntityMixin + SiteScopedMixin`; "enum" means TEXT plus Literal)

`site_page_links` is the canonical edge list. Each crawl rebuilds it with
a full replace: one delete-by-site statement, then batched value inserts
of 1000 rows, after the `write_link_scores` pattern.
Columns: `src_page_id FK ondelete=CASCADE, dst_page_id FK
ondelete=CASCADE, anchor, rel, region, ordinal INT NOT NULL DEFAULT -1,
context, count INT, weight REAL, followable BOOL, dst_canonical BOOL`.
The -1 sentinel for non-body links avoids NULLs, because NULLs count as
distinct in a unique index.
Unique index on `(site_id, src_page_id, dst_page_id, region, ordinal)`.
Plain indexes on `(site_id, dst_page_id)`, `(site_id, src_page_id)`, and
`(site_id, lower(anchor))` for the anchor-uniqueness check.
Weights by region: body 1.0, breadcrumb 0.4, nav 0.2, header 0.2, aside
0.15, pagination 0.15, footer 0.1, and 0 when `rel` contains nofollow.
`dst_canonical` is false when the target is non-canonical, noindexed, or
a redirect. The reason is not stored. Trap reports derive the reason with
a join on the target page row. Such edges are stored for the trap reports
but excluded from PageRank and defect math.

`site_page_roles`: `page_id FK CASCADE` with a unique index, `role`
(money, informational, utility, leaf, unknown), `confidence REAL, source`
(rule, llm, user), `template_key TEXT, locked BOOL server_default false`.

`site_structure_defects` holds the defect rows that the Health tab and
the `issue_triage` loop schema operate on: `kind` (facet_trap,
internal_nofollow, missing_breadcrumbs, nav_gap, high_outdegree, …),
`page_id FK CASCADE NULL, detail JSONB, state` (open, dismissed),
`dismissed_reason TEXT, run_id FK`. Each precompute run re-emits open
defects and closes the ones that no longer hold. A `dismissed` row is not
re-opened for the same `(kind, page_id)`.

`site_structure_settings` is one row per site: `archetype` (ecommerce,
blog, saas, local), `budget_overrides JSONB`. The Roles tab writes it.
The roles cascade and the create-path budget read it.

`site_link_suggestions`: `kind` (new_link, bridge_link — `trim` is
deferred together with removal suggestions, which are report-only in v1),
`src_page_id FK, dst_page_id FK, src_ordinal INT, src_chunk_text TEXT,
src_paragraph_key TEXT` (a hash of the normalized chunk text, which is
the stable paragraph identity), `anchor_text, strategy TEXT` (free text
that names the strategy or template that produced it), `scores JSONB,
score REAL, state` (proposed, llm_approved, llm_rejected, accepted,
rejected, never, snoozed, applied, stale), `state_reason` (one shared
enum for LLM and human: wrong_target, bad_placement, bad_anchor),
`src_content_hash TEXT, snooze_until TIMESTAMP, accepted_at_seq INT,
reviewed_at, applied_at, verified_at`.
Chunk ids are not stable across re-embeds. So the suggestion stores the
chunk text, the ordinal, and the paragraph key, not a `site_chunks`
foreign key. `scores` records the per-signal breakdown. Rejections
(`rejected` and `llm_rejected` alike) are scoped to `src_content_hash`. A
content change lifts the block. `never` ignores the hash.
Partial unique index on `(site_id, src_page_id, dst_page_id) WHERE state
IN ('proposed','llm_approved','accepted','applied')`. The `applied` state
is included so that the window between accept and verify cannot spawn
duplicates.

The guarded create service is used by the agent tool, the loop job, and
any future caller. The checks run in the service for every caller:

- Anti-joins: existing body edges in `site_page_links`, rows in the
  partial-unique states, `never` rows, and `rejected` or `llm_rejected`
  rows with a matching `src_content_hash`.
- Eligibility: the target role must be money or informational, not
  utility or leaf. The source chunk must have at least 40 words and must
  not come from a list or a table. One suggestion per
  `src_paragraph_key`.
- Budget: `floor(word_count/125) − body_outdegree − pending_accepted`.
  `word_count` comes from `site_pages`. `body_outdegree` counts
  body-region edges with `dst_canonical=true`. `pending_accepted` counts
  the rows of this source in the partial-unique states. The whole batch
  check runs as one SQL statement under a per-site advisory lock. Then
  two concurrent callers cannot both pass and overshoot.
- The service returns accepted or refused per item, with the name of the
  refusing check. Then a caller learns the constraint instead of a blind
  retry.

`site_structure_runs` is bookkeeping for one precompute pass: `seq INT`
(monotonic per site), `trigger` (crawl, manual, verify), `status, params
JSONB, counters JSONB, started_at, finished_at`. It is not claimable. It
runs in-process in api. `trigger=verify` runs only stage 5.

`site_loop_jobs` is the generic claimable item-loop job: `status`
(queued, running, complete, failed), `item_kind` (suggestion, defect,
page), `item_ids JSONB` (always concrete ids — the service resolves a
filter to ids at create time and does not persist the filter), `task
TEXT` (an optional strategy addendum, see §4.4), `template TEXT` (a
server-side task-template name; the core review flows use fixed
templates), `output_schema TEXT` (a name from the server-side registry),
`context JSONB` (strategy-global extras only; the server assembles
per-item context at item-fetch time), `model TEXT` (stamped by the runner
at claim), `heartbeat_at, counters JSONB, failures JSONB` (item_id →
reason), `created_by` (agent, ui).
Partial unique index on `status='running'` per site. Multiple `queued`
rows are allowed, and the runner drains them in order. So a second job
queues instead of a refusal. `POST …/reap` uses the 10-minute staleness.
Claim, heartbeat, and PATCH are identical to the crawl-job protocol.

New columns on `site_pages`: `editorial_inlinks INT` and
`editorial_score REAL`.

Alembic: one revision per build step. Squash into the baseline when
convenient.

### 4.2 PageRank changes (a modification, not reuse)

`pagerank.py` today distributes `damping·rank[src]/out_count[src]` with
no weights. Extend it: edges become `(src, dst, weight)`, the
contribution becomes `damping·rank[src]·w/Σw(src)`, and dangling mass
redistributes through the teleport vector as today. The precompute runs
it twice:

- The full canonical graph (followable, canonical targets, weight
  ignored) with a blended teleport `SEED_FLOOR + α·GA_sessions +
  β·log(1+GSC_impressions_90d)`. The result writes `link_score`, which
  keeps its current meaning with a better seed. α and β ship as fixed
  constants, not knobs. Nothing exposes them until something consumes the
  distinction.
- The weighted editorial graph (region weights). The result writes
  `editorial_score`.

Both outputs are site-relative scales from 0 to 100, with the one-decimal
quantization that matches the existing rescale. Never compare them across
sites and never show them as absolute page quality.

### 4.3 Precompute (one `site_structure_runs` row, in-process, no LLM, no agent)

1. Edges. Rebuild `site_page_links` from `out_links`. Restamp `inlinks`
   and `depth` on the canonical graph. Depth is not computed through
   `pagination` edges. Compute `editorial_inlinks`. This replaces
   `rebuild_graph` and also the `compute_link_scores` call bundled with
   it (`service.py:216-218`). The structure run absorbs both, so
   `link_score` continues to be written. `POST /site/pages/graph` becomes
   a thin trigger of a structure run. The crawler keeps calling the same
   endpoint.
2. Authority. Run §4.2.
3. Roles. The rule cascade reads stored fields. `schema_types` with
   Product or Offer means money. Article, BlogPosting, HowTo, FAQ, or
   `kind=article` means informational. `kind` in legal or contact, or a
   `shallow_reason`, means utility. Body outdegree of 0 plus thin content
   means leaf. URL-pattern rules (for example `/product/`, `/blog/`) work
   as tie-breakers, tuned by the archetype in `site_structure_settings`.
   Cross-check the `kind` vocabulary against `extract.js::classify`
   before you write the cascade. `locked` rows are never overwritten.
   Low-confidence residue becomes `unknown` and appears in the confirm
   UI.
4. Health. Emit `site_structure_defects` rows: parameter and facet trap
   (high fan-in of non-canonical query-string URLs), internal nofollow,
   missing breadcrumbs, `nav_gap` (a spoke page whose only hub edge has a
   region other than body), and high outdegree.
5. Applied verification. For `accepted` suggestions: a body-region edge
   from source to target, after URL normalization to page identity, marks
   `applied`. A missing `src_paragraph_key` on recrawl marks `stale`. Two
   crawl-triggered runs after `accepted_at_seq` without the edge also
   mark `stale`. A `trigger=verify` run executes only this stage. The
   refresh on the Suggestions tab fires it, so "I applied these links"
   does not wait for a crawl. Without a recrawl the edge cannot appear,
   so the verify run mainly re-checks staleness.

That is the whole coded pipeline. There is no candidate-generation stage
and no drain stage. Opportunity finding is a strategy, executed by the
agent with the tools below.

### 4.4 The item-loop job (the one LLM harness)

The agent, or a dashboard button, creates a `site_loop_jobs` row that
names the items, a task template, and a registered output schema. The app
claims the job. For each item the app: fetches the item payload from the
server at processing time (the server returns "skip" for items that are
no longer in the expected state), makes one zero-tool schema-constrained
`query()` call, and posts the validated output back. One item per call,
never a batch map. Then it works with small local models.

Prompt safety and quality:

- The runner owns the prompt frame. Item content (chunk text, page text —
  crawled third-party material) is wrapped in fixed delimiters by the
  runner. It is never concatenated raw into instructions.
- The per-item instruction comes from a server-side task template, named
  by `template`, in one registry beside the schema registry. The `task`
  field from the agent is an optional addendum interpolated into the
  template. It is never the whole prompt. The core review flows
  (`link_verdict`, `anchor_pick`) ship with fixed templates.
- No loop output is terminal. Every write lands in a human-reviewable
  state. `llm_approved` still needs an accept. `issue_triage` dismissals
  are visible and reversible in the Health tab.

Idempotency (safe to run twice) and resume:

- `POST /loop-jobs/{id}/items/{item_id}/result` upserts keyed on
  `(job_id, item_id)`. It applies its effect as a guarded state
  transition: a no-op with a 409-style result unless the row is in the
  expected pre-state. A re-post is harmless.
- After a reap and a re-claim, the runner skips items that already have a
  result. A job that dies at item 800 of 1000 resumes at 801.
- Items that fail schema validation land in `failures` with a reason.
  Then a strategy can retry only those items.

The `output_schema` registry is server-side code, one handler per name,
because the write-back side effect must be trusted code:

- `link_verdict`: `{approve: bool, reason: enum}` → the suggestion moves
  `proposed → llm_approved | llm_rejected`, with a reason from the shared
  enum.
- `anchor_pick`: `{anchor: str}` → the server makes sure that the anchor
  is a substring of `src_chunk_text`. A non-substring becomes
  `llm_rejected(bad_anchor)`. The server also rejects an exact anchor
  that already points at a different page anywhere on the site, in edges
  or in pending suggestions. "Exact" means lowercased with collapsed
  whitespace, one normalization defined in the service, backed by the
  `(site_id, lower(anchor))` index.
- `issue_triage`: `{action: keep|dismiss, note}` → a guarded transition
  on a `site_structure_defects` row.
- `page_label`: `{label: str, confidence}` → writes a role with
  `source=llm` when the row is not locked. This ships late, see the build
  plan.

New schemas are added as code when a strategy needs one. Strategy text
never defines a schema.

Rubber-stamp detection: verdicts are counted per `model` across jobs. A
model with an approval rate over 90% across at least 30 items is flagged,
and the UI marks its approvals as untrusted. The aggregation is a query
over `site_loop_jobs` counters plus `model`. No extra table until that
proves insufficient.

### 4.5 State machine

`proposed → llm_approved | llm_rejected`. Also `proposed → accepted |
rejected | never | snoozed` directly: a human can act on un-vetted
suggestions, which makes the Suggestions tab usable before any LLM
exists. `llm_approved → accepted | rejected | never | snoozed`.
`snoozed → llm_approved` after `snooze_until` (back to the human queue,
no second verdict). `accepted → applied | stale` per §4.3 stage 5.
`rejected` and `llm_rejected` resurface only when `src_content_hash`
changes. `never` is permanent.

### 4.6 Endpoints (`/api/v1/site/structure/...`)

Get, list, and patch per table, defects included. Also:

- `POST /runs` (crawler and manual trigger; `params.verify_only` for the
  verification run).
- `POST /loop-jobs` (the create path for the dashboard; the agent tool
  calls the same service in-process).
- `GET /loop-jobs/due`, `POST /loop-jobs/{id}/claim`,
  `PATCH /loop-jobs/{id}`, `POST /loop-jobs/reap`.
- `POST /loop-jobs/{id}/items/{item_id}` (item fetch at processing time)
  and `POST /loop-jobs/{id}/items/{item_id}/result`.
- `GET /overview` (the counts for the tab headers).
- `POST /suggestions/{id}/accept|reject|snooze|never` and
  `POST /suggestions/accept-batch` (ids or a strategy filter; the create
  budget already ran, so batch accept needs no second check).
- `POST /roles/confirm`.
- `GET /export?dataset=` (the download buttons of the dashboard; it and
  the agent download tool call the same export service function).

Scoping note: `GET /seo/rank-tracker/due` is user-scoped
(`rank_tracking/endpoints.py:66-72`), not site-scoped. `GET
/loop-jobs/due` copies that on purpose. It is user-scoped and returns due
jobs across sites. Then the app poller runs one loop without
`x-meelu-site`. The endpoint therefore lives on its own router, not
behind `require_site`.

Integration tests follow the existing httpx pattern.

## 5. Agent server (Site desk) — the strategy surface

- Add the new tables to `SITE` in `api/src/agent_scope/desks.py`. This
  only affects what `schema_map` advertises. The SELECT grants and the
  RLS policies come from `security.bootstrap()` at startup. So the agent
  service must restart after the migration.
- Add `api/src/site_structure/tools.py` to the imports in
  `api/src/agent_scope/registry.py`, and add its `WRITE_TOOLS` to the
  union there. The tools:

Reads and retrieval:

- `structure_download_data(dataset: edges|suggestions|deficit|defects)`
  writes a CSV under `settings.agent_data_dir` and returns the path plus
  a row count. The `deficit` dataset (impressions joined to
  `editorial_inlinks`) is a blessed materialized precompute output, not
  an in-tool cross-desk join. Analytical questions route to the Analytics
  desk.
- `structure_find_placements(target_page_id, keywords?, limit≤20)` embeds
  the intent summary of the target (chunk-0 style: title + h1 + meta +
  lead, with the `query:` prefix, about 150 to 250 tokens, under the
  512-token truncation) plus keywords that the caller supplies. The tool
  reads no keyword tables of another desk. The agent passes keywords that
  it already has. The tool scans body chunks of informational pages with
  an exact per-site scan, the same approach that `semantic_page_matches`
  already takes. It applies eligibility: a chunk of at least 40 words,
  not derived from a list or a table, lexical co-occurrence of a keyword
  token family nearby, and a candidate cap per chunk. It returns at most
  `limit` scored rows. Each row carries a page id, an ordinal, a
  paragraph key, and a snippet of about 200 characters, never the full
  chunk text.
- Ordinary graph questions (orphans, deficit, outdegree, roles) need no
  tool. The agent reads the precomputed tables over direct SQL, and the
  plan library of the guide carries the canned queries.

Writes (human-gated or guarded by the service):

- `structure_create_suggestions(items)` is a batch create through the
  guarded service of §4.1.
- `structure_start_loop(item_kind, item_ids | filter, template, task?,
  output_schema, context?)` resolves a filter to concrete ids and creates
  a `site_loop_jobs` row (queued if one is running). It refuses an
  unregistered schema or template name.
- `review_suggestion(id, verdict, reason)` and
  `set_page_role(page_id, role)`, which sets source=user and locked=true.
  Desk-level write filtering means that other Site scopes can also call
  these tools. That is accepted. They are safe, human-gated actions.

Add a guide topic `structure` in `api/src/agent/tools/guides.py`, listed
on the SITE desk. It covers: the tables and their grain, the deficit rule
("high impressions plus low editorial_score"), the review rules, and
worked strategy recipes. The recipes are orphan rescue, info-to-money
placement, and outdegree trim, each written as "read these tables, then
retrieve, create, and loop". Recipes name only the tools registered on
the scopes of this desk. Everything else is described, per the prompt
rules. Add plan-library entries for the deficit query and the orphan
query. Add an Ask-shaped scope `site-structure` in
`api/src/agent_scope/site/`, registered in `registry.py` with the write
tools above.

The strategies from the PRD map onto this surface with no new code.
Money-page link analysis is SQL over edges plus roles. Orphan rescue is
SQL, then `structure_find_placements`, then
`structure_create_suggestions`, then a `link_verdict` and `anchor_pick`
loop. Outdegree trim is SQL plus an `issue_triage` loop over the defect
rows of the worst pages.

## 6. App changes

- The crawler extraction from §3, with the frontier-loop update.
- The loop-job runner. Register it beside `startCrawlSchedule` in
  `src/main/index.js`, gated by an env var. It polls the user-scoped
  `GET /site/structure/loop-jobs/due`, claims, fetches each item, runs
  the zero-tool `query()` call, posts the item result, heartbeats, and
  stamps `model`. The reap is wired into `orphaned-jobs.js`.
- The post-crawl call does not change. `POST /site/pages/graph` now
  triggers the precompute run.

## 7. Dashboard — `dashboard/src/app/dashboard/site/structure/`

Tabs:

- Health: the defect list with dismiss, traps, breadcrumbs, nav_gap.
- Roles: the confirm flow, the archetype picker that writes
  `site_structure_settings`, and the unknown-residue list.
- Suggestions: grouped by target page, the source paragraph with the
  anchor phrase highlighted, accept, reject with a reason, snooze, never,
  batch-accept per strategy when its acceptance rate is high, a refresh
  that fires the verify-only run, and per-strategy acceptance stats.
- Deficit: impressions against `editorial_inlinks`, with the explicit "no
  search data" state.

The "review with AI" button on Suggestions creates a loop job through
`POST /loop-jobs`, with the fixed `link_verdict` template over the
selected proposed rows. It is the same job that the agent creates.

## 8. Decisions and alternatives

- An own edge table instead of JSONB recompute. The downstream reads need
  per-edge region, weight, and context. Applied verification becomes a
  join.
- Chunk text stored on suggestions instead of chunk foreign keys. Chunk
  rows are replaced on re-embed, and a dangling key would break review.
- One generic loop-job table instead of one table per job type. The job
  types here are open-ended by design, which is the point of strategies.
  The schema and template registries keep prompts and write-backs as
  trusted code. The existing per-type tables elsewhere are untouched.
- Guardrails in the create service, not in the tool layer. Then the loop
  job and the tool cannot diverge.
- An exact per-site vector scan for retrieval, which is what the existing
  `semantic_page_matches` query already does in practice.
- No networkx and no FAISS. The e5-small model stays. Thresholds are
  calibrated per site from score distributions, never set as absolute
  cosine values, because the e5 cosine range is compressed.
- No GBDT in version 1. Acceptance data can train a scorer later through
  the `data_analytics` `train_classifier` tool.
- Simple beats DRY. Subpackages can repeat small helpers. No shared
  framework until a third consumer exists.

## 9. Build plan — one step at a time, each shippable and reviewable

Each step is a separate piece of work with its own migration where
needed, its own tests, and a working surface at the end. Do not start a
step before the previous one is merged.

1. Crawler link context. The §3 extraction, the frontier-loop update, and
   the JSONB shape change (no api schema change needed). Run one real
   crawl and make sure that the regions and ordinals look sane.
2. Edge table plus precompute stage 1. The `site_structure` package
   skeleton, `site_page_links`, `site_structure_runs` with `seq`, the
   edge rebuild that replaces `rebuild_graph` plus `compute_link_scores`,
   the depth and inlinks restamp, and `editorial_inlinks`.
   `POST /site/pages/graph` becomes the trigger. Integration tests.
3. Weighted PageRank. §4.2, `editorial_score`, and the blended teleport
   with fixed α and β.
4. Health plus Deficit. `site_structure_defects`, precompute stage 4, the
   endpoints, the Health tab, and the Deficit tab. The Deficit tab only
   needs `editorial_inlinks` and existing GSC data. This is the first
   user-visible value, and it needs nothing from the LLM or the agent.
5. Roles. The rule cascade, `site_page_roles`, `site_structure_settings`
   with the archetype, the confirm endpoints, and the Roles tab with
   money-page confirmation.
6. Suggestions store plus guarded create. `site_link_suggestions`, the
   state machine with the direct human transitions from `proposed`, the
   guarded create service, the review endpoints with batch-accept,
   applied verification (stage 5 plus the verify-only run), and the
   Suggestions tab.
7. Item-loop job. `site_loop_jobs`, the claim, heartbeat, reap, item, and
   result endpoints with the idempotency rules, the schema registry with
   `link_verdict` and `anchor_pick` and their fixed templates, and the
   app-side runner. Test with a stubbed model, and include the
   die-and-resume path.
8. Agent surface. `tools.py` (download, find_placements,
   create_suggestions, start_loop, review_suggestion, set_page_role), the
   desk, the scope, and the guide with the first strategy recipes.
   Rubber-stamp stats surfaced in the Suggestions tab.
9. Later, on demand. The v1.1 signal sources (query overlap from GSC,
   chunk similarity) as retrieval additions. The `issue_triage` and
   `page_label` schemas when a strategy needs them. Template-widget edge
   detection in the crawler. Taxonomy tables and the Tree tab. Per-site
   threshold calibration helpers. GBDT scoring.
