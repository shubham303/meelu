# Plan: one MCP server, scoping done in the app

## Goal

The agent server lists every tool it has. It does no filtering. The app builds
the prompt and the tool list for each turn from the AgentScope response. The
app hides every tool that the scope does not allow. One MCP server, one
connection per turn, no extra connections when a desk is added.

## Facts this plan rests on

Measured on this machine and checked against the docs:

1. Each `query()` call in the Claude Agent SDK starts one CLI process. That
   process does one MCP handshake with the agent server: `initialize`,
   `tools/list`, `prompts/list`, `resources/list`. A call with `resume` is a
   new process and a new handshake. Today every turn already does this, so
   the plan adds no connections.
2. The agent server runs FastMCP with `stateless_http=True`. Every HTTP
   request is independent. There is no session to keep or to lose.
3. `disallowedTools` with bare tool names removes those tools from the
   request to the model. The model never sees them. Verified: 54 tools
   became 51 when three names were passed. `allowedTools` only auto-approves
   and hides nothing. Hooks and `canUseTool` block at call time and hide
   nothing.
4. FastMCP `@mcp.tool(meta={...})` puts the dict on the wire as the tool's
   `_meta` field. The MCP spec defines `_meta` on every Tool object. Prefixes
   other than `mcp` and `modelcontextprotocol` are free for us to use.
5. The Agent SDK does not hand `_meta` to app code. `mcpServerStatus()`
   returns tool names and a few annotations only. So the app reads the
   catalog itself with one `tools/list` request, not through the SDK.
6. The Anthropic prompt cache is built in the order tools, system, messages.
   A change to the tool list or the system prompt invalidates the cache from
   that point. Adding a desk changes both. That cost is accepted.

## What each part owns

Agent server (`api/src/agent`)
: Registers every tool once with two tags in `_meta`: `meelu/desk` (the desk
  that owns it, or absent for shared tools) and `meelu/writes` (true or
  false). Serves `tools/list` with all of them. No header filter, no
  `scoping.py`, no `x-meelu-scope`.

Scope API (`api/src/agent_scope`, `GET /api/v1/agent/scope`)
: Given an action and the desks added so far, returns: the desk names loaded,
  the write tool names allowed, the system prompt, the desk offers, limits,
  providers, connector server templates. It does not list read tools and
  does not need the tool catalog.

Runner middleware (`app/src/main/agent/runner.js`)
: Before every model call: fetch the scope, fetch or reuse the tool catalog,
  compute the allowed set, compute the hidden set, build the system prompt,
  start the query with `disallowedTools`. This is the only place that joins
  scope and catalog.

## The rule for the allowed set

A tool is allowed on a turn when one of these holds:

- It has no `meelu/desk` tag and `meelu/writes` is false. These are shared
  reads: `run_sql`, `find_plans`, `get_plan`.
- Its `meelu/desk` tag is one of the loaded desks and `meelu/writes` is
  false. These are the desk's reads, for example `search_page` on pages.
- Its name is in the scope's `writes` list. Writes are always explicit.

Everything else in the catalog goes into `disallowedTools`.

The analytics desk already exists with three actions. The 30 analytics
engine tools get `meelu/desk: analytics`. After that, a pages chat holds 7
tools instead of 45. Loading the analytics desk brings the engine tools in.

## Complete flow

### 0. Server start

1. The agent container imports every `tools.py`. The `@tool(writes=,
   desk=)` decorator calls `mcp.tool(meta={"meelu/desk": desk,
   "meelu/writes": writes})`.
2. FastMCP serves `/mcp/`. `AuthMiddleware` checks `x-api-key` and
   `x-meelu-site` only.

### 1. User opens a desk chat and sends the first message

1. The renderer sends action, site id, message, form draft, files to the
   main process. No session id yet.
2. Runner: `sessionDesks` for this session is empty.
3. Runner calls `GET /agent/scope?action=ask-pages` with the site header.
   The api returns `desks: ["pages"]`, `writes: [save_note, update_note,
   delete_note]`, the system prompt with tables and guides, and the desk
   offers.
4. Runner gets the catalog. It sends one `tools/list` request to the agent
   server with the MCP client from `@modelcontextprotocol/sdk` (already a
   dependency of the Agent SDK). The server is stateless, so this is one
   POST. The result is cached in memory per agent URL for the life of the
   app. The cache is dropped when a tool call fails with an unknown tool
   name or when the agent server restarts.
5. Runner computes allowed and hidden with the rule above. For pages:
   allowed is run_sql, find_plans, get_plan, search_page, and the three note
   writes. Hidden is the other 46 names, prefixed `mcp__meelu__`.
6. Runner builds the system prompt: the scope prompt, then the shared
   blocks (web tools, reader, site, writes, read-only, other desks).
7. Runner starts `query()` with: the meelu server config (api key and site
   headers, `alwaysLoad: true` so the small allowed list is always in the
   request), `disallowedTools` = hidden, the reader subagent with the
   allowed reads, `canUseTool` as a second gate that denies anything not
   allowed and asks the user before a write.
8. The CLI process connects to the agent server once, lists tools, drops
   the hidden ones, and calls the model with 7 meelu tools.
9. The model answers. Tool calls go to the agent server as normal. The
   runner emits text, tool, wrote, created, and done to the renderer.

### 2. A later turn on the same desk

Same as above with `resume: sessionId`. New process, one handshake, same
scope, same catalog from cache, same prompt and tool list. The prompt cache
hits because nothing in tools or system changed.

### 3. The model needs another desk

1. The system prompt lists the other desks. When the request needs a write
   or a tool that another desk owns, the model calls `add_desk` with the
   name. It does not ask permission.
2. The `add_desk` handler adds the name to `sessionDesks` and to the turn's
   `addedDesks`, and tells the model to end its reply in one line.
3. The turn ends. The runner sees `addedDesks` is not empty and does not
   emit done. It loops: same session id, a hidden continuation message
   ("the content desk is now loaded, continue").
4. The loop fetches the scope again with `desks=content`. The api merges
   the content desk's writes, tables and guides into the response.
5. Allowed is recomputed with desks pages and content. Hidden shrinks.
   The system prompt grows. The query resumes with the new
   `disallowedTools`. This is one new process and one handshake, the same
   as any turn. The prompt cache misses once, on this turn only.
6. The model continues the user's request with the content tools and
   finishes. The runner emits one done for the whole turn. At most three
   such resumes per turn.

### 4. Every later turn in that session

`sessionDesks` still holds content. Every scope fetch passes `desks=content`
so the prompt and the tool list stay the same from here on, and the cache
hits again.

## Changes, file by file

api/src/agent/server.py
: `tool()` passes `meta` to `mcp.tool()`. Keep `READ_TOOLS`, `WRITE_TOOLS`
  and `TOOL_DESKS` for the registry's own checks.

api/src/agent/scoping.py
: Delete. Remove `scoping.install()` from `app.py`. Already done in the tree.

api/src/agent/auth.py and context.py
: Drop the scope header and the `scope` field. Already done in the tree.

api/src/data_analytics/tools.py
: Every `@tool()` becomes `@tool(desk="analytics")`. Already done in the
  tree.

api/src/agent_scope/registry.py
: Remove the `data_analytics`, `agent.tools.core` and `agent_plans` imports
  that I added, and the `all_tool_names` and `allowed_tool_names` helpers.
  The api does not need the catalog. Keep `DESK_NAMES`, `desk_addition`,
  `desk_writes`.

api/src/agent_scope/schemas.py and service.py
: Response gains `desks_loaded: list[str]`. Remove `write_tools`,
  `reader_tools`, and the `tools` and `all_tools` fields I added.

api/tests/integration/agent_scope/test_scope.py
: Replace the scoping test with one that checks `desks_loaded` and `writes`
  merge when desks are added.

app/src/main/agent/runner.js
: Add `catalog.js` next to it: `listAgentTools(url, headers)` with an
  in-memory cache. In `runQuery`: compute allowed and hidden, pass
  `disallowedTools`, drop the `x-meelu-scope` header, derive the reader's
  tools from allowed reads, change the `canUseTool` gate to "not allowed"
  instead of "is a write outside the list".

app/package.json
: Add `@modelcontextprotocol/sdk` as a direct dependency.

Prompts
: Fix the phantom tool names in pages (`search_page`, `run_sql`),
  issue-review (`reject_issue`, `restore_issue`, SQL over `site_issues`),
  compose-reply (`profile` table). Outreach and analytics prompts keep their
  pending names per the 2026-09-12 decision until those desks get tools.

## What stays the same

- One MCP server process. One handshake per turn, as today.
- `add_desk`, the session desk memory, and the automatic resume.
- The renderer and the dashboard bridge. The `scope` event shape does not
  change.
- Row-level security and the read-only role on canonical tables.

## Risks

- Security for tool access moves to the app. A holder of a workspace API
  key can call any tool on the agent server directly. Writes were only
  header-gated before, with a value the client chose, so nothing real is
  lost. Rows stay protected by Postgres.
- The catalog cache can go stale if a tool is added while the app runs. A
  denied unknown tool drops the cache and the next turn refetches.
- With `alwaysLoad: true` the meelu tools sit in the cached prefix. Any
  change in the allowed list invalidates the cache. That only happens when
  a desk is added.
- The reader subagent on non-analytics desks loses the four engine tools it
  carries today. It gets them back when the analytics desk is loaded.

## Verification

1. Run the capture harness on the pages desk: the request must show 7 meelu
   tools and no engine tools.
2. Send a message that needs content. The model calls `add_desk`, the
   runner resumes, the second request shows `content_create_piece` and the
   content tables in the prompt.
3. Agent server log: one `tools/list` per turn, none extra.
4. `uv run pytest tests/integration/agent_scope` passes.

## Implemented on 2026-09-14

- Agent server: `scoping.py` deleted, scope header gone, every desk's
  `tools.py` imported in `app.py`, desk tag and write flag on each tool's
  `_meta`. `tools/list` returns all 53 tools to every caller.
- Scope API: returns writes, prompt, offers. Each offer carries a `brief`:
  the text the model receives when it loads that desk (its writes, tables
  and guides). No tool lists.
- Runner: one `LiveSession` per task (streaming input, one CLI process, one
  MCP handshake). `catalog.js` reads the catalog once per app run. Hidden
  tools are applied with `applyFlagSettings({permissions: {deny}})` right
  after the process starts and before the first message. `add_desk` adds the
  desk to the session list, fetches the merged scope, recomputes the hidden
  list, applies it the same way, and returns the desk brief as the tool
  result. The model's very next call in the same reply has the new tools.
  No restart, no handshake, no continuation message.
- Measured: two turns on the pages desk, one `tools/list` from the CLI, 7
  meelu tools instead of 45. Scripted `add_desk content`: the next model
  call shows 12 meelu tools including the five content writes, still one
  handshake.
- Two SDK facts that shaped this: the `disallowedTools` and `settings`
  options are permanent layers that later calls cannot lift, so the initial
  hide must also go through `applyFlagSettings`. And the system prompt
  cannot change on a live process, so the added desk's tables and guides
  travel in the tool result, not the prompt.

## Tests that guard this

- `api/tests/unit/agent_scope/test_tool_catalog.py`: every tool carries the
  meta tags, all engine tools sit on the analytics desk, only three reads are
  shared, the pages desk resolves to seven tools, every scope's writes are
  registered writes, and no prompt names a tool its desk cannot call.
  Update `PENDING_TOOL_NAMES` there when the outreach and analytics desks get
  real tools.
- `app/test/agent/runner-scoping.test.js`: drives the real runner against a
  fake scope API, a fake MCP server and a fake model, no Docker. Asserts one
  MCP handshake across three turns, the exact tool list per desk, the system
  prompt sent to the model, and that `add_desk` unhides tools on the next
  call without a new handshake. Update `CATALOG` and `SCOPES` in `fakes.mjs`
  when desks or tools change.
