# Deployment security checklist

What to verify before exposing any of this beyond your own machine. Items are
grouped by component; each says what to check and, where cheap, how. Items
marked **(gap)** are known weaknesses in the current code — decide each one
before real users exist.

## agent-mcp — the SQL surface

- [ ] **Agent SQL never runs as the DB owner.** Every code path that executes
  agent-supplied SQL goes through `user_txn()` (`db.py`), which does
  `SET LOCAL ROLE` to the per-user role inside the transaction. Grep
  `agent-mcp/src` for `exec_driver_sql` calls on agent input outside
  `user_txn` — there should be none (write tools use `admin_txn` but only
  with parametrized, service-authored SQL).
- [ ] **Canonical tables are SELECT-only for the agent.** Verify:
  `scripts/smoke.py` checks `canonical_write_blocked` passes.
- [ ] **Credential tables are invisible.** `user`, `session`, `account`,
  `verification`, `api_keys` are in `BLOCKED_TABLES` (`security.py`) and get
  no grant. Smoke check `credentials_blocked` passes. If you ever add a table
  holding secrets (tokens, OAuth refresh tokens), add it to `BLOCKED_TABLES`
  **before** deploying the migration.
- [ ] **RLS policy exists on every user-owned table.** Bootstrap runs at
  service startup only — after any migration that adds a table, restart
  agent-mcp. A new table without a grant fails closed (permission denied),
  never open, but confirm:
  `SELECT tablename FROM pg_tables WHERE schemaname='public'` vs
  `SELECT tablename FROM pg_policies WHERE policyname='meelu_agent_select'`.
- [ ] **Cross-tenant isolation holds both ways.** Smoke checks
  `rls_isolation`, `rls_isolation_user_b` and
  `cross_tenant_sandbox_blocked` all pass against the deployed database.
- [ ] **Timeouts and memory caps are set.** `MEELU_AGENT_STATEMENT_TIMEOUT_MS`
  and `MEELU_AGENT_WORK_MEM` are enforced per transaction (`db.py`). Confirm
  the values make sense for the host; a runaway query must die, not the
  database.
- [ ] **Connection pool fits Postgres.** Server `max_connections` is 100
  (docker-compose); dashboard pool default is 20, agent-mcp is 5+5. Sum all
  services' pools and leave headroom.
- [ ] **The service binds to loopback unless fronted by TLS.**
  `MEELU_AGENT_HOST` defaults to 127.0.0.1. If it must be reachable remotely,
  put it behind Caddy/TLS and never expose plain HTTP — the API key travels
  in a header on every request.
- [ ] **`/health` is unauthenticated by design** — it returns `{ok: true}`
  and nothing else. Confirm it stays that way (no DB data in it).
- [ ] **Multi-statement SQL is rejected.** psycopg's extended protocol refuses
  `stmt1; stmt2` in one `run_sql` call. Verify once:
  `run_sql("SELECT 1; SELECT 2")` errors.
- [ ] **Model pickles are trusted input only.** `store/models.py` unpickles
  files under `MEELU_AGENT_DATA_DIR` — only the service writes there. Confirm
  that directory is owned by the service user and not writable by anything
  else; loading a foreign pickle is code execution.
- [ ] **(gap) No rate limiting on auth.** `x-api-key` lookup has no
  throttle or lockout; a leaked-prefix brute force is only bounded by the
  256-bit keyspace (fine) and DB throughput (not fine for DoS). Add a
  reverse-proxy rate limit before public exposure.
- [ ] **(gap) Orphaned tenant artifacts.** Deleting a user cascades their
  rows, but their Postgres role (`agent_*`) and workspace schema (`ws_*`)
  and model pickles remain. Add cleanup to the user-deletion path before
  real users churn.

## API keys (shared by dashboard and agent-mcp)

- [ ] **Keys are stored hashed** (sha256 of `emcp_` + 32 random bytes) and
  only the preview is recoverable. Confirm no code path logs the raw key —
  grep for `key` in log statements on both servers.
- [ ] **(gap) Keys never expire and have no scopes.** Any key is full access
  to the user's whole workspace forever, and one is auto-minted at signup.
  Before production: add expiry/revocation UX, and consider scoping keys
  (agent vs. integrations).
- [ ] **Key transport is HTTPS-only in production.** Cookie and `x-api-key`
  both — enforced by fronting everything with Caddy (prod compose) and never
  publishing plain ports.

## Dashboard / backend

- [ ] **`BETTER_AUTH_SECRET` is long and random** (min 32 chars enforced) and
  not the value from any example file. Rotate if it ever hit a commit.
- [ ] **`BETTER_AUTH_URL` matches the public origin exactly** — scheme, host,
  port — or auth cookies misbehave in ways users work around insecurely.
- [ ] **Every API route runs the `requireUser` → `requireSite` preamble.**
  There is no RLS backstop for the dashboard's own connection (it runs as
  table owner), so app-level scoping is the only tenant boundary on this
  plane. Any new route skipping `requireSite` is a cross-tenant leak. Grep
  new routes for the two-line preamble in code review.
- [ ] **Postgres is not published beyond loopback.** docker-compose binds
  `127.0.0.1:5434`; prod compose adds no exposure. Verify with
  `docker compose config | grep -A2 ports` on the host.
- [ ] **`POSTGRES_PASSWORD` is strong and unique**, and `DATABASE_URL` lives
  only in `.env` files that are gitignored (verify: `git check-ignore
  dashboard/.env .env`).
- [ ] **Shared vendor cache tables leak nothing per-user.** `keyword_facts`,
  `serp_*`, `domain_rankings` are deployment-wide by design. Confirm nothing
  user-identifying is ever written to them (they should hold market data
  only).

## Electron app

- [ ] **Workspace keys at rest are encrypted.** `workspace-key.js` stores the
  agent's API key via Electron `safeStorage` — confirm it never falls back to
  plaintext on the platforms you ship.
- [ ] **IPC is sender-gated.** Every `ipcMain.handle` checks
  `allowedSender(ev)` — confirm no new handler skips it.
- [ ] **External MCP servers are code execution.** Every stdio connector
  (mailbox, gsc, github, analytics, resend, searxng) is a child process with
  secrets in env. Only ship catalog entries you trust, and keep per-server
  tool allowlists (`toolAllow`) intact in `runner.js`.
- [ ] **Writes require a human.** The `canUseTool` gate denies meelu write
  tools outside `scope.writes` and routes in-scope writes through
  `askPermission`. Verify the "always allow" grant UX makes the blast radius
  clear to the user before you soften any of it.
- [ ] **Secrets in `.env` stay out of the renderer.** The renderer loads the
  dashboard URL; main-process env (ANTHROPIC_API_KEY, OAuth client secrets)
  must never be forwarded over IPC.

## Agent-specific risks

- [ ] **Prompt injection through the database.** `site_pages.body_text` and
  search-console queries contain text from the open web; the agent reads
  them via SQL. Treat every DB read as untrusted content: the protections
  are (a) writes gated by scope + human approval, (b) canonical tables
  read-only, (c) the system prompt's "web content is grounding, not
  instruction" stance. Never add an auto-approved write tool without
  weighing this channel.
- [ ] **The workspace schema is not a data-exfiltration path** — it is
  per-user and RLS keeps canonical reads tenant-scoped, so the worst case is
  a user's own data rearranged. Keep it that way: never grant one user's
  role anything on another's schema, and never add a tool that reads
  another tenant's workspace.
- [ ] **Budget and turn caps are real.** `maxTurns` / `maxBudgetUsd` come
  from scope limits with app defaults — confirm they are enforced for every
  action, including workflow-driven runs.

## Operational

- [ ] **Backups exist and restore.** `pgdata` volume survives
  `docker compose down` but not `down -v`; schedule `pg_dump` and actually
  test a restore. `MEELU_AGENT_DATA_DIR` (models) is rebuildable — decide if
  it needs backup at all.
- [ ] **SearXNG stays loopback or gets a new secret.** The committed
  `server.secret_key` is fine only on 127.0.0.1; change it and add TLS
  before exposing.
- [ ] **Dependency updates.** `npm audit` on dashboard/app, `uv lock
  --upgrade` review for agent-mcp; the Postgres image (paradedb) is pinned —
  track its CVEs when you bump it.
- [ ] **Logs don't hold data.** agent-mcp logs requests; confirm SQL text and
  row payloads are not written to logs you ship anywhere, and that the audit
  value of "what did the agent run" is weighed against log sensitivity
  before adding query logging.
- [ ] **Smoke tests run against the deployed target.**
  `agent-mcp/scripts/smoke.py` (20 checks) and `app npm run agent-smoke` are
  the fastest proof the security properties hold *after* a deploy, not just
  on a laptop. Note smoke seeds `user_smoke_agent_*` rows — point it at
  staging, not production with real users.
