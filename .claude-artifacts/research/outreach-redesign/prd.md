# Outreach Desk — Redesign PRD

Date: 2026-09-14 · Status: proposal for review · Companion mockup: `design.html`

---

## 1. What the desk does today, and why it falls short

### The current shape (from the code)

**Data model** (`api/src/outreach/models/`): four tables.

- `projects` — the "standing brief": `name, goal, prompt, prospect_profile, search_criteria, email_tone, value_prop, cta`. All free text.
- `campaigns` — one row per "Run campaign" click: `project_id, requested_count, status(running/done/failed), summary`.
- `prospects` — `name, company, role, email, website, source_url, fit_reason, status(found/contacted/replied/won/rejected), dedupe_keys`. Belongs to a *campaign*, deduped per *project*.
- `conversations` — flat email rows on a prospect: `status(draft/…), from/to/cc/bcc, subject, body, message_id, thread_ref`.

**Agent surface** (`api/src/agent_scope/outreach/`): seven separate scopes — `project` (create brief), `edit-project`, `project-assist` (project-page chat), `run-campaign`, `edit-prospect`, `outreach-email` (draft), `compose-reply` (inline message box). Each carries a long single-task prompt and the same table list.

**UI** (`dashboard/src/app/dashboard/outreach/`): projects list → project detail with runs + prospects table → prospect drawer with a conversation. `sending-as.ts` reads the mailbox from the app's local IMAP integration; "Check inbox" pulls replies; Send goes through the interim IMAP path (the connector catalog / Resend server was deleted 2026-09-14; email is slated to become an app provider).

### Why it falls short

1. **Discovery is web-search-only and count-driven.** `run-campaign` tells the agent to WebSearch until it hits `requested_count`. The count is the target, so quality degrades toward filler leads at the tail of every run. There is no access to the scraper capability the Social Listening desk already proved out (Apify actors, public-free-first), even though "people asking for what you sell" on Reddit/LinkedIn/X *is* the prospect pool for most small sites.
2. **No qualification stage.** A prospect goes from "found by an LLM in one search session" straight to "draft an email". `fit_reason` is one sentence written by the same agent that found the lead, graded against a free-text `prospect_profile` — never against what meelu actually knows about the site (profile, corpus, keywords). Nothing separates "scraped a name" from "verified, has an email, worth the user's send".
3. **Two entities where one belongs.** Project vs campaign confuses every prompt ("a project is the standing brief that its campaigns execute"). A campaign row is really just a *run log* of one discovery job; it earns a table, FK, cascade rules, and three MCP tools it doesn't need. Prospects belong to a run, not to the play.
4. **One status enum mixes lead stage and deal stage.** `found/contacted/replied/won/rejected` can't express "qualified but no email yet", "draft awaiting my approval", or "followed up twice, gone cold" — which are the states a user actually manages.
5. **The email loop is manual and stateless.** Flat `conversations` rows, no thread entity, no follow-up scheduling, no "waiting on them / waiting on you" view. Replies arrive only when the user clicks "Check inbox". Nothing tracks that a lead has been silent for 9 days.
6. **Seven agent scopes, all currently write-less.** Since 2026-09-12 every `outreach_*` write named in those prompts is unregistered — the actions are read-only and the prompts lie about their own tools. The surface needs rebuilding anyway; rebuilding seven single-task chats is the wrong target.
7. **The desk violates its own bulk-data rule.** The prospects table pages through the UI, but there is no CSV download for the agent/Analytics desk; the `run-campaign` agent instead holds every lead in context.

---

## 2. The redesign

### Thesis

Outreach becomes a **pipeline desk**: meelu finds and qualifies leads *locally in the app* (scrapers + web search + the site profile it already has), the user stays the **sender and approver** of every email, and the desk's job is to keep an honest picture of where each lead stands. One entity for the play (**campaign**), one for the person (**lead**), one thread per lead. Discovery mirrors Social Listening's proven pattern: public-free-first, Apify fallback, user's own token, pipeline runs in the app and writes results to the api.

### The three loops

1. **Discovery loop (local app process, scheduled or on-demand).** For each active campaign: expand the brief into queries → fan out over enabled sources (web search + Apify scrapers for LinkedIn/Reddit/X/YouTube/directories, public callers first) → normalize to one Lead shape → dedupe against the site's existing leads → **qualify**: score fit against the campaign brief *and the site profile* (what the site sells, who it serves, its keywords), attach evidence quotes and source URLs → write qualified leads to the api with `fit_score`, `fit_reason`, `evidence`. Never invent an email; enrichment (finding the address on a page the pipeline actually fetched) is a step, not a guess. The run writes a row to `outreach_runs` as its log. **The api never calls a vendor.**
2. **Compose-and-approve loop (agent drafts, user sends).** From a lead the user (or an agent task) drafts a personalized email grounded in the lead's evidence, the campaign angle, and the user's profile sign-off. The draft sits in the thread as `status=draft`. The user edits, then clicks **Approve & send** — the app's email provider facade (Resend/SMTP adapter, user's own account) sends it and writes back `sent` + `message_id`. **Sending is a button, never an MCP tool.**
3. **Reply loop (local sync + triage).** The app's mailbox integration syncs the thread on a schedule (interim IMAP path today; the email provider facade when it lands), matching by `message_id`/references. New replies flip the lead to `replied` and surface in the Conversations tab with a suggested next move. Leads silent past the campaign's follow-up window surface as "nudge due" — the agent drafts the follow-up, the user approves it like any other send.

### User journeys

- **Start a play**: New campaign → meelu proposes the brief from the site profile ("who to look for, where, what to say") → user edits chips/fields → enable sources → Find leads now, or leave it on the weekly schedule.
- **Work the pipeline**: Leads tab, filtered to "Qualified". Open a lead drawer: who they are, why they fit (evidence quotes with source links), draft with meelu, approve & send.
- **Handle replies**: Conversations tab shows threads where the ball is in the user's court, each with meelu's suggested reply angle. Reply inline, approve & send.
- **Add a lead by hand**: "+ Add lead" on the Leads tab — a name, a URL, optionally an email and a note about why. Saved as qualified into a chosen campaign (or as a one-off); meelu then reads the URL, fills the evidence and fit score, and verifies the email — a hand-added lead flows through the same pipeline as a discovered one. This is also how a lead met offline (an expo, a referral) enters.
- **Ask questions**: "✱ Ask meelu" opens a desk-scoped agent task ("which SaaS leads from last week haven't been contacted?", "rewrite the pet-blogger campaign angle"). Anything analytical over the whole pipeline: **Download data** → CSV path → Analytics desk.

### Screens (see `design.html`)

| Tab | Purpose |
|---|---|
| **Overview** | Pipeline funnel tiles, "waiting on you" queue (approvals due + replies to answer + nudges due), live run strip, campaign summary cards. |
| **Campaigns** | Campaign list + brief editor: audience, angle/value prop, CTA, tone, source chips (public-free vs Apify-token, mirroring Social Listening's platform chips), schedule, follow-up window. |
| **Leads** | The pipeline table: stage rail (found → qualified → contacted → replied → won/lost), fit-score meter, evidence on hover, lead drawer for detail + drafting; "+ Add lead" inline form for manual entry (meelu enriches it afterwards). |
| **Conversations** | Thread-centric view of every open email exchange, grouped by "needs your reply / awaiting approval / waiting on them / nudge due". |

Header actions: **✱ Ask meelu** (primary) · Find leads now · Download data (CSV).

### Data model sketch

```
outreach_campaigns          (replaces projects + absorbs campaign-as-play)
  id, site_id, user_id, name, status(active|paused|archived)
  audience          text     -- who to look for (required)
  angle             text     -- value prop / what the email says
  cta               text
  tone              text
  sources           text[]   -- enabled source keys ('web-search','apify:linkedin',…)
  schedule          text     -- off|weekly|daily
  followup_days     int      -- nudge window; 0 = no follow-ups

outreach_runs               (replaces campaigns-as-run; written by the app pipeline)
  id, site_id, user_id, campaign_id FK
  status(running|done|failed), started_at, finished_at
  found int, qualified int, skipped_duplicates int, summary text

outreach_leads              (replaces prospects; deduped per SITE, not per project)
  id, site_id, user_id, campaign_id FK, run_id FK nullable
  name, company, role, email, website, channel_handles jsonb
  source, source_url
  fit_score numeric, fit_reason text, evidence jsonb   -- quotes + urls from the pipeline
  stage(found|qualified|contacted|replied|won|lost), stage_changed_at
  dedupe_keys text[] (gin)

outreach_messages           (replaces conversations; one implicit thread per lead)
  id, site_id, user_id, lead_id FK
  direction(out|in), status(draft|approved|sent|received)
  subject, body, from, to, cc
  message_id, in_reply_to, sent_at
```

### Who does what

| Step | Owner |
|---|---|
| Discovery + qualification + enrichment | **Local app process** (`app/src/main/outreach-pipeline/` + a `ProspectSource` facade under `app/src/main/providers/` — public-free-first, Apify adapter fallback, same pattern as `social_listening`). Writes leads/runs to api over HTTP. |
| Brief authoring, lead edits, email drafting, follow-up drafts, pipeline questions | **Agent actions** (desk chat + inline compose), collapsed from seven scopes to three: `outreach` (desk/campaign chat), `outreach-draft` (compose one message), plus the discovery task the app harness runs with web search + the in-process scraper tools. |
| Approve & send, mark won/lost, pause campaign, run now | **Buttons** (IPC → app email provider / pipeline; api CRUD). |
| Reply sync | **Local app schedule** (mailbox integration → api). |
| Analytics over the pipeline | **Not this desk.** Download CSV → Analytics desk. |

### MCP write tools (minimal — four)

- `outreach_save_campaign` — create or patch one campaign brief.
- `outreach_update_lead` — patch one lead's fields/stage (never past `contacted`; `sent` transitions come from the app).
- `outreach_add_leads` — batch-insert qualified leads for a run (used by the discovery task; server enforces site-wide dedupe).
- `outreach_save_draft` — upsert one outgoing draft message on a lead.

Reads stay on the direct SQL surface. No send tool, no delete tools (deletes are UI buttons), no run-status tool (the app owns run rows via the api). Bulk export is a shared-shape download tool that writes a CSV under `MEELU_DATA_DIR` and returns the path.

### What got cut

- The **project/campaign split** — one `campaigns` entity; runs become logs.
- **`requested_count`** and count-driven runs — the pipeline keeps what qualifies.
- **Five of seven agent scopes** (`project`, `edit-project`, `edit-prospect`, `run-campaign`, `compose-reply` as separate prompts) — folded into desk chat + one composer.
- **"Check inbox" as a user chore** — replaced by scheduled sync.
- Prospect `status` doubling as deal tracker — split into `stage` with app-owned transitions.
- Web-search-only discovery — sources are pluggable providers in the app.

---

## 3. Open questions for you

1. **Lead dedupe scope**: the sketch dedupes per *site* (a person contacted once is claimed for all campaigns). Per-campaign instead, or per-site with an explicit "release" action?
2. **Follow-ups**: is one nudge window per campaign enough, or do you want a real sequence editor (step 1 / step 2 / breakup email)? The sketch deliberately stops at one nudge.
3. **Non-email channels**: leads found on Reddit/X often have no email. Keep them as "qualified, no address — contact on-platform yourself" (copy-a-DM like Social Listening's v0), or drop email-less leads entirely?
4. **Qualification LLM**: run it in the app harness (costs the user's Claude session per run) like Social Listening's classify step, or keep discovery pure-mechanical and let a desk agent task qualify in batches on demand?
5. **Email provider timing**: does this redesign wait for the planned `email` provider facade, or ship on the interim IMAP send path first?
6. **Won/lost**: do you actually want deal-outcome tracking on this desk, or is "replied" the end of meelu's job and the CRM lives elsewhere?
