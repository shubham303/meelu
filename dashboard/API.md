# Meelu REST API (v1)

The REST endpoints of the Meelu api (`../api`, FastAPI). The dashboard and
the desktop app call them. The agent does not: it reads the database through
the agent server and writes through each desk's MCP tools.

This is a map. For request and response fields, see the OpenAPI page at
`/docs` on the api (for example `http://localhost:8100/docs`). Routes are
mounted in `api/src/app.py`; each feature has its own `endpoints.py`.

## How the dashboard reaches the api

`next.config.ts` rewrites `/api/auth/*` and `/api/v1/*` to `MEELU_API_URL`
(default `http://localhost:8100`).

Paths like `/api/agent/ask-seo` in the dashboard code are not HTTP routes. The
dashboard takes the last part of the path (`ask-seo`) as an action name and
gives it to the desktop app's agent bridge. In a plain browser, agent tasks do
not run.

## Conventions

### Authentication

Every `/api/v1` endpoint needs one of these:

- the `meelu_session` cookie, which `POST /api/auth/session` sets, or
- an `x-api-key` header with a workspace API key (`emcp_...`), or the same
  key as `Authorization: Bearer emcp_...`. Keys are managed in Settings.

If neither is valid, the answer is 401. Two endpoints are for Meelu operators
only and answer 403 to other users: `POST /credits/grant` and
`POST /credits/sweep`. The Dodo payment webhook needs no auth.

### Which website a request is about

Most endpoints work on one website. Send its id in the `x-meelu-site` header,
or as `?siteId=`.

- If the workspace has exactly one website, you can leave the header out.
- If it has several and the request names none, the answer is 400.
- If it has none, the answer is 400 and tells you to create one with
  `POST /api/v1/sites`.
- If the named website is not in the workspace, the answer is 404.
- If the website is disabled for billing, most site endpoints answer 402.

Not tied to a website: auth, API keys, profile, the `/sites` routes, credits,
payments, data providers, agent scope, agent plans, scratchpads, and content
media and Unsplash.

### Who started a request (actor)

The content desk records whether a person or the agent created a piece. A
request with a session cookie, or with `x-meelu-actor: user`, counts as `user`.
Any other key-authenticated request counts as `agent`. The desktop app sends
`x-meelu-actor: user` for direct clicks. The agent never sends it.

### Response shape

- Success: `{ "data": <payload> }`. A create answers 201 where the route says
  so. A 204 has no body.
- Paged lists: `{ "data": [...], "pagination": { "page", "page_size",
  "total", "total_pages", "has_next", "has_prev" } }`. Query parameters are
  `page` (default 1) and `page_size` (default 10, max 100).
- Errors: `{ "error": { "message": string } }`. A validation error is a 400,
  not a 422.
- Credit and provider errors add a `code`:
  - Not enough credits: 402 with `balanceMicros` and `minimumMicros`.
  - Disabled website: 402 with `siteId`.
  - Data vendor errors: 400, 402 or 502.
- Field names in JSON are camelCase. Money is in USD micros.
- `GET /healthz` (outside `/api`) is the liveness check.

## Auth (`/api/auth`)

Sign-in uses Better Auth, which runs inside the dashboard at `/auth/*` with its
own database. The dashboard trades a short-lived Better Auth JWT for the api's
session cookie; the api verifies it against the dashboard's `/auth/jwks`.

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/session` | Swap `{ accessToken }` for a session cookie. Creates the user on first sign-in. |
| POST | `/api/auth/logout` | End the session and clear the cookie. |
| GET | `/api/auth/me` | The signed-in user. |

All paths below start with `/api/v1`.

## Account

Workspace API keys, and the profile of the person who owns the workspace.

| Method | Path | Purpose |
|---|---|---|
| GET, POST | `/keys` | List keys (paged); create a key. The full key is returned only once. |
| DELETE | `/keys/{key_id}` | Revoke a key. You cannot revoke the last one. |
| GET, PUT, PATCH, DELETE | `/profile` | Get (null if none), create or update (PUT), update fields (PATCH, 404 if none), delete. |

## Websites

The businesses in the workspace. `/sites/{id}` works by id. `/site` works on
the website the request is about.

| Method | Path | Purpose |
|---|---|---|
| GET, POST | `/sites` | List websites (paged, with filters and search); add a website. The domain is normalized. A duplicate is 409. |
| GET, PUT, PATCH, DELETE | `/sites/{site_id}` | Get or update a website. DELETE removes it and all its data, with no undo. |
| GET, PUT, PATCH, DELETE | `/site` | Get (null if none), update or delete the current website. |
| GET | `/stats` | Counts for the dashboard home, for the current website. |

## Pages

The crawled pages of a website, their links and text chunks. The app's crawler
writes here.

| Method | Path | Purpose |
|---|---|---|
| GET, POST | `/site/pages` | List pages; save one or many crawled pages. |
| POST | `/site/pages/search` | Search pages. |
| GET | `/site/pages/by-url` | Get a page by URL. |
| GET | `/site/pages/stats` | Page counts. |
| GET | `/site/pages/discovery` | Link depth, orphan and unreachable page counts. |
| POST | `/site/pages/visited` | Mark pages as visited by the crawler. |
| POST | `/site/pages/prune` | Delete pages the crawler did not visit. |
| POST | `/site/pages/links` | Save a page's outgoing links. |
| POST | `/site/pages/graph` | Rebuild the internal link graph. |
| GET, PUT, PATCH, DELETE | `/site/pages/{page_id}` | Get, update or delete a page. |
| GET | `/site/pages/{page_id}/links` | A page's incoming and outgoing links. |
| GET | `/site/chunks` | List text chunks of pages. |

## Page classification

The answers a server-side LLM gives about each page (page type and other
fixed questions), and the human review of those answers.

| Method | Path | Purpose |
|---|---|---|
| GET, POST | `/site/page-llm-extractions` | List extractions; save an extraction. |
| GET | `/site/page-llm-extractions/stats` | Extraction counts. |
| GET | `/site/page-llm-extractions/review-queue` | Pages waiting for review. |
| GET | `/site/page-llm-extractions/by-page/{page_id}` | The extraction for one page. |
| POST | `/site/page-llm-extractions/by-page/{page_id}/page-type` | Set the page type by hand. |
| POST | `/site/page-llm-extractions/by-page/{page_id}/review` | Save a review of the extraction. |
| GET, DELETE | `/site/page-llm-extractions/{extraction_id}` | Get or delete an extraction. |

## Crawl jobs

One row per crawl run. The app claims a job, runs it locally and reports back.

| Method | Path | Purpose |
|---|---|---|
| GET, POST | `/site/crawl-jobs` | List crawl jobs; start a crawl. |
| POST | `/site/crawl-jobs/reap` | Close jobs whose worker stopped reporting. |
| GET, PATCH, DELETE | `/site/crawl-jobs/{job_id}` | Get a job, report progress, finish or stop it, or delete it. |
| POST | `/site/crawl-jobs/{job_id}/claim` | A worker claims a job. |

## Rendering

Render jobs load pages in a browser (desktop and mobile) to compare them with
the raw HTML. The results feed technical SEO.

| Method | Path | Purpose |
|---|---|---|
| GET, POST | `/site/render-jobs` | Render status for the website; start a render job. |
| POST | `/site/render-jobs/reap` | Close jobs whose worker stopped reporting. |
| PATCH | `/site/render-jobs/{job_id}` | Report progress, finish or stop a job. |
| POST | `/site/render-jobs/{job_id}/claim` | A worker claims a job. |
| GET, POST, DELETE | `/site/page-renders` | Get, save or delete the render of a page. |

## Site structure

Link and pillar page suggestions. Each one is a proposal that the user
approves, edits or rejects. The pipeline is: propose, screen, review (in the
app), rank.

| Method | Path | Purpose |
|---|---|---|
| GET, POST | `/site/structure/jobs` | List structure jobs; start one. |
| GET, PATCH | `/site/structure/jobs/{job_id}` | Get a job; finish it. |

**Link suggestions** (add or remove an internal link):

| Method | Path | Purpose |
|---|---|---|
| POST | `/site/structure/link-suggestions/reconcile` | Bring suggestions in line with the current link graph. |
| POST | `/site/structure/link-suggestions/hierarchy` | Propose links from the site hierarchy. |
| POST | `/site/structure/link-suggestions/mentions` | Propose links for unlinked mentions. |
| POST | `/site/structure/link-suggestions/removals` | Propose links to remove. |
| POST | `/site/structure/link-suggestions/from-table` | Propose links from a workspace table. |
| POST | `/site/structure/link-suggestions/screen` | Screen out weak proposals. |
| POST | `/site/structure/link-suggestions/review-inputs` | Get the inputs for the app's LLM review. |
| POST | `/site/structure/link-suggestions/verdicts` | Save the review verdicts. |
| POST | `/site/structure/link-suggestions/rank` | Rank the suggestions. |
| GET | `/site/structure/link-suggestions/summary` | Counts by status. |
| GET, POST | `/site/structure/link-suggestions` | List suggestions; create a suggestion. |
| GET, PATCH, DELETE | `/site/structure/link-suggestions/{suggestion_id}` | Get, update (approve, edit, reject) or delete one. |

Pillar page suggestions:

| Method | Path | Purpose |
|---|---|---|
| POST | `/site/structure/pillar-suggestions/reconcile` | Bring suggestions in line with the current site. |
| POST | `/site/structure/pillar-suggestions/propose` | Propose pillar pages. |
| POST | `/site/structure/pillar-suggestions/screen` | Screen out weak proposals. |
| POST | `/site/structure/pillar-suggestions/review-inputs` | Get the inputs for the app's LLM review. |
| POST | `/site/structure/pillar-suggestions/verdicts` | Save the review verdicts. |
| POST | `/site/structure/pillar-suggestions/rank` | Rank the suggestions. |
| GET | `/site/structure/pillar-suggestions/summary` | Counts by status. |
| GET, POST | `/site/structure/pillar-suggestions` | List suggestions; create a suggestion. |
| GET, PATCH, DELETE | `/site/structure/pillar-suggestions/{suggestion_id}` | Get, update or delete one. |

## Search data (Google Search Console)

Search Console data for the website. The app fetches it locally and sends the
rows here.

| Method | Path | Purpose |
|---|---|---|
| GET | `/site/search-data` | Overview. |
| POST | `/site/search-data/property` | Set the Search Console property. |
| POST | `/site/search-data/rows` | Ingest daily rows. |
| GET | `/site/search-data/queries` | Queries with their numbers. |
| GET | `/site/search-data/pages` | Pages with their numbers, or one page's detail. |
| GET | `/site/search-data/series` | Time series. |
| GET | `/site/search-data/changes` | Biggest changes between periods. |
| GET, POST | `/site/search-data/inspections` | URLs to inspect next; ingest URL inspection results. |
| GET, POST | `/site/search-data/sync-jobs` | List sync jobs; start a sync. |
| GET, PATCH | `/site/search-data/sync-jobs/{id}` | Get one sync job; report progress or finish a sync. |
| POST | `/site/search-data/sync-jobs/{id}/claim` | A worker claims a sync job. |

## Traffic (Google Analytics 4)

GA4 data for the website. The app fetches it locally and sends the rows here.

| Method | Path | Purpose |
|---|---|---|
| GET | `/site/traffic` | Overview. |
| GET, PUT | `/site/traffic/property` | Get or set the GA4 property. |
| GET, POST | `/site/traffic/rows` | Export rows; ingest rows. |
| GET | `/site/traffic/series` | Time series. |
| GET | `/site/traffic/pages` | Landing pages. |
| GET | `/site/traffic/content` | Content pages. |
| GET | `/site/traffic/breakdown` | Breakdown by a dimension. |
| GET, POST | `/site/traffic/sync-jobs` | List sync jobs; start a sync. |
| GET, PATCH | `/site/traffic/sync-jobs/{id}` | Get one sync job; report progress or finish a sync. |
| POST | `/site/traffic/sync-jobs/{id}/claim` | A worker claims a sync job. |

## SEO

The SEO desk: the website's SEO lists, keyword clusters and tracked rankings.

| Method | Path | Purpose |
|---|---|---|
| GET | `/site/seo` | The website's SEO record. |
| POST | `/site/seo/{name}/add` | Add items to a list. `name` is `competitors` or `backlink_opportunities`. |
| POST | `/site/seo/{name}/remove` | Remove items from that list. |
| GET | `/site/seo/clusters` | List keyword clusters. |
| GET, DELETE | `/site/seo/clusters/{cluster_id}` | Get or delete a cluster. |
| POST | `/site/seo/clusters/{cluster_id}/metrics` | Score the cluster again. |
| GET | `/site/seo/tracked` | Tracked keywords overview. |
| POST | `/site/seo/tracked/rankings` | Fetch and record current rankings. |

## Technical SEO

Checks on the crawled pages. A run is one audit. Issues are either site-wide
or tied to one page.

| Method | Path | Purpose |
|---|---|---|
| GET | `/site/technical-seo/runs` | List runs. |
| GET, PUT, PATCH, DELETE | `/site/technical-seo/runs/{run_id}` | Get, update or delete a run. |
| POST | `/site/technical-seo/run-audit` | Run an audit. |
| GET, POST, PATCH | `/site/technical-seo/issues` | List site-wide issues; create a site-wide issue; update all site-wide issues of one kind. |
| GET, PUT, PATCH, DELETE | `/site/technical-seo/issues/{issue_id}` | Get, update or delete one site-wide issue. |
| GET, POST, PATCH | `/site/technical-seo/page-issues` | List page issues; create a page issue; update many page issues by filter. |
| GET, PUT, PATCH, DELETE | `/site/technical-seo/page-issues/{issue_id}` | Get, update or delete one page issue. |
| GET | `/site/technical-seo/groups` | Issues grouped by kind. |
| GET | `/site/technical-seo/summary` | Counts for the desk. |
| GET | `/site/technical-seo/download` | Download issues as CSV. |

## Content

Web pages for the user's own site. Each piece has a title, H1, meta
description, slug, target keyword and body. Meelu does not publish. The user
puts the page on the site by hand.

| Method | Path | Purpose |
|---|---|---|
| GET, POST | `/content/pieces` | List pieces (paged); create a piece. |
| GET, PATCH, DELETE | `/content/pieces/{piece_id}` | Get, update or delete a piece. |
| GET | `/content/pieces/{piece_id}/markdown` | The piece as Markdown. |
| GET, POST | `/content/pieces/{piece_id}/issues` | List the piece's check results; replace them. |
| PATCH | `/content/pieces/{piece_id}/issues/{issue_id}` | Update one issue. |
| POST | `/content/media` | Upload an image. |
| GET | `/content/media/{media_id}` | Serve an uploaded image. |
| GET, POST | `/content/unsplash` | Search Unsplash; record an Unsplash download (their rules require it). |

## Analytics

The Analytics desk. It keeps the analytics chats.

| Method | Path | Purpose |
|---|---|---|
| GET, POST | `/analytics/chats` | List the website's Analytics chats (paged, newest activity first; id, title, updatedAt only); start a chat. |
| GET, PUT, DELETE | `/analytics/chats/{chat_id}` | Get a chat; rename it or store its SDK session id; delete it with its messages. |
| GET, POST | `/analytics/chats/{chat_id}/messages` | List a chat's messages (paged, newest first); append the user's question or the answer. |

## Reports

The Reports desk. It holds the self-contained HTML reports the user keeps from the Analytics, SEO and Technical SEO desks.

| Method | Path | Purpose |
|---|---|---|
| GET, POST | `/reports` | List reports (paged, `?desk=` filters by the desk that wrote it, `?q=` searches titles); create a report (`desk`, `title`, `html`). |
| GET, PUT, DELETE | `/reports/{report_id}` | Get, update (title and/or html) or delete a report. |

## Notes

Notes about the website: standing rules and corrections the agent must follow.

| Method | Path | Purpose |
|---|---|---|
| GET, POST | `/notes` | List notes (paged), or search them with `q`; create a note. |
| GET, PUT, PATCH, DELETE | `/notes/{note_id}` | Get, update or delete a note. |

## Social listening

Finds social posts that match the website's search lines. Runs are started by
hand. The app runs the search pipeline locally and sends results here.

| Method | Path | Purpose |
|---|---|---|
| GET, PUT | `/social-listening/config` | Get or set the desk settings. |
| GET, POST | `/social-listening/queries` | List search lines; add or update search lines. |
| PATCH, DELETE | `/social-listening/queries/{query_id}` | Update or delete a search line. |
| GET, POST | `/social-listening/runs` | List runs (paged); start a run. |
| GET, PATCH | `/social-listening/runs/{run_id}` | Get or update a run. |
| POST | `/social-listening/posts/bulk` | Ingest found posts. |
| POST | `/social-listening/posts/gate` | Filter new posts before they are judged. |
| POST | `/social-listening/posts/judged` | Save the LLM's verdicts on posts. |
| GET | `/social-listening/posts` | List posts (paged). |
| GET | `/social-listening/summary` | Counts for the desk. |
| GET, PATCH | `/social-listening/posts/{post_id}` | Get or update a post. |

## Find leads

People worth a personal message, found by the app's local pipeline. The app
starts a run, the api collects post authors and LinkedIn people in background
jobs, the app sends web leads and the judge's verdicts. Meelu never contacts
anyone; a lead is new, contacted or discarded.

| Method | Path | Purpose |
|---|---|---|
| GET, POST | `/find-leads/briefs` | List briefs; add one. |
| GET, PATCH, DELETE | `/find-leads/briefs/{brief_id}` | Get, update or delete a brief. |
| GET, POST | `/find-leads/runs` | List runs (paged); start a run. |
| GET, PATCH | `/find-leads/runs/{run_id}` | Get or update a run. |
| POST | `/find-leads/runs/{run_id}/collect` | Start collecting one source (`posts` with a platform, or `linkedin`). |
| POST | `/find-leads/runs/{run_id}/enrich` | Start reading the shortlist's recent activity. |
| POST | `/find-leads/leads/candidates` | Ingest web leads found by the app. |
| POST | `/find-leads/leads/screened` | Save the first, snippet-only verdicts. |
| POST | `/find-leads/leads/judged` | Save the final verdicts with reason, angle and evidence. |
| GET | `/find-leads/leads` | List leads (paged; `status`, `briefId`, `runId`, `source`, `q`). |
| GET, PATCH, DELETE | `/find-leads/leads/{lead_id}` | Get a lead, change its status, or delete it. |
| GET | `/find-leads/summary` | Counts for the desk and the last run. |

## Data providers

Shared third-party data vendors (DataForSEO, Apify). The server holds one
account per vendor and charges calls to the user's credits.

| Method | Path | Purpose |
|---|---|---|
| GET | `/providers/status` | Which providers are configured. |
| GET | `/providers/calls` | The user's provider call log (paged). |
| GET | `/providers/social-listening/platforms` | Platforms social search supports. |
| POST | `/providers/social-listening/search` | Search social posts through the provider. |

## LLM

Every LLM call the app makes goes through the api to OpenRouter on the
server's key, and is charged to the user's credits at OpenRouter's reported
cost. The default model is `anthropic/claude-haiku-5.5`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/llm/models` | Tool-capable models with price per million tokens and context size. Recommended first, then well-known providers, then the rest, cheapest first within each. |
| GET | `/llm/preference` | The user's default model. |
| PUT | `/llm/preference` | Set the default model. Only a listed model is accepted. |
| GET | `/llm/calls` | The user's LLM call log with tokens and cost (paged, `?model=` filter). |
| POST | `/llm/v1/messages` | Anthropic Messages API, streamed or not. Point an Anthropic client's base URL at `/api/v1/llm`. Optional headers: `x-meelu-site`, `x-meelu-purpose` (`agent`, `social_listening`, `page_review`, `site_summary`). Responses and errors are Anthropic's shape, not the envelope. A balance under the floor answers 402. |

## Credits and payments

The user's balance in USD micros. Provider calls, LLM calls and websites are
charged against it. Top-ups go through Dodo Payments.

| Method | Path | Purpose |
|---|---|---|
| GET | `/credits` | Current balance. |
| GET | `/credits/ledger` | Ledger entries (paged). |
| GET | `/credits/sites/{site_id}` | Billing state of one website. |
| POST | `/credits/grant` | Add credits. Operators only. |
| POST | `/credits/sweep` | Run the website billing sweep. Operators only. |
| POST | `/payments/checkout` | Start a checkout. Returns a URL to send the user to. |
| GET | `/payments` | List payments (paged). |
| GET | `/payments/{payment_id}` | Get one payment. |
| POST | `/payments/webhooks/dodo` | Dodo webhook. Credits the balance once per paid payment. |

## Agent scope and plans

The app's agent runner reads the scope before each task: the system prompt,
tables, guides, allowed writes and the desks the model may add. Plans are
saved plans the agent can reuse, each with a slug and the question it answers.

| Method | Path | Purpose |
|---|---|---|
| GET | `/agent/scope` | Scope for `?action=` (and `?desks=`), for the website in `x-meelu-site`. |
| GET, POST | `/agent-plans` | List plans (paged); create a plan. |
| GET | `/agent-plans/by-slug/{slug}` | Get a plan by slug. |
| GET, PATCH, DELETE | `/agent-plans/{plan_id}` | Get, update or delete a plan. |

## Scratchpads

Temporary work queues for one agent run. A tool with a large output writes rows
here and returns a handle. The agent then takes rows in batches and marks each
one done or failed.

| Method | Path | Purpose |
|---|---|---|
| POST | `/scratchpads` | Create a scratchpad. |
| GET, DELETE | `/scratchpads/{scratchpad_id}` | Get or delete a scratchpad. |
| POST | `/scratchpads/{scratchpad_id}/rows` | Append rows. |
| GET | `/scratchpads/{scratchpad_id}/metrics` | Row counts by status. |
| POST | `/scratchpads/{scratchpad_id}/next` | Read the next rows. |
| POST | `/scratchpads/{scratchpad_id}/claim` | Claim rows for work. |
| POST | `/scratchpads/{scratchpad_id}/status` | Set the status of rows. |
| GET | `/scratchpads/{scratchpad_id}/failed` | List failed rows. |
| GET | `/scratchpads/{scratchpad_id}/search` | Search rows. |
