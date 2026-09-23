We have four components

1. api : the backend (Python, FastAPI, SQLAlchemy, Alembic, uv-managed). Stores data, owns the schema, exposes the REST apis, and runs the embedding worker as its own process. The apis serve the UI; the agent does not read through them.
2. agent server : `api/src/agent`, a second entrypoint of the same codebase (`src.agent.app`, the `agent` compose service, MCP over streamable HTTP at /mcp). It gives the agent direct SQL over Postgres (RLS-scoped, read-only on canonical tables, a per-user workspace schema for derived work), the deterministic analytics algorithms, guide prompt tools, and each desk's write tools — a desk's `tools.py` registers on the shared FastMCP instance and calls that desk's own service.
3. dashboard : web UI (Next.js frontend only; every /api path it serves is a rewrite to api).
4. App : electron app that renders the same dashboard.. The app also has agent harness that uses claude sdk.. the harness runs locally and connects to the agent server over HTTP.. some external mcp servers can be installed as well. Crawling, page analysis, GSC/GA fetching and the schedules run locally in the app and talk to api over HTTP. Every shared third-party data vendor (DataForSEO, Apify, and whatever comes next) lives in the api under `api/src/providers`, keyed by ONE server-side account per vendor (`DATAFORSEO_*`, `APIFY_TOKEN` in settings). One facade per domain (`seo_data`, `social_search`, `prospect_sources`) holds an ordered adapter list — primary first, fallbacks after — and the user never picks a vendor. `ProviderFacade.fetch` is the only path to a vendor: it looks the normalized request up in `provider_cache` first, otherwise walks the adapters in order, caches the response with a per-capability TTL, logs the call in `provider_call`, and charges the user's credit balance (`api/src/credits`, USD micros; the vendor's reported cost by default, `credits/pricing.py` overrides). The seo-data facade is exposed as MCP tools tagged `meelu/provider` on the agent server, which the app runner allows only when the scope lists that domain in `providers`; the social and prospect facades are REST endpoints the app's local pipelines call. GA4, GSC and mailboxes stay user-specific and stay in the app (`app/src/main/integrations`). Page classification (`api/src/site_page_llm_extraction`) runs on the server: when a crawl settles as completed, a background loop walks every page whose content hash has no fresh row and asks the `json_data_extractor` facade (OpenRouter's TypeSafe Jev decision model, `OPENROUTER_API_KEY`) a fixed set of choice questions; add a question there to extract more per page.
dashboard and App look same. only difference is App has agentic actions.
The Content desk writes and checks pieces only. Meelu never posts, schedules or tracks what went out; the user publishes by hand or through an external scheduler (optionally exposed to the agent as an MCP server), and the api holds only the text they wrote.

## Agent scoping lives in the app, not on the MCP server

The agent server is one plain MCP server. It registers every tool once and
`tools/list` returns all of them, every time, to every caller. It does no
per-desk filtering, reads no scope header, and knows nothing about which desk
launched a task. Each tool carries two facts in its MCP `_meta`: `meelu/desk`
(the desk that owns it, absent for shared tools) and `meelu/writes`.

The scope API (`GET /api/v1/agent/scope`) is the only source of scope: the
system prompt, the tables and guides, the authorised writes, and the desks the
model may add. It never lists read tools and never needs the tool catalog.

The app runner (`app/src/main/agent/runner.js`) is the middleware that joins
the two. Per task it opens ONE session with the SDK (streaming input, one CLI
process, one MCP handshake) and keeps it alive across the user's turns. Before
the model runs it fetches the scope, reads the tool catalog once, computes the
allowed set (shared reads, plus reads tagged with a loaded desk, plus the
scope's writes) and hides everything else with `disallowedTools`. `add_desk` is
a local tool that only appends to the session's desk list; the runner notices
the list changed, fetches the scope again, rebuilds the prompt and the hidden
list, and continues the same session. Never add per-desk logic to the MCP
server, never open a second MCP connection per desk, and never re-handshake
on an ordinary turn.

## The agent server owns all analytics

analytics-mcp (the local stdio/DuckDB CSV tool the `api/src/data_analytics/algorithms`
package was copied from) is **not part of this project** — it lives one
directory above the repo as its own thing. Everything analytical here is the
agent server's job.
Never re-import analytics-mcp, add it as a dependency, or extract a shared
algorithm package to deduplicate against it: the copies diverge freely, and
coupling this repo to an external tool's release cycle is worse than any
duplication. The analytics desk in the dashboard still references the old
local tool and is pending rework.

## Nothing is in production

There is no deployment, no users, and no database anywhere that has to survive
a change. **Do not write backward-compatible code.** When something is wrong or
obsolete, change it outright:

- Rename and drop columns and tables freely. No deprecation window, no
  keeping a dead column "so old rows still parse".
- No compatibility shims, no `legacy_*` fallbacks, no reading both an old and
  a new shape. One shape, the current one.
- When a feature is cut, delete it — the table, the API routes, the service,
  the MCP domain and the comments that reference it. Leaving a table behind
  "just in case" is what makes the schema unreadable.

## A desk owns one vertical slice, and nothing outside it

A desk is its tables, the API routes over those tables, and the `tools.py` whose
MCP tools call only that desk's service. That is the whole of it. **No tool reaches into
another desk's data.** If a capability needs rows from somewhere else, it is not
that desk's tool — it belongs in the domain that owns the rows, or in a domain
of its own.

The temptation is always the same: a desk needs one field from a neighbour, so
its tool joins across. Then the neighbour renames a column and a tool three
desks away breaks, for a reason nothing in its own directory explains. A desk
whose slice is vertical can be read, changed and deleted on its own; one that
reaches sideways cannot be read without reading everything.

The agent is what crosses desks, not the code. It already holds every read tool
it was scoped, and installing another MCP server adds more — the analytics
engine, a mailbox, a search provider. Combining them is the agent's job and it
needs no help: a question that spans the corpus and a CSV is answered by calling
one desk's download tool and the engine's query tool in the same turn. **Do not
write a tool to pre-combine what the agent can combine itself.** The Analytics
desk is the example to copy — its domain saves sessions, transcripts and
reports, and reads nothing it does not own.

## Bulk data leaves as a file path, never as tokens

A tool that hands rows to the model is bounded by what a conversation can hold.
Anything that could be thousands of rows — the page corpus, a link graph, a
keyword export — does not come back as data. **The MCP server walks the pages
itself, writes a CSV under `MEELU_DATA_DIR`, and returns the path.** The model
sees a filename and a row count; the rows never enter its context.

`meelu_site_download_data` is the shape to copy. From there the path goes to
the Analytics desk, whose engine ingests CSVs into DuckDB and answers questions
over them for the cost of one session.

The consequence is a rule about where analysis lives: **a desk that owns data
does not answer analytical questions about it.** Counting, averaging, grouping,
trends and "which section has the most of X" are endless, and each one answered
in-desk costs another walk through the corpus. The desk offers the download and
names the Analytics desk; it does not page through its own tables to compute a
number, and it does not read the CSV back.

## Never write comments in code

Do not add comments unless the user explicitly asks for them. Not a header
block, not a "why this is here" line above a function, not a section divider.

The code is read by agents far more than by people, and a comment is the one
thing in the file that nothing verifies. Types are checked, tests run, dead
imports get flagged — a sentence claiming a deleted surface still exists
survives every one of those and is believed by the next model to open the file.
A wrong comment does not fail loudly; it just seeds a false premise. That is
the same failure documented below for tool names, except it applies to every
claim in every file.

Name things so the code says it. If a line genuinely cannot be understood
without prose, that is a signal to rename or restructure, not to annotate.

Load-bearing pragmas are not comments in this sense and stay:
`// eslint-disable-*`, `@ts-expect-error`, `biome-ignore`, `prettier-ignore`,
shebangs.

## Never name a tool you are not certain is there

**Default to describing the capability, not naming the tool.** Write "the
website record", "the desk that reads pages", "save it once the user agrees" —
not `meelu_website_details`, not `seo_study_start`.

A prompt is written once and then read by every agent that inherits it, and the
tool list underneath it changes constantly: domains get split, tools get
renamed, a scope narrows its `toolsets` and two thirds of the surface
disappears. A named tool that is no longer registered does not fail loudly. The
model believes the sentence, tells the user it cannot do the thing, and points
them at a tool that does not exist — which reads as the agent being obstinate
rather than the prompt being stale. That has already happened here: the profile
agent refused to read a website and referred the user to a tool it had never
been given.

The exception is narrow: **you may name a tool the prompt actually instructs
the agent to call, and only if the scope guarantees it is there** — its own
`writes` (the harness passes those as `MEELU_SCOPED_WRITES`), and reads whose
domain the scope lists in `toolsets`. A step the model must actually perform —
"read the method first", "save it once with X" — needs the real name, because
"there is a tool for this somewhere" is not something a model can act on.

Naming a tool is therefore a PROMISE that the scope registers it. Anything the
prompt merely mentions in passing — another desk's tools, a capability you are
pointing at rather than invoking — gets described, never named.

When a prompt needs to send the user somewhere else, name **the desk or the
screen**, not the tool: "that lives on the Website profile screen", "auditing
pages is the Pages desk". Those survive a rename; tool names do not.

### Migrations

Tables are declared in `api/src/models`, one class per table, and every
schema change ships as an Alembic revision under `api/alembic/versions`
(`cd api && uv run alembic revision --autogenerate -m "<what changed>"`,
then `uv run alembic upgrade head`). The `migrate` compose service runs
`alembic upgrade head` before anything that reads the database starts.

Because nothing is deployed, squashing is always available: collapse the
revisions into one baseline, then `docker compose down -v` and rebuild from
empty. Prefer that over accumulating migrations that only ever run against
throwaway databases.

### Local database

Postgres is published on loopback at `POSTGRES_PORT` (5434 — 5432 and 5433 are
taken by other projects on this machine), straight from `docker-compose.yml`.
A plain `docker compose up -d` is enough for TablePlus or psql to connect:

```bash
psql postgres://craftmate:$POSTGRES_PASSWORD@localhost:5434/craftmate
```

### Basic Implementation Architecture.
1. Database tables for a entity. we define tables in api/src/models, one class per table, and migrate with Alembic (api/alembic).
2. Each feature is a package under api/src (e.g. api/src/site_pages) with endpoints.py (thin, no business logic), service.py (business logic; may commit at safe checkpoints of long operations), repository.py (db access only, flush not commit) and schemas/ (pydantic). get_db owns commit/rollback.
3. api/src/app.py mounts the feature routers under /api/v1; the app and the dashboard frontend depend on the response JSON shapes, route paths, the `x-api-key` contract and the `x-meelu-site` header.
4. The agent reads those tables through the agent server's direct SQL surface (`api/src/agent`, RLS-scoped, read-only on canonical tables); writes go through each desk's `tools.py`, which calls the desk's service directly — never raw SQL, never HTTP back to the api.
5. dashboard/src/app/dashboard is a frontend UI.
6. app folder is a electron app, which renderes the dashboard as well as it has some local processes like crawling, agent harness etc.

### Adding a new feature. Strictly follow this.
1.Define the scope of feture with developer human.
2. Decide what tables to create and columns in those tables. this defines what data for a particular feature we will store in database
3. implement the database schema, ask user for review.
4. implement repository and service and api for crud operations. test all apis are working by writing integration tests.
5. decide the scope of mcp tools to expose with human and then implement them.
6. implement the app changes, prompt chips, buttons etc.

### Guidelines
repository file should simply contains the crud operation on db tables. It shoudld not have any domain logic.
each subfeature should be a package with its service and repository file.
service code should contain the business logic related to that, the pacakage can also contain some extra files that are imported by service
to avoid have service file too large.
e.g refer api/src/keys , api/src/sites for the shape.

### writing the apis 
Idea is simple.. If we have a table A. we try to write four types of api.
Get --> get a particular row by id, or other unique element. e.g page url. so we can have multiple get apis based on what unique elements we have.
post -> add a new entry by id
update --> update the entry by id
delete --> delete the entry by id.
if there is another unique element, its better to get it first, extract the id, then call other apis by id only.
list --> list multiple rows with paging.. this can take various filtering arguments with most of them null, as well as support free form search if required.

beyond this, if there is any other action supported by service related to business logic, it generally has a post api corresponding to it. but above mentioned apis
pretty much are applicable in every place.

### Writing mcp tools.
Thing with mcp tools is that we dont want to have one to one mapping for every api. 
It depends on domain knowledge of the feature you are implementing.. 
for apis we can afford to have multiple apis created , even if we dont use it. But for mcp tools, those will live in llm context window, so we should only add those mcp tools which are truly required.

Tool descriptions sit in the model's context on every turn, so every sentence
is paid for on every call. Keep them extremely concise: two or three sentences
saying what the tool does and any rule the agent must follow to use it right.
No examples, no restating the input schema, no desk-level prose — that belongs
in the domain guide. Input `.describe` strings follow the same rule: a phrase,
not a paragraph.
