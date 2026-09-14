# Meelu Dashboard — REST API Spec (v1)

**Meelu is an AI marketing assistant for a website.** A user may run
several; every capability is argued from one website's positioning, so a second
business is a second website rather than a second account. v1 ships one agent:
**Outreach**. The intelligence lives in the agent server (`../api/src/agent`),
which reads the database directly and writes through its own controlled tools;
this dashboard is where its work lands and gets reviewed, edited and sent by a
human. These APIs serve the UI — the agent does not read through them.

## Conventions

- Base path: `/api/v1`; JSON in/out.
- Success envelope: `{ "data": <payload> }` (200, or 201 for creates).
- Error envelope: `{ "error": { "message": string } }` (400/401/404/409).
- Auth on every endpoint: `meelu_session` cookie (browser) **or** `x-api-key`
  header (a workspace API key). Keys are managed in Settings.
- Timestamps ISO 8601; IDs like `prj_ab12cd34ef56`. `PUT` = partial merge patch.
- All resources are scoped to the authenticated user's workspace. Every
  successful write appends an Activity entry.
- List endpoints return newest-first arrays.

### Who initiated a request (actor)

One API serves three clients — the browser dashboard, the MCP server, and the
desktop app — and a few rules care whether a *person* or a *model* initiated
the action (only a person may mark a post `posted`; todos record who added
them). A session cookie is always `user`. A key-authenticated request is
`agent` unless it carries **`x-meelu-actor: user`**, which the desktop app
sends on direct UI clicks. The MCP server never sends it — that header is a
human's claim, and the agent has no honest way to make it.

### Which website a request is about

Most resources belong to **one website**. Name it with the `x-meelu-site`
header (or `?siteId=`); the browser sends the site the switcher is showing and
the MCP server sends the one the chat session picked.

- **One website in the workspace → the header is optional.** It is used
  automatically, so a single-site workspace never thinks about any of this.
- **Several and none named → 400**, saying how many there are and how to pick.
  Nothing is guessed: a wrong guess would write a MahaJob email against another
  business's positioning.
- **A row belonging to another website is invisible**, not merely mislabelled —
  `GET /contacts/:id` with the wrong site is a 404. That matters most for the
  agent, which may still be holding an id from the site it worked on earlier.

| Per website | Personal to the user |
|---|---|
| outreach projects, campaigns, prospects, emails | profile |
| content projects, platforms, posts | API keys |
| contacts | todos |
| knowledge notes, coaching | the platform catalog |

`GET /api/v1/activity` is the exception: the header narrows it to one website,
and omitting it shows the whole workspace.

## Auth (mounted at /api/auth)

- `POST /api/auth/register` — `{ name, email, password }`
- `POST /api/auth/login` — `{ email, password }`
- `POST /api/auth/logout` · `GET /api/auth/me`

## User profile — the person

Who the workspace belongs to. `site` is the business; this is the human whose
name signs the emails and whose voice the content is written in. Separate from
the `user` row, which holds login identity only.

- `GET /api/v1/profile` → `data: UserProfile | null`
- `PUT /api/v1/profile` — upsert. First create requires `fullName`; all fields
  optional after: `{ fullName, role, company, timezone, signature, bio,
  writingVoice, linkedinUrl, xUrl, websiteUrl }`
- `PATCH /api/v1/profile` — merge only; 404 if there is no profile yet
- `DELETE /api/v1/profile` → `data: { deleted: true }`

`signature` is used verbatim at the bottom of outreach emails, line breaks
included. `timezone` must be an IANA `Area/Location` name (`Asia/Kolkata`) or
`UTC` — abbreviations like `IST` are rejected because they are ambiguous, and
scheduling reads this field.

## Websites — the businesses being marketed

A workspace holds one or more. Everything an agent writes is argued from one of
them. Design notes in `../WEBSITES.md`.

- `GET /api/v1/sites?q=&domain=&country=&hasRepo=&neverCrawled=&crawledBefore=&crawledAfter=&sort=&limit=&offset=`
  → `{ sites, total, shown, offset }`, oldest first. `q` matches name, domain
  or summary; `sort` takes created, name, domain or crawled; every filter is
  ANDed, and `total` counts the whole filtered set so a caller pulling
  everything walks `offset` until it has `total` rows.
- `POST /api/v1/sites` — `{ domain, name, ... }`; domain and name required.
  The domain is normalized (`https://WWW.Foo.com/pricing` → `foo.com`) and a
  duplicate is a 409. A new website starts empty apart from the default
  workflows and prompts, and its first crawl begins in the background.
- `GET | PUT | PATCH | DELETE /api/v1/sites/:id` → PUT and PATCH are the same
  merge patch. DELETE answers
  `data: { deleted: true }`. The row is gone for good and takes the website's
  whole world with it: pages, chunks, crawl jobs, search data, issues, notes,
  projects, campaigns, prospects, emails, content, workflows and analytics all
  cascade in the database. Activity survives with its `siteId` cleared. There
  is no undo — adding the domain back gives you an empty website.

The singular `/api/v1/site` below means **the website this request is about**,
resolved as described in Conventions.

The record has two halves. The **curated** half is the user's own words about
their business. The **scraped** half starts empty and is filled by an agent
reading the live site; `detailsStatus` (`empty` | `scraped` | `reviewed`) and
`scrapedAt` say where it stands.

- `GET /api/v1/site` → `data: SiteProfile | null` — null when the workspace has
  no website yet, which is what onboarding is for
- `PUT | PATCH /api/v1/site` — merge patch onto the current website
- `DELETE /api/v1/site` → `data: { deleted: true }` — the same permanent
  delete as `DELETE /api/v1/sites/:id`

Use `POST /api/v1/sites` to create one; the singular endpoint no longer
upserts, because "the site I'm on" cannot create the thing it resolves to.

```
curated  { domain, name, tagline, positioning, targetAudience,
           brandVoice, country }
scraped  { summary, products[], pricing, differentiators[], proofPoints[],
           sourceUrls[], links[], scrapedAt, detailsStatus,
           suggestedPositioning, suggestedAudience, suggestedBrandVoice }
```

The three `suggested*` fields sit on the scraped side because they are the
agent's proposal for the three curated fields above it — the one place it is
asked to form a view rather than copy one down. They are pre-filled into the
form on `/dashboard/website-profile`; accepting one is the **user** saving the
curated field through `PATCH /api/v1/site`, never the agent writing it.

`links` is `{ platform, url, handle? }` — the business's own social profiles,
one row per platform. It lives in a side table (`site_links`) and is hydrated
onto the record on read.

**Sending `links` replaces the whole set** — it is not a merge, so a re-scrape
cannot leave behind a platform the business has since dropped. Omitting it
leaves the existing rows untouched.

There is no `keyPages`; see the note under *Website details* below for what
replaced it and why.

### Website details — the agent's door onto the scraped half

- `GET /api/v1/site/website-details` → the scraped fields plus `siteId`,
  `domain` and `name`, for the current website
- `PUT /api/v1/site/website-details` — accepts **only** the scraped fields.
  Stamps `scrapedAt` and sets `detailsStatus` to `scraped`. Sending
  `detailsStatus: "reviewed"` is the exception: that records a human confirming
  what is already there, so it moves the status and leaves `scrapedAt` alone.

**`keyPages` is gone** along with the `site_pages` table. It was a second page
table sitting alongside `site_pages`, and two page tables drift until something
is reading the unmaintained one — `GET /api/v1/site/pages` is the page list.
`links` stays: those are the business's social handles, which no crawl table
holds and the Social desk needs. Sending `keyPages` is now a 400 like any other
unknown field.

Passing a curated field (`positioning`, `targetAudience`, `brandVoice`, `name`,
`domain`) is a **400 naming the offending fields**, not a silent drop. That is
the point of the separate endpoint: an agent can record what the website says,
but it cannot quietly rewrite how the user describes their own business. To put
a view of the first three in front of the user, it sends `suggestedPositioning`,
`suggestedAudience` and `suggestedBrandVoice` instead.

In the desktop app this runs by itself: adding a website lands on
`/dashboard/website-profile`, which launches the `website-profile` agent when
`detailsStatus` is `empty`. The web has no harness, so the same screen is a
plain form there.

## Context (the brain — pulled by the MCP server before every task)

- `GET /api/v1/context` → `data: { site, stats, knowledge, projects,
  activeCampaigns, awaitingSend, recentActivity, coaching }`
  - `projects`: each brief with its campaigns and `knownProspects` — the count
    already claimed project-wide, i.e. the dedupe scope.
  - `awaitingSend`: emails in `draft`. Nothing in this API sends, so these are
    waiting to go out through the email MCP server in the agent's session, or
    from the user's own client.
  - `coaching`: the knowledge notes flagged `isFeedback` (newest 50) — what was
    turned down, why, and the standing instruction each produced. The agent MUST
    honor these.

## Stats

One group per desk — the same object `GET /api/v1/context` carries as `stats`.

- `GET /api/v1/stats` → `data: {`
  - `outreach: { projects, campaigns, activeCampaigns, prospects, emailsDrafted,
    emailsSent, emailsFailed, replies }`
  - `content: { projects, pending, ready, posted }` — `projects` counts `active` ones
  - `contacts: { total, neverContacted }`
  - `seo: { pages }`
  - `todos: { open, overdue }` — overdue means the six-hour block ran out and it is still open
  - `ideas: { total, sparks, building }`
  - `knowledgeNotes }`

Todos and ideas belong to the person, not a website, so those two groups answer
the same under every site.

## Activity

- `GET /api/v1/activity?limit=50&agent=outreach|system` → `data: Activity[]`

## API keys

- `GET /api/v1/keys` · `POST /api/v1/keys` `{ name? }` · `DELETE /api/v1/keys/:id` (keep ≥1)

## Outreach

The chain: **project** (standing brief) → **campaign** (a run) → **prospect**
(a lead) → **email** (one message).

**This API sends no mail.** There is no provider integration and there won't
be: the agent writes drafts here and sends them through an email MCP server in
its own session (Resend), or the user copies them into their own client. Either
way the outcome is written back with `PUT /outreach/emails/:id`, so `sent`
records a send that actually happened rather than one this API caused.

### Projects

- `GET /api/v1/outreach/projects`
- `POST /api/v1/outreach/projects` — `{ name, prospectProfile, goal?, prompt?,
  searchCriteria?, emailTone?, valueProp?, cta? }` (name + prospectProfile required)
- `GET | PUT | DELETE /api/v1/outreach/projects/:id`
- `GET /api/v1/outreach/projects/:id/known-prospects` → the exclusion list an
  agent loads **before** prospecting: `{ projectId, projectName, count,
  excludeEmails[], excludeDomains[], excludeCompanies[], prospects[] }` —
  everyone already claimed under this project across all of its campaigns.

### Campaigns

- `GET /api/v1/outreach/campaigns?projectId=&status=` → each with computed
  `stats: { prospects, emails, sent, replies }`
- `POST /api/v1/outreach/campaigns` — `{ name, projectId, status?, notes? }`
  (status `drafted|running|completed`, default `drafted` — a campaign is one
  run of the brief: created → the agent is searching → the run is over. The
  agent marks its campaign `completed` at the end of a run; completed is not
  a lock — prospects can still be added to the project by hand.)
- `GET | PUT | DELETE /api/v1/outreach/campaigns/:id`
  - The first transition into `running` freezes the project's brief onto the
    campaign as `projectSnapshot`. The snapshot is never patchable from
    outside — editing the live project must not rewrite what a campaign
    actually ran with.

### Prospects — **unique per project**

A person/company may appear at most once per **project**, no matter how many
campaigns it has. Two campaigns under one brief therefore never work the same
lead, and nobody gets two cold emails for the same reason.

Prospects **belong to the project**; the campaign on each row only records
which run found it. Manual adds pass `projectId` instead of `campaignId` and
land on the project's auto-created `Manual additions` campaign, so the
prospect → campaign → project chain holds without a nullable column.

- `GET /api/v1/outreach/prospects?campaignId=&projectId=&status=`
- `POST /api/v1/outreach/prospects` — one of:
  - `{ campaignId, name, company?, role?, email?, website?, sourceUrl?,
    fitReason?, status? }` → 201, or **409** if the lead is already claimed
    under the campaign's project (the message names the owning campaign)
  - `{ projectId, name, … }` → a manual add: filed under the project's
    `Manual additions` campaign (created on first use, born `completed`)
  - `{ prospects: [ …same shape… ] }` → batch: `{ created[], skipped[] }`.
    Duplicates are skipped rather than failing the batch.
  - `dedupeKeys` is server-derived and ignored on input; with `campaignId`
    present the prospect's project is derived from the campaign.
- `GET | PUT | DELETE /api/v1/outreach/prospects/:id`
  - `status` one of `new|contacted|replied|converted|rejected` (default `new`).
  - Changing `email`/`website`/`company`/`name`, or moving the prospect to a
    campaign in another project, re-checks uniqueness (409 on clash).

**Identity matching.** Each prospect carries `dedupeKeys` — every identity it
answers to: `email:…`, `domain:…` (bare host of `website`), `company:…`, and
`name:…` only when nothing stronger is known. Two prospects are the same lead
when these sets overlap on **any** key, so a lead found by email in one
campaign still matches when another finds only its website or company. Dedupe
is deliberately org-level: two people at the same publication must not both
get a cold email from the same brief.

### Emails

- `GET /api/v1/outreach/emails?campaignId=&prospectId=&status=`
- `POST /api/v1/outreach/emails` — `{ campaignId, prospectId, subject, body,
  status? }`. The prospect must belong to that campaign (400 otherwise).
- `GET | PUT | DELETE /api/v1/outreach/emails/:id`
  - status is exactly `draft | sent | failed`, default `draft`:
    - `draft` — written, waiting for the user to send it by hand
    - `sent` — the user sent it and said so; the server stamps `sentAt`
    - `failed` — bounced, or never went out
  - The agent only ever creates drafts. `sent`/`failed` are the user's record
    of what happened in their own mail client, not something the system caused.

## Contacts — people you already know

The mirror of prospects: a prospect is a stranger the agent found, unique per
project, contacted once; a contact is someone the user already knows and may
write to as often as they like. Identity on both sides comes from the same
`identityKeys()`, so the two lists can recognise the same person. Design notes
in `CONTACTS_AGENT.md`.

- `GET /api/v1/contacts?search=&source=` — `source` is `inbox|file|manual|other`.
- `POST /api/v1/contacts` — `{ name, email?, company?, role?, website?, phone?,
  source?, sourceRef?, notes? }`, or a batch under `contacts`.
  - **One row per person.** A duplicate is a 409 naming the existing contact
    and its id; in a batch it lands in `skipped` and the rest are still created.
- `GET /api/v1/contacts/known` → `{ contacts[], prospects[] }` — the exclusion
  list to load **before** re-reading a mailbox or a file.
- `GET | PUT | DELETE /api/v1/contacts/:id` — on PUT, `""` clears an optional
  field; changing name/email/company/website re-keys and re-checks for a clash.
  - GET and every create carry `alsoProspect[]` when the same person is a
    prospect in a campaign. It is a **warning, not a block** — both rows may
    legitimately exist, but nobody should get a cold pitch and a warm note in
    the same week by accident.
- `POST /api/v1/contacts/:id/touch` — `{ at?, note? }` stamps
  `lastContactedAt`, bumps `touchCount`, and appends one dated line to `notes`,
  dated in the user's own timezone. There is no message store and no reply
  tracking in v0; this is the whole history.

## Website content — the desk that never existed

`/content/posts` and `/content/pages` are **not the same resource**, and the
reason is one column: a post carries `platformKey` and a notNull `scheduledAt`,
so every row must have a slot. That is a social assumption. A piece of website
content has no slot — it is draft, ready, in a PR, or published. Sending
`scheduledAt` or `platformKey` here is a **400 that says so**; a shared table
would have meant inventing a fake time for every article and then teaching every
query to ignore it.

- `GET /api/v1/content/pages?status=&kind=&projectId=&targetPageId=&search=&view=&limit=&offset=`
  → `{ pages, total, shown }`. Slim by default — these rows carry
  `bodyMarkdown`, and forty drafts would otherwise be forty articles down the
  wire to answer "what have we got". `?counts=true` gives the status tally.
- `POST /api/v1/content/pages` — `{ title, kind?, slug?, bodyMarkdown?,
  description?, frontmatter?, projectId?, targetPageId?, matchedPassage?,
  linkFromPageId?, status?, publishTarget?, sourcePageId? }`, 201.
  - `kind: "update"` **requires `targetPageId` and `matchedPassage`** — which
    page this rewrites, and the sentence on it that made this an update rather
    than a new piece. Without them the piece is a new page that happens to
    overlap one you already have.
  - The `source*` references are written at creation time even when nothing
    reads them yet. They cost a column now and are unbackfillable later.
- `GET | PATCH | DELETE /api/v1/content/pages/:id`
  - PATCH refuses to rewrite the body of a **published** piece: the stored
    record would then disagree with the live page, and nothing downstream could
    tell which one "the article we published in March" meant. Draft the change
    as a new `update` against it.
  - DELETE refuses on a published piece for a different reason — removing the
    row does not unpublish anything, and it loses the reference saying where
    the piece came from, which is the only way to find out later whether
    it worked.
- `POST /api/v1/content/pages/:id/publish` — `{ publishTarget, prUrl?, prState?,
  publishedUrl?, publishedAt? }`.

  **It does not publish and it does not merge.** The PR is opened by the harness
  on the user's device against their own GitHub credential — this backend has
  never held one, for the same reason it holds no LLM key. So the body is a
  report, and `prUrl` and `publishedUrl` are different strengths of claim stored
  separately: a merge is a fact about a repository, and only a live URL is a
  fact about the website. When `linkFromPageId` is set, a publish answers with
  `pendingLinkFromPageId` — adding that link is an edit to the user's site, so
  it is surfaced rather than acted on.

## Social — publishing through the app

Publishing runs in the Meelu app, through the user's own connected provider
(Postproxy today). The api holds only the binding between a website and its
account at the provider, plus the channel flags; every vendor call and every
piece state change is made by the app's social scheduler, which patches the
content piece with the `system` actor (`x-meelu-actor: system`).

- `GET /api/v1/social/account` → `{ id, provider, externalAccountId }`, 404
  when the website has none yet.
- `PUT /api/v1/social/account` — `{ provider, externalAccountId }`, upsert.
- `DELETE /api/v1/social/account`.
- `POST /api/v1/social/channels/sync` — `{ platforms[] }` flips the website's
  channels on or off to match what is connected at the provider.

`scheduled` and `posted` are the only two statuses no caller may set: they are
facts about what the vendor did, so `api/src/content` refuses them from
every actor except `system`, which is the app's scheduler.

## Crawling — the one job this backend runs

Crawling is mechanical — fetch, parse, hash, diff — so it runs here rather than
on the user's machine. Understanding a page still needs a model and still
happens in the app.

A crawl is **detached**: the request that starts it returns as soon as the job
row exists, because a full crawl is thousands of URLs and tens of minutes and no
HTTP request should be asked to survive that. Callers **poll**.

### Three filters, cheapest first

This is the whole performance story, and the order matters:

1. **The freshness cutoff** — a page downloaded within `freshDays` (default 7)
   that the pipeline has finished with is skipped **without a request**. One
   indexed query decides it for the whole site.
2. **The conditional request** — what survives is fetched with `If-None-Match` /
   `If-Modified-Since`, so an unchanged page costs headers, not a body.
3. **The content hash** — what comes back is compared to the stored hash, so a
   server with no ETags still costs nothing downstream.

A page is only skip-eligible when the crawl owes it nothing: never fetched,
errored, missing or stale passages, or a passage the embedder gave up on all
make it ineligible however fresh it is. That is what makes an interrupted run
**resume** — the pages it fetched are the freshest on the site, so the next run
steps over them instead of starting at the home page.

`freshDays: 0` disables the cutoff and re-reads everything. It is what a first
crawl uses, and what to pass when a site has been rebuilt.

### Pages — the crawled corpus

The corpus is the Site desk's, not the SEO desk's: it is what a crawl writes and
what every other desk reads. `api/src/site_pages`
holds it, and the routes sit under `/api/v1/site/` to match.

- `GET /api/v1/site/pages?url=&kind=&stage=&status=&needsAudit=&searchText=&sort=&limit=&offset=&view=`
  — `{ pages, total, shown, offset }`, slim by default, because these rows carry
  `bodyText` and a three-hundred-page site would otherwise send a megabyte to
  answer "what pages are there". `limit` defaults to 50 and `total` counts the
  whole filtered set, so a caller pulling everything walks `offset` until it has
  `total` rows. Every sort breaks ties on `url`, which is unique per site — a
  page of results means the same rows on the next call.
  The same route answers "which pages 404": `statusCode=` (repeat or comma-join
  for several), `urlContains=`, `title=`, `titleContains=`, `metaContains=`,
  `textContains=`, `lang=`, `format=`, `embedState=`, `ids=`, `urls=`, `kinds=`,
  `inSitemap=`, `orphan=`, `shallow=`, `noindex=`, `canonicalElsewhere=`,
  `redirects=`, repeated `missing=` (title | metaDescription | h1 | bodyText),
  `minWords=`/`maxWords=`, `minDepth=`/`maxDepth=`, `minInlinks=`/`maxInlinks=`,
  `crawledBefore=`/`crawledAfter=`, `changedBefore=`/`changedAfter=` and
  `publishedBefore=`/`publishedAfter=` all narrow it, ANDed together; `status=`
  takes a class (ok, error, gone, blocked, serverError, unreachable, redirect),
  and `sort=` takes a comma-separated list of url, inlinks, depth, words,
  status, crawled or changed, each optionally suffixed `:asc` or `:desc` to
  override that key's own direction — keys apply in the order given, e.g.
  `sort=words:desc,depth:asc`. A malformed filter is a 400 naming it, never a
  silently ignored argument.
  `searchText=` folds retrieval into the same list: the query is embedded and
  matched against the site's passages semantically, the matching pages become a
  pre-filter that every other argument then narrows, and each returned row
  carries `similarity` and `match` (the best passage and its heading path).
  With no explicit `sort`, rows come back most-relevant first; a `sort`
  overrides that. An unembedded site cannot answer — the reply is empty with a
  `note` saying so, and exact-string questions belong to `textContains=`, not
  to `searchText=`.
  `view=export` is the third shape: scalar columns only, plus link/image/
  heading counts and `hasText` computed in SQL, and no body text or JSON
  blobs. It exists so `meelu_site_download_data` can walk the corpus into a
  CSV without dragging megabytes of page text across the wire.
- `GET | PUT | PATCH | DELETE /api/v1/site/pages/:id`, and
  `GET /api/v1/site/pages/by-url?url=` for lookup only — a URL is unique per
  website and a crawl knows the URL long before it knows the id, but every
  mutation goes through the id: resolve by url first, then call the id route.
  The URL is normalized the same way a crawl normalizes it
  (hash dropped, host lowercased, trailing slash trimmed), so the address a
  caller has works without being canonicalized first. Writing `inlinks`,
  `inboundAnchors`, `depth`, `linkScore` or `visited` is a 400: the first four
  are properties of the whole link graph, rebuilt by
  `POST /api/v1/site/pages/graph`, and `visited` is the crawl's own sweep mark.
  An unknown field is a 400 too. DELETE takes the page's passages with it.
  Both list and detail carry the derived `stage`,
  computed in one place (`api/src/site_pages/stage.py`). A screen that
  re-derived it would be the second implementation of that ladder, and two
  implementations are how two screens start disagreeing about what "changed"
  means.
- `POST /api/v1/site/pages` — a crawl batch, `{ pages: [ … ] }`, answering with
  how many rows it wrote. `inlinks`, `inboundAnchors` and `depth` are refused
  from a crawl: they are properties of the whole graph, and a crawl only ever
  sees the slice it happened to fetch. Posting a single page object instead of
  a `pages` array writes that one page — inserted, or merged onto whatever is
  already at that URL — and answers with the row.
- `GET /api/v1/site/pages/graph?from=&to=&limit=&offset=` — the internal link
  graph as `{ edges, total, shown, offset }`, one distinct `{ from, to, anchor }`
  per link between two crawled pages. `from=` is what a page links to, `to=` is
  what links to it; both together with no filter is the whole graph, paged.
  `meelu_site_page_links` reads one page's edges.
- `POST /api/v1/site/pages/graph` — rebuilds that graph from the stored pages,
  which is what makes those three columns true site-wide.
- `POST /api/v1/site/pages/visited` — the crawl's mark-and-sweep bookkeeping.
  `{ reset: true }` flags every page of the site unvisited at crawl start;
  `{ urls: [ … ] }` flags the pages a crawl batch reached, so the mark spreads
  over the crawl instead of one corpus-sized request at the end. Saving a crawl
  batch marks its pages too, so the urls form only carries pages that were
  visited without being written — fresh ones the crawl skipped.
- `POST /api/v1/site/pages/prune` — the sweep: deletes every page still
  unvisited, i.e. the pages a complete crawl no longer reached. No body — the
  marks already say what survives. The crawler calls it only after a complete,
  unstopped crawl whose reset succeeded; a crawl that dies mid-run leaves
  stale marks, and the next run's reset replaces them.
- `GET /api/v1/site/pages/stats` — counts by stage, plus `lastCrawledAt` and the
  sitemap size, for the Site desk header.
- `GET /api/v1/site/pages/keywords?limit=` — every saved keyword and answered
  question collected across the pages, deduplicated, each with how many pages
  carry it, ordered most-carried first and cut at `limit` (500 by default, 2000
  at most; `keywordsTruncated`/`questionsTruncated` say when the cut bit). The
  same filters as the page list narrow which pages are collected — everything
  except `searchText`, `sort` and paging. `matchedPages` and `annotatedPages`
  come along so a caller can tell an unannotated corpus from an uncovered one.
- `GET /api/v1/site/chunks?pageId=` — the passages one page was split into.

**`needsAudit` is `status = 200` with a content hash**, not a comparison against
a last-audited hash: there is no column recording what a page was last audited
from, so the audit desk re-reads a page it has already seen. Re-adding that
column is what would make this a real queue.

### Crawl jobs — one row per run

- `GET /api/v1/site/crawl-jobs?status=&trigger=&active=&complete=&failed=&startedAfter=&startedBefore=&finishedAfter=&finishedBefore=&createdAfter=&createdBefore=&sort=&limit=&offset=`
  → `{ jobs, total, shown, offset, status }` — the paged run history plus the
  current state of the site's crawling. `status=` repeats or comma-joins,
  `sort=` takes created, started, finished or fetched, and an unparseable date
  is a 400 rather than a filter that quietly matches everything.
- `POST /api/v1/site/crawl-jobs` — starts a crawl — `{ freshDays?,
  freshBefore?, sitemapUrls?, trigger? }`, plus `reap: true` to
  clear jobs whose owner died before starting a new one. 202 / 409.
- `GET /api/v1/site/crawl-jobs/:id` — the polling read.
- `PATCH /api/v1/site/crawl-jobs/:id` — `{ status: "cancelling", reason? }`, and
  nothing else. A job records what a process did; letting a caller write
  `fetched` or `complete` would let it lie about work that never happened.
- `DELETE /api/v1/site/crawl-jobs/:id` — stops a live job, deletes a settled one.
  One verb because "make this go away" is one intention; a live job cannot just
  be deleted or its loop would write to a row that no longer exists.
- `POST /api/v1/site/crawl-jobs/reap` — `{ staleMs? }` (floor 60s). Fails jobs
  whose heartbeat stopped. **Distinct from stopping one**: stopping asks a live
  loop to wind up, reaping clears a row with nobody behind it — from the outside
  they look identical, and only the heartbeat tells them apart.

Statuses: `queued → running → completed | failed | cancelled`, with
`cancelling` in between when somebody asks a running crawl to stop. Stopping is
cooperative: the batch in flight lands first, so a stopped crawl leaves the same
consistent state a finished one does, only smaller.

**One live job per website**, enforced by a partial unique index rather than by
application code — two containers racing is exactly the case a check-then-write
loses, and the damage is two crawls interleaving their upserts over the same
rows.

### Search data — the query truth layer (Search Console, measured)

Query × page × day rows from Search Console, kept 16 months, synced by the app
from the user's own machine the same way a crawl is: open a job, claim it, post
batches, settle. The property the numbers come from is the user's explicit
choice (`site.gscProperty`), never guessed between domain and URL-prefix forms.

- `GET /api/v1/site/search-data` — the overview: connection, coverage
  (`firstDay`/`lastDay`/`daysStored`), 28-day totals against the 28 before,
  weekly click series, the latest sync. `operatingBlind: true` when the site
  has almost no impressions — callers repeat that rather than trending noise.
- `POST /api/v1/site/search-data/property` — `{ property }`. The user's answer
  to "which property is authoritative".
- `POST /api/v1/site/search-data/rows` — `{ days: [{ day, rows }] }`, max 31
  days per batch. Each day is replaced whole, so re-syncing a day is idempotent.
- `GET | POST /api/v1/site/search-data/sync-jobs` — latest/active, or open one
  (202 / 409; one live sync per site, same partial-index trick as crawls).
- `POST /api/v1/site/search-data/sync-jobs/:id/claim` — the plan: property,
  `startDay`/`endDay` (ends three days back — the data lags), `resumeFrom` so a
  killed sync never refetches what already landed.
- `GET | PATCH /api/v1/site/search-data/sync-jobs/:id` — poll / heartbeat,
  progress counters, and settle with `status: completed | failed | cancelled`.
- `GET /api/v1/site/search-data/series?days=&pages=` — the daily chart:
  per-day clicks/impressions/CTR/position over the window, plus totals for the
  window and the one before it. `pages=` (comma-separated, max 5) returns one
  series per page instead of the site-wide line.
- `GET /api/v1/site/search-data/pages?days=&sort=&dir=&search=&url=` — per-page
  rollups with deltas, weekly trend, and index status (state, last crawl, last
  inspection). Sortable by any column; `url=` gives one page's queries instead.
- `GET /api/v1/site/search-data/queries?view=top|striking&days=&pages=&search=` —
  query rollups, optionally scoped to up to 5 pages. `striking` is position
  8–15 with ≥ 50 impressions over 28 days, each row joined to its owning page
  and that page's inlinks.
- `GET /api/v1/site/search-data/changes?days=` — the movers: pages and queries
  that gained or lost the most clicks vs the previous window.

Positions aggregate impression-weighted (`sum(position·impressions) /
sum(impressions)`), never plain averages.

### Structure — index status and the link graph

- `GET /api/v1/site/structure` — indexation buckets (indexed /
  crawled-not-indexed / discovered / excluded / blocked / unchecked), median
  inlinks, orphans, starved money pages, over-linked thin pages, weak anchor
  text, and `contentQualityVerdict` when the crawled-but-not-indexed bucket is
  big enough to override "publish more".
- `POST /api/v1/site/structure` — recompute internal PageRank into
  `site_pages.link_score`. Also runs automatically after every graph rebuild.
- `GET /api/v1/site/structure/inspections?limit=` — which URLs the app should
  inspect next (never-checked first). `POST` ingests the results
  (`{ inspections: [{ url, verdict, coverageState, googleCanonical }] }`);
  verdicts are classified into the buckets above on write.

### Technical SEO — the checks, and every run of them

Three tables, one desk. `site_audit_runs` is one row per pass of the checks;
`site_issues` holds what a run found about the website as a whole, and
`site_page_issues` what it found about one page. Every issue belongs to exactly
one run through `run_id`, so a run is a photograph rather than a running tally,
and deleting a run takes its issues with it.

A run is rebuilt from scratch each time, but decisions survive: any issue the
user or an agent has touched — turned down, reworded — is copied onto the new
run by `kind` (and by URL, for a page issue). That is why turning something down
once is enough.

Every read takes an optional `runId=`; without one it answers from the latest
run, and 404s with "this website has not been audited yet" when there is none.

**Running the checks**

- `POST /api/v1/site/technical-seo/run-audit` — `{ trigger? }`. Runs every rule
  over the pages already on record, writes a new run, and answers 201 with that
  run's summary and `checks`. It does not crawl: re-read the site first if it
  has changed, or the checks will flag what has since been fixed.

**Runs**

- `GET /api/v1/site/technical-seo/runs?trigger=&reviewed=&limit=&offset=`
  → `{ runs, total, shown, offset }`, newest first.
- `GET /api/v1/site/technical-seo/runs/:id`.
- `PUT | PATCH /api/v1/site/technical-seo/runs/:id` — `{ reviewed?, trigger? }`.
  `reviewed: true` stamps `reviewedAt`, `false` clears it. Counts are written by
  the audit itself and cannot be set by a caller.
- `DELETE /api/v1/site/technical-seo/runs/:id` — takes the run's issues with it.

**Site-wide issues** (`site_issues`)

- `GET /api/v1/site/technical-seo/issues?runId=&state=&severity=&kind=&limit=&offset=`
  → `{ runId, issues, total, shown, offset }`. `kind` repeats or comma-joins and
  an unknown one is a 400, not an empty list.
- `POST /api/v1/site/technical-seo/issues` — `{ runId?, kind, issue, severity?,
  state? }`, 201.
- `PATCH /api/v1/site/technical-seo/issues` — the bulk edit: `{ runId?, kind,
  state?, rejectionReason?, issue?, severity? }` → `{ runId, updated }`.
- `GET | PUT | PATCH | DELETE /api/v1/site/technical-seo/issues/:id`.

**Page issues** (`site_page_issues`)

- `GET /api/v1/site/technical-seo/page-issues?runId=&state=&severity=&kind=&pageId=&url=&limit=&offset=`
  → `{ runId, issues, total, shown, offset }`, each row carrying the page `url`.
- `POST /api/v1/site/technical-seo/page-issues` — `{ runId?, pageId | url, kind,
  issue, severity?, matchedPages? }`, 201. A URL that is not on record is a 404.
- `PATCH /api/v1/site/technical-seo/page-issues` — the bulk edit, filtered by
  `{ runId?, kind?, pageId?, url? }` (at least one) → `{ runId, updated }`. This
  is how a whole check is turned down in one go: a rule can flag thousands of
  pages, and the desk caps what it stores at 500 of the worst while
  `matchedPages` records how many there really were.
- `GET | PUT | PATCH | DELETE /api/v1/site/technical-seo/page-issues/:id`.

Any write to an issue stamps `reviewedAt`, which is what marks it as decided and
carries it onto the next run. Moving an issue back to `open` clears its
`rejectionReason`.

**Reading a run whole**

- `GET /api/v1/site/technical-seo/summary?runId=` — the run, open/turned-down
  counts for both tables, and the open issues grouped by check.
- `GET /api/v1/site/technical-seo/groups?runId=&state=` — one row per check
  rather than per page: wording, severity, how many pages it flagged, three
  example URLs, and the reason if it was turned down. This is what the desk
  screen renders; listing page issues row by row is for drilling into one check.
- `GET /api/v1/site/technical-seo/download?runId=&state=&kind=` — the CSV, up to
  50,000 rows, `content-disposition` naming it after the site and state. Rows go
  out as a file, not as data to page through.

## Analytics — sessions, and the reports kept in them

The analysis engine (the analytics MCP server) runs on the user's own device:
DuckDB sessions, ingested CSVs and intermediate tables never reach this
backend. What lands here is the frame around the work — the **session**, its
**sources** as metadata, and the finished artifacts worth keeping — so the web
can show what the agent built.

A **session** is one conversation about one body of data: what it is
(`about`), the sources attached to it, and the reports kept from it. It maps 1:1 to a device-local engine session
(`sessionKey`, filled in by the agent on first ingest). Sources are metadata
only — the CSV bytes live on the user's device under the app's analytics data
dir, and what is stored here is `filePath`, their location *relative* to that
dir: `sessions/<sessionId>/sources/<sourceId>.csv` for a file the user
attached, or the bare name a download tool wrote. Absolute paths and `..` are
rejected. A source over **1,000,000 rows is rejected** by the app, which counts
the lines before writing the file.

- `GET | POST /api/v1/analytics/sessions` — POST `{ title?, about? }`
  (`title` defaults to "Session N").
- `GET | PUT /api/v1/analytics/sessions/:id` — PUT takes `title`, `about`
  and/or `sessionKey`. There is no delete: nothing removes a session, and the
  CSVs and engine directory behind one live on the user's device anyway.
- `GET | POST /api/v1/analytics/sessions/:id/sources` — POST
  `{ name, filePath? }`.
- `DELETE /api/v1/analytics/sources/:id`. There is no PUT: the app writes the
  file to disk first and POSTs the row with its `filePath` already set.
- `GET /api/v1/analytics/workspace` — the desk in one call:
  `{ sessions, sources, reports }`, reports as summaries.

### Reports

One **self-contained** HTML document (inline CSS/SVG, no external fetches; it
renders in a sandboxed iframe) kept because the user asked to keep it.

- `GET /api/v1/analytics/reports?sessionId=` — summaries only: every field
  except `html`, plus `htmlBytes`. The payload is the whole weight of a row;
  the list never carries it. `sessionId` narrows to one session.
- `POST /api/v1/analytics/reports` — `{ title, html, sessionId? }`. `html`
  is capped at **8MB**; over it almost always means embedded raw data or
  base64 images, neither of which belongs in a report. `sessionId` is the
  session it came out of — pass it and the report shows on that session's
  page as well as the desk.
  - `html` must be **fully self-contained** and is rejected otherwise: no script/iframe/form/link/etc. elements, no
    `src`/`href`/`url()` pointing at another origin, no `@import`, no
    `http-equiv`. Sandboxed iframes block scripts but not resource loads, so
    an external reference would be a data-exfiltration channel for a
    prompt-injected agent; template output never contains one.
- `GET | PUT | DELETE /api/v1/analytics/reports/:id` — GET returns the full
  report including `html`; PUT takes `title` and/or `html` (same cap).

## Todos — one flat list, four blocks a day

The day divides into four six-hour blocks (`0` night, `1` morning, `2`
afternoon, `3` evening) and a todo sits in exactly one. Every incoming time is
floored to its block start **in the user's own timezone** (`UserProfile.timezone`,
falling back to UTC) — so `scheduledAt` is always a block start, and there is
no finer granularity to send. Design notes in `TODO_AGENT.md`.

- `GET /api/v1/todos?status=&date=&block=&from=&to=` — `date` is `YYYY-MM-DD`
  in the user's zone, which is not the same 24 hours as a UTC day.
- `POST /api/v1/todos` — `{ title, notes?, date?, block? }`, or a batch under
  `todos` (one bad entry comes back in `skipped`, the rest are created).
  Omitting the time puts it in the block happening now.
- `GET /api/v1/todos/day?date=` — one day already split into its four blocks.
- `GET | PUT | DELETE /api/v1/todos/:id` — PUT carries every edit: `{ block }`
  moves it within its day, `{ date, block }` (or `{ scheduledAt }`) moves it
  anywhere, `{ status }` ticks it off.
  - `status` is `open|done`. Crossing to `done` stamps `doneAt`; crossing back
    clears it. Unlike `posted` and `sent`, the agent may set both.
  - No slot collision and no minimum gap: a block holds as many todos as you
    like.

## Ideapad — write it down before it evaporates

Personal, not per-website, for the same reason todos are: an idea routinely
arrives before the business it belongs to. Design notes in `IDEAPAD_AGENT.md`.

- `GET /api/v1/ideas?search=&status=&tag=` — `status` is
  `spark|exploring|building|shelved`.
- `POST /api/v1/ideas` — `{ capture, title?, summary?, analysis?, tags?,
  status? }`, or a batch under `ideas` (one bad entry lands in `skipped`, the
  rest are created). **`capture` is the only required field**; the title is
  taken from its first sentence when omitted.
- `GET | PUT | DELETE /api/v1/ideas/:id` — on PUT, `""` clears an optional
  field.
  - **`capture` is written once.** A PUT that changes it is a **409** telling
    the caller to put the rewrite in `summary`. Sending the *identical* text
    back is a no-op, not an error. This is the rule the feature exists for: it
    is what makes it safe to let an agent iterate on someone's idea, because
    the worst it can do is write a bad summary next to the untouched original.
  - GET carries `similar[]` — earlier ideas that look like this one, scored on
    shared tags and uncommon words. Every create carries it too. It is a
    **nudge, not a block**, and deliberately the opposite of the prospect rule:
    the same idea arriving three times is the most useful thing this pad can
    tell someone about what they actually care about.
- `POST /api/v1/ideas/:id/note` — `{ note, at? }` appends one dated line to
  `notes`, dated in the user's own timezone. `analysis` is the standing take
  ("what do we think"); the notes are the trail ("how did we get here"), which
  is what makes `shelved` worth more than deleted.

## Suggestions — what the user thinks we should build

**Not the ideapad, and the distinction is why this is its own table.** An idea
is the person's own thinking: private, kept word for word, and costless to write
down — which is the only reason half-formed thoughts get captured at all. A
suggestion points the other way: it is addressed to *us* and expects to be read.
Collecting feedback through the pad would turn somebody's private notebook into
our inbox, and the first person to notice starts writing more carefully in the
one place that only works when they don't.

- `GET /api/v1/suggestions` — **the caller's own only.** Not an admin view: one
  user can never read another's, so the screen can show someone what they sent
  without this becoming a way to read everyone's feedback.
- `POST /api/v1/suggestions` — `{ body }`.
- `DELETE /api/v1/suggestions/:id` — withdrawing something you said is yours to
  do.

There is deliberately **no PUT**: a suggestion is a thing you said, stored in
your words, and the way to say something different is to say it. Equally
deliberate is the absence of a status or triage state — showing someone their
suggestion marked `declined` is worse than showing them nothing, and a promise
to reply is one this can't keep yet.

## Site notes — standing rules, and what was corrected

Two kinds of row in `site_notes`, told apart by `kind`: a `note` is guidance the
user gave on purpose, a `feedback` is a correction on something an agent
produced. Both are per website, both are embedded so they can be searched by
meaning as well as by word, and editing the text clears the embedding so the
next pass re-embeds it rather than matching the old wording.

- `GET /api/v1/site/notes?kind=&contains=&embedded=&createdAfter=&createdBefore=&sort=&limit=&offset=`
  → `{ notes, total, shown, offset }`, newest first; `sort` takes created or
  updated, and `kind` repeats or comma-joins.
- `GET /api/v1/site/notes?q=&mode=&kind=&limit=` — the same route searches when
  `q` is present, answering `{ hits, mode, embedded, note? }`. `mode` is `auto`
  by default and falls back to keyword until the notes are embedded; the reply
  says which mode ran, because a thin keyword answer is not the same as
  "nothing is recorded".
- `POST /api/v1/site/notes` — `{ note, kind? }`; the text is required and
  capped at 4000 characters, because a note is a standing rule or a correction,
  not a document.
- `GET | PUT | PATCH | DELETE /api/v1/site/notes/:id`.

The agent reads these before writing anything the user will see, and a note
that contradicts what it was about to write wins: it is the user's own
instruction, and they should not have to give it twice.

## Activity logging by domain

| Domain | agent | example summary |
|---|---|---|
| outreach/* | `outreach` | `Found prospect Dana Whitfield` / `Marked email sent: "Sponsoring your September issue"` |
| seo/* | `seo` | `Found: Every district has four near-identical URLs` / `Marked "…" accepted` |
| contacts/* | `contacts` | `Added contact Dana Whitfield (Fern Gully)` / `Logged contact with Dana Whitfield: Sent the September quote` |
| todos/* | `todo` | `Added "Pick up the parcel" to afternoon` / `Finished "Call the plumber"` |
| ideas/* | `ideas` | `Captured idea "What if the digest only went to lapsed users?"` / `Moved idea "…" to exploring` |
| site, profile, knowledge, keys | `system` | `Updated site profile` / `Updated website details for www.mahajob.in (4 pages read)` |
| suggestions/* | `system` | `Sent a suggestion: I'd want it to read email attachments too` |
| content/pages | `content` | `Drafted a new page: "The widgets guide"` / `Published "…" at https://…` |

### Log decisions and corrections, not only creations

A trail with holes cannot answer "what happened last month", but a trail of
nothing but creations is barely better: it says what exists and never says why.
Two kinds of line are worth more than any of the others and are the ones nobody
thinks to write.

**A decision, with its reason.** *"Rejected `meta-description-missing` at
`/pricing`, because we're not sending a competitor traffic"* is the most useful
line in any thread. Every refusal in this API — a rejected
issue, a declined verdict — logs the reason alongside it, which is also why
those endpoints refuse a rejection that arrives without one.

**A correction, with BOTH sides.** When the user overrules a verdict — the agent
said consolidate, they said write a hub page — the log stores what was proposed
as well as what was chosen:

> `Changed the verdict on thin-content at /guides: was accepted ("merge into the
> hub"), now rejected — "the two pages answer different questions"`

A thread that holds only outcomes cannot show where the judgement was wrong,
which is the one thing worth reading it for. Record the same correction as a
`feedback` note on the website, so the next run of the same shape reads it
before repeating the mistake.
