# Dead-code review — app/ and dashboard/

2026-09-08. Two audit agents traced every export, IPC channel, API route and
scope to its actual callers (across both `app/` and `dashboard/`, since the
renderer is the dashboard and the app's workers call dashboard routes).
Findings are grouped: **A = safe to delete now** (no reachable caller, proven),
**B = dormant/pending** (leave until the analytics-desk rework), **C = stale
docs/config/schema**. Everything in A was verified by absence of callers, not
by looks.

---

## APP

### A. Delete now

1. **`app/src/main/workflow/runner.js` — whole file.** `WORKFLOWS` is a frozen
   empty object; `listWorkflows()` always returns `[]`, `runWorkflow()` always
   throws. Its IPC channels (`workflow:list`, `workflow:run`) are exposed but
   called by nothing. Also remove: the import in `index.js:25`, handlers
   `index.js:379-394`, `preload/index.cjs:26-27`, the `runWorkflow?` field in
   `dashboard/src/components/agent/bridge.tsx:60-65`, and the
   `"workflow:done"` term in `run-rail.tsx:197`.
2. **The plan-approval path.** `plan:run`/`plan:confirm` handlers have zero
   dashboard callers and nothing ever launches the `plan` scope. In
   `workflow/plan-runner.js` keep only `OUTWARD_ACTIONS`/`INWARD_ACTIONS`/
   `isOutward` (lines 42-63 — `isOutward` is imported by the live
   `run-driver.js`); delete `runPlan`, `prepare`, `missingTarget`,
   `REFERENCE_LOOKUP` and the now-unused imports. Also remove
   `index.js:26,66,396-435,497-500`, `preload/index.cjs:28-30`, the
   `runPlan?`/`confirmPlanStep?` bridge fields (`bridge.tsx:50-59`), and the
   plan branches in `run-rail.tsx:48,131-132,174-183,196`.
3. **Zero-reference exports** (verified against app + dashboard):
   `paths.js:19 withinAppRoot` · `rank-schedule.js:77 stopRankSchedule` ·
   `crawler/index.js:27 crawlIsRunning` · `crawler/schedule.js:80
   stopCrawlSchedule` · `agent/tool-surface.js:10-50 MEELU_READ_TOOLS`
   (superseded by `READER_SAFE`) · `integrations/gsc/client.js:192
   siteTotalsDay`, `:226 listSitemaps` · `gsc/sync.js:36 searchSyncIsRunning`,
   `:109 requestIndexCheckStop` · `ga/sync.js:133 trafficSyncIsRunning` ·
   `agent/catalog.js:146 resolveTransport`.
4. **Dead config** in `config.js`: `MAX_TURNS` export (`MEELU_MAX_TURNS` —
   runner has its own local), and the `ENV_DEFAULTS` fields `model`,
   `dailyBudgetUsd`, `anthropicApiKey`, `resendApiKey` (all zero readers;
   `ANTHROPIC_API_KEY` itself still works via the env spread in runner.js).
5. **`crawlDir` option**: computed and passed into the harness twice, never
   read. `runner.js:383`, `index.js:135-137,215,273`.
6. **App catalog slimming** (`agent/catalog.js`): the only consumer reads
   `tools` + `readOnly`. Keep `github` and `searxng` entries (their fields do
   real work); delete the inert `mailbox` and `resend` entries (dashboard owns
   the real catalog — do NOT touch dashboard's copies).
7. Small: `connector-config.js:25` — drop `"mailboxSites"` from RESERVED (never
   written or read). `index.js:583-606` — the `mailboxAddressFor` stub ignores
   its argument and its `error` branch is unreachable; collapse it.
8. Cosmetic: drop the unused `export` keyword on `net.js MAX_OUTBOUND`,
   `site-record.js getSiteRecord`, `connector-config.js mailboxAccountFor`,
   `crawler/images.js IMAGE_PER_PAGE, probeImage`, `crawler/crawler.js
   MAX_PAGES`, `analytics-store.js MAX_SOURCE_ROWS`.

### B. Leave alone (and why)

- `analytics-store.js` + the eight `analytics:*` IPC handlers + preload
  exposure — genuinely called by the analytics desk UI today; pending that
  desk's rework. Its `engineState()` probes the deleted analytics-mcp's
  on-disk layout, so sessions report `engine: "missing"` until the rework.
- The mailbox `address` parameter chain — always null today, but it's the
  multi-mailbox routing that returns with per-site sending.
- `permissionGrants.always/.full` — looked dormant, is real
  (`agent-tasks.tsx:1163,1166`).
- Crawl/rank background schedules — env-gated by design, alive.

### C. Stale docs / config

- `app/README.md`: still describes the deleted mcp-server (lines 17-18, 29),
  a `MEELU_SERVER_AGENT` var nothing reads (22), spike files that don't exist
  (33-35), an `AGENT_APP.md` that doesn't exist (73), and a 3-method bridge
  that now has 46 methods (28). Rewrite.
- `app/.env.example`: nothing stale, but `MEELU_AGENT_MCP_URL` should be
  promoted out of the optional tail, and ~14 live vars are undocumented
  (auto-crawl/rank-check knobs, crawl concurrency, `MEELU_SHOT*`,
  `MEELU_SMOKE_SITE`).
- **Fix, don't delete**: `workflow/run-driver.js:6-16` `ACTION_DESK` names
  `"site-crawl"` (not a registered scope, no alias → would fail) and
  `"outreach-prospects"` (works only via alias); no entry maps the `"pages"`
  desk that the default workflow seeds. The default workflow is effectively
  broken until this table is corrected.
- `package.json` is clean — every dep and script is real.

---

## DASHBOARD

### A. Delete now

1. **`suggestions` slice — whole vertical.** Routes
   (`api/v1/suggestions/**`), `features/domain/suggestions/`, the
   `CollectionKey`/`TABLES` entries in `lib/store.ts:16,33`. Zero callers
   anywhere. Table drop → C.
2. **`diagnostics` / tool-error slice — whole vertical.** It was the deleted
   TS server's error sink: `api/v1/diagnostics/**`,
   `features/domain/diagnostics/`, `scripts/smoke-tool-errors.sh`. Table
   drop → C.
3. **`/api/v1/context` and `/api/v1/activity` routes** + `activity/service.ts`
   + `context/service.getContext` (lines 49-107) — MCP-server reads with no
   remaining caller. Keep `pushActivity` (still writes the trail) and
   `getStats` (served via `/api/v1/stats`).
4. **KEPT by decision (2026-09-08): do not delete.** The user intends to wire
   these up at some point. Original finding, for the record —
   **28 API routes with zero callers** (verified against UI + app workers) —
   each takes its uniquely-owned service function with it:
   `content/projects/[id]/free-slots`, `outreach/projects/[id]/known-prospects`,
   `seo/ai-visibility/prompts`, `seo/clusters` (base), `seo/clusters/keywords`,
   `seo/clusters/observed`, `seo/competitors/pages`, `seo/competitors/rankings`,
   `seo/competitors/serp`, `seo/keywords/[id]`, `seo/keywords/measure`,
   `seo/keywords/seed`, `seo/plans` (base), `seo/plans/[id]`,
   `seo/plans/summary`, `seo/results/detect`, `seo/results/measure`,
   `seo/runs/[id]`, `seo/runs/reap`, `site/chunks`, `site/crawl-jobs/reap`*,
   `site/pages/by-url`, `site/pages/keywords`, `site/search-data/changes`,
   `site/technical-seo/runs`, `site/technical-seo/runs/[id]`,
   `social/posts/[id]`, `social/publish`.
   Caveats: keep `site/crawl/service.reapCrawls` (called internally by the
   crawl-jobs route); keep `technical-seo` repository `updateRun` (internal
   use); keep `filters.ts`; delete the stale known-prospects hint string at
   `outreach/service.ts:281`. (*reap routes: see B — keep if wanted as ops
   hooks, they're the only judgment call in this list.)
5. **Four unlaunchable agent scopes** (no endpoint, no orchestrator entry, no
   alias): `ask/ask-content/`, `ask/ask-outreach/`, `social/content-week/`,
   `seo/issue-review/` + their import/map lines in `_shared/scopes.ts`
   (15,17,20,33 / 62,64,67,80).
6. **Dead components**: `components/agent/plan.tsx` (whole file, matches the
   app's dead plan path), `components/info-tip.tsx` (untracked, never wired),
   `AnimatedNumber` export in `animate.tsx:97`, `STATUS_HINT` in
   `content/content-page.ts:38`.
7. **Dead lib exports**: `calendar.ts weekDays, dayString` ·
   `current-site.ts isGlobal` · `embedder.ts EMBED_DIMENSIONS, passageInput` ·
   `integrations/dataforseo.ts llmBrandTarget` · `platforms.ts platformSeed` ·
   `_shared/connector-scope.ts optionalServerTemplate`.
8. **Dead domain exports**: `seo/clusters/repository getClusterByLabel,
   clustersDue` · `seo/findings/detectors DETECTOR_NAMES` ·
   `seo/keywords/repository getByKeyword, setCluster` ·
   `seo/plans/repository patchPlan` · `seo/results/measure daysBetween` ·
   `seo/runs/service beatRun` · `seo/vendor/repository volumeMonths` ·
   `site/pages/repository EXPORT_COLUMNS`.
9. **`toolsets` scope field — dead end-to-end** (the harness no longer reads
   it): remove from `_shared/lib.ts:24`, the scope route response,
   `ask-common.ts`, `scope-brief`, and the ~22 scope files that set it; then
   `_shared/tree.ts toolsetsFor/DOMAINS/BASE_DOMAINS` die too. Also delete the
   `subagents` type + serializer (no scope defines one). `borrowTools` waits
   for the analytics rework (its only setters).
10. **Stale smoke scripts** targeting deleted routes: `smoke-todos.sh`,
    `smoke-contacts.sh`, `smoke-ideas.sh`, `smoke-sites.sh`,
    `smoke-link-audit.sh`, `smoke.sh`, (`smoke-tool-errors.sh` in A2). Fix
    `smoke-site.sh` (one step hits `site/pages/by-url`).
11. **Unused deps**: `graphology`, `graphology-communities-louvain` (the
    deleted site-structure graph; pagerank is hand-rolled now).
12. Cosmetic: ~40 redundant `export` keywords on file-local helpers/constants
    (full list in the audit transcript; zero risk, low value).

### B. Leave alone (and why)

- **Analytics desk, all of it** — UI pages, `api/v1/analytics/**`, domain
  service/repository, the three agent scopes. Two notes for the rework:
  `analyze-report` has no launcher at all, and `analyze-data/prompt.ts` still
  spawns the deleted `meelu-analytics-mcp` — that scope cannot start today.
- `verification` table (better-auth needs it), `_shared/tree.ts writesFor`
  (one live caller), reap endpoints if you want operator escape hatches.

### C. Stale docs / config / schema

- **Docs still selling the deleted TS server**: `mcp-catalog.ts meeluServer`
  (`npx -y meelu-mcp`) + `meeluConfigJson`/`meeluCommand`, the whole
  `docs/meelu` install page, the settings-page "Connect your coworker (MCP)"
  panel, `dashboard/API.md:6`, `dashboard/README.md:5,22`, and root
  `CLAUDE.md:168` ("we define mcp server in mcp-server/src/domains" —
  contradicts the header of the same file). These should describe agent-mcp
  (streamable HTTP at `MEELU_AGENT_MCP_URL`).
- **The big one — scope prompts naming dead tools**: only ask-seo and
  ask-site were migrated to the new write-tool names. Every other scope's
  `writes`/`createToolName`/prompt text names tools that no longer exist —
  59 distinct dead `meelu_*`/`content_*`/`social_*`/`outreach_*` names across
  seo/plan, seo/keyword-research, site/issue-review, site-pages,
  profile-setup, prompt-chips, and all content/social/outreach/workspace
  scopes. This is the desk-by-desk rework, not a deletion — but until each
  desk is migrated, its agent actions are broken on purpose (fail-safe:
  denied writes).
- **Schema drops at next squash**: `tool_error` (after A2), `suggestions`
  (after A1). Everything else has a live reader. Also: seven untracked
  migrations (0053-0059) + modified journal — squash before adding these
  drops.
- `GSC`/`GA4` catalog entries keep placeholder `transport` — vestigial but
  load-bearing (they drive the OAuth connect buttons); fine as is.

---

## Suggested order of attack

1. App A1-A8 + dashboard A1-A11 — mechanical deletions, each independently
   verifiable (`node --check`, `tsc --noEmit`, both smoke suites after).
2. Fix `run-driver.js ACTION_DESK` (broken default workflow) while in there.
3. Rewrite the two READMEs + docs/settings MCP panels for agent-mcp.
4. Desk-by-desk scope migration (C2 dashboard) — separate effort, per desk.
5. Schema drops + migration squash last, once A1/A2 land.
