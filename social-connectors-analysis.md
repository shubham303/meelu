# Social publishing for Meelu — vendor & build analysis

*Researched 2026-08-02. Prices from vendors' own pricing/docs pages, not blog roundups.*

## 1. Decision frame

Meelu's constraints, in order of scarcity:

1. **Approval calendar time** — platform app reviews (LinkedIn partner, Meta review,
   TikTok audit) take weeks-to-months and can't be parallelized away. Code is cheap
   (Claude); approvals are not.
2. **Recurring cost** — the server must stay cheap; per-user vendor fees are fine only
   if users pay them or revenue covers them.
3. **Architecture fit** — local-first agent, MCP tools, scopes + approvals inbox;
   the backend stays CRUD + (eventually) connections/executor. No LLM server-side.

The structural fact that organizes every option: **platform-approval pain attaches to
whoever owns the platform developer apps.** Vendors rent you their approved apps.
Self-hosting an open-source scheduler does *not* dodge approvals — you must register
your own LinkedIn/Meta/TikTok/X apps behind it.

Three ownership stages:

| Stage | Who owns the vendor relationship | Who owns platform apps | Meelu builds |
|---|---|---|---|
| **V1 — BYO** | the user (their subscription/key) | vendor | catalog entry + agent guidance |
| **V2 — native connect** | Meelu (one vendor contract or OAuth app) | vendor | connect UX, custody, proxy routes |
| **V3 — own platform** | — | **Meelu** | everything + approvals + churn forever |

## 2. Vendors

### 2.1 Postiz — three distinct commercial faces

Postiz is not just "the open-source one." It sells three ways, and they map to
different Meelu stages:

**(a) Cloud subscription (BYO — stage V1).**
All plans include **unlimited posts, the public API, webhooks, and the hosted MCP
server at no extra cost**:

| Plan | $/mo | Channels | Notes |
|---|---|---|---|
| Standard | $29 | 5 | no team, no AI images |
| Team | $39 | 10 | unlimited team members |
| Pro | $49 | 30 | |
| Ultimate | $99 | 100 | |

- Official hosted MCP: `https://api.postiz.com/mcp/{API_KEY}` — works in Claude,
  ChatGPT, Cursor, Claude Code. Tools: list channels, create/draft/schedule/publish
  posts, uploads, image/video generation.
- Public API: posts CRUD, integrations list, upload, analytics across **32 platforms**.
  Create-post rate limit: **90 req/hr** on cloud (fine for scheduling, relevant for
  bulk agent runs).

**(b) Cloud as a developer platform (stage V2, user-pays variant).**
The public API supports **OAuth2 for third-party apps** ("building apps serving other
users", `pos_` tokens). Meelu can register as a Postiz OAuth app: user clicks
"Connect Postiz" in Meelu, authorizes in the browser, no API-key copying. Billing
stays on the user's own Postiz account. This is native-connect UX **without Meelu
paying per profile** — a middle path none of the API-first vendors offer.

**(c) Self-host (stage V3 stepping stone).**
AGPL-3.0. Free for commercial use. Requires your own platform developer apps (the
approval gauntlet, §3) and real infra: PostgreSQL, Redis, Temporal, Node 22,
S3-compatible storage (~$30–60/mo VPS). License rules:
- Meelu's proprietary code is safe — AGPL doesn't cross the HTTP API boundary.
- Run it **unmodified** and the network clause never triggers. Never patch the fork;
  customize in your own layer. Any modification you serve to users must be published
  under AGPL.
- Their trademark isn't licensed — strip branding when white-labeling.

### 2.2 Postproxy — cheapest flat-rate API-first (stage V2)

API-first by design ("the UI exists for visibility and debugging"). Native MCP.
**11 platforms**: Instagram, Facebook, Threads, TikTok, X, YouTube, LinkedIn,
Pinterest, Bluesky, Telegram, Google Business.

| Plan | $/mo | Profile groups | Posts |
|---|---|---|---|
| Free | $0 | 2 (≤22 profiles) | 10/mo |
| Build | $17 | 10 | 120/mo |
| Grow | $49 | 20 | unlimited |
| Scale | $99 | 50 | unlimited, SSO |
| Enterprise | $699 | 500 | unlimited |

A "profile group" ≈ one Meelu user's set of socials, so the plan tier ≈ user count.

### 2.3 Zernio (formerly Late) — graduated per-account (stage V2)

**First 2 accounts free**, then $6/acct (3–10), $3 (11–100), $1 (101+). Every feature
on every plan, unlimited posts, webhooks; MCP server exposing publishing/analytics.
12 social platforms + WhatsApp/Telegram/Discord messaging + ad networks.
Example: 100 accounts ≈ $318/mo.

### 2.4 SocialAPI.ai — unified inbox angle, MCP on the free plan

| Plan | $/mo | Profiles | Posts |
|---|---|---|---|
| Hobby | $0 | 2 | 10/mo |
| Side Hustle | $29 | 10 | unlimited |
| Full Send | $109 | 50 | unlimited |
| Empire | $349 | 200 | unlimited |

**MCP access on the free plan.** 7 platforms (IG, FB, TikTok, YouTube, X, LinkedIn,
Google Business). Differentiator: full unified inbox (comments, DMs, reviews,
mentions) — relevant if Meelu ever does engagement, not just publishing.

### 2.5 Ayrshare — the incumbent, priced for funded SaaS

Premium $149/mo for **1 profile**; Launch $299 (10 profiles); Business $599 base
(30 profiles, then $8.99 → $3.49 → $2.49 per profile); Max Pack +$300/mo for max
posting limits; DM metering $0.09/conversation. 13 networks. Mature SDKs, white-label
user-connect page on Business. **Its MCP is documentation-only — it cannot execute
actions.** Ruled out on price and MCP for Meelu's stage.

### 2.6 Buffer — MCP beta, platform-risk history

Official MCP server shipped early 2026 (public beta, GraphQL API, personal-key
access, 11 channels). Viable BYO fallback with a strong free tier — but Buffer
revoked its entire public API in 2019 once before. Don't build the primary path on it.

## 3. Owning the platform apps (stages V2b/V3)

What it takes per platform, as of mid-2026:

| Platform | Approval | Time | Ongoing cost |
|---|---|---|---|
| LinkedIn (member posting) | self-serve products (OIDC + Share on LinkedIn) | days | free; 60-day tokens, no refresh |
| LinkedIn (refresh tokens, org pages) | Community Management API: registered legal entity, verified company page, dev tier → standard tier + screencast | 4–8 wks fast, 3–4 mo typical | free |
| Meta (FB + IG) | app review + business verification | weeks–2 mo | free |
| TikTok | content-posting audit (unaudited = private-only posts) | weeks | free |
| YouTube | API audit for quota | weeks | free |
| **X** | none — but no free tier since Feb 2026 | immediate | **$0.015/post, $0.20/post with a link**, $0.005/read |
| Bluesky, Mastodon, Reddit, Telegram | trivial | hours | free |

Notes:
- LinkedIn partner requires a **registered legal entity** — solo developers are
  ineligible. This gates the timeline more than any code.
- X's per-link-post pricing ($0.20) makes owning an X app nearly always worse than a
  vendor's pooled access for outreach-style content. X likely stays vendored forever.
- Approvals are also *maintenance*: platform API churn, deprecations, re-reviews.
  Vendors sell absorption of that churn, not code.

## 4. Cost model

Assume ~4 connected socials per Meelu user.

**V1 (user pays, Meelu pays $0):** per-user monthly cost of the BYO account —

| Vendor | Light user (free tier) | Real user |
|---|---|---|
| Postiz cloud | — (no free cloud tier) | $29 |
| Postiz self-host | $0 (their own infra + apps — power users only) | $0 |
| SocialAPI.ai | $0 (2 profiles, 10 posts/mo, **MCP included**) | $29 |
| Postproxy | $0 (10 posts/mo) | $17 |
| Zernio | ~$12 (2 free + 2×$6) | ~$12 |
| Buffer | free tier | — |

**V2 (Meelu pays):** monthly vendor bill by active users —

| Users (≈profiles) | Postproxy | Zernio | SocialAPI.ai | Ayrshare |
|---|---|---|---|---|
| 10 (40) | $17–49 | ~$138 | $109 | $299 |
| 50 (200) | $99 | ~$418 | $349 | ~$780 |
| 200 (800) | $699 | ~$1,018 | enterprise | ~$1,580 |
| Postiz OAuth2 path | **$0 to Meelu** (each user's own account) | | | |

**V2b/V3 (own apps):** infra $30–60/mo + X pay-per-use + **1–3 months of approval
calendar** + permanent churn ownership. Break-even vs Postproxy Scale ($99) is real
only past ~50 paying users *and* only if the approval time has option value anyway.

## 5. Risks

- **Vendor viability**: Postproxy/Zernio/SocialAPI.ai are young companies; Postiz has
  open-source gravity and a self-host escape hatch (your data model doesn't depend on
  it anyway — posts live in Meelu). Ayrshare is the established one, at 5–10× the price.
- **Buffer precedent**: platforms and aggregators both kill APIs. Mitigation: Meelu's
  own tool schema (§6), posts stored in Meelu, vendor swap = catalog change.
- **Rate limits**: Postiz 90 posts/hr (cloud) — batch bulk agent runs; add agent
  guidance to schedule rather than fire rapid sequential posts.
- **ToS posture**: human-approves-every-post (Meelu's approvals inbox) is the safe
  posture on every network; keep social writes out of default always-allow.

## 6. Recommendation

1. **Now (V1, ~1 day):** Add a **Postiz** catalog entry — official hosted MCP, key
   field, agent guidance (mark scheduled posts back onto Meelu content records with
   the Postiz post ID so the agent can reschedule/cancel). Optionally add
   **SocialAPI.ai** as the zero-cost BYO alternative (free tier includes MCP).
2. **Now, in parallel (days, free):** Register the **LinkedIn self-serve app**
   (company page + privacy policy + OIDC + Share on LinkedIn). It's the only
   quick-and-valuable own-app approval, and the future direct-LinkedIn path
   (60-day tokens + backend token custody) starts here.
3. **When users resist creating vendor accounts (V2):** Prefer **Postiz OAuth2**
   first (native connect UX, still $0 to Meelu), then **Postproxy** ($17–99 flat) if
   Meelu should absorb billing. Only now do connections/custody/proxy routes enter
   the backend.
4. **Later, selectively (V3):** In-source platforms one at a time on real numbers.
   LinkedIn first (partner application needs the registered entity — start that
   paperwork when V2 revenue exists). **Never in-source X** at current pricing.
5. **Design once:** define Meelu's own MCP tool schema for social actions
   (`social_schedule_post`, `social_list_channels`, `social_cancel_post`) as a thin
   wrapper when V2 begins — so V1→V2→V3 swaps never change agent prompts or user
   habits. At V1, raw Postiz tools are fine; don't build abstraction before the
   second backend exists.

## 7. Decision (2026-08-02): Postproxy, integrated server-side

Chosen over Postiz-BYO for two reasons beyond price: **Postiz is a destination app**
(calendar UI, AI copilot) that competes with Meelu for the user's attention, while
Postproxy is infrastructure with aligned incentives; and a $29/mo third-party
subscription at V1 is an adoption tax.

Verified capabilities that make it fit:

- **Per-profile-group scoped API keys** — a group's key cannot see other groups or
  account-level resources. One group per Meelu account = per-user isolation.
- **White-label connect**: `initialize_connection` on a group returns an OAuth URL;
  users connect socials through Meelu's UI, never seeing Postproxy.
- **Native scheduling** (scheduled / triggered / on-demand, queues) — no Temporal,
  no cron executor needed for social. Resend covers email scheduling the same way.

### Architecture

1. **Provisioning (backend, master key)**: when an account enables social, create a
   Postproxy profile group + scoped key; store the scoped key encrypted on the
   account. Master key is used for provisioning only, never for posting.
2. **Connect UX (app + backend)**: backend calls `initialize_connection` → OAuth URL
   → user authorizes each network in the browser. Meelu-branded end to end.
3. **Agent tools — a separate `meelu-social` MCP server, shipped with the app**
   (his call; fits "Meelu is the memory, other MCP servers are the hands"): own
   schema (`social_list_channels`, `social_schedule_post`, `social_cancel_post`),
   never Postproxy's MCP. It's a catalog entry with **zero credential fields** —
   authenticates with the user's Meelu API key, calls backend proxy routes, which
   call Postproxy with the group's scoped key and record status (Postproxy post ID,
   scheduled/published state) on the content record atomically. Dual-use for free:
   standalone users install it in Claude Code/any host and it works identically.
   Other social MCP servers (Postiz BYO, Buffer) remain in the catalog as
   alternatives; connector-scoped launches attach exactly one.
4. **Vendor swap insurance**: because agents and users only ever see Meelu's tool
   schema and posts live in Meelu's backend, replacing Postproxy (or in-sourcing a
   platform at V3) is a backend-only change.

Costs: free tier (10 posts/mo account-wide) for development; Build $17/mo ≈ 10
users; Grow $49 ≈ 20; Scale $99 ≈ 50 — price into Meelu's paid plan. Temporal
explicitly rejected for now: no "execute at time T" job remains server-side, and a
cron poller is the first resort if one appears.

## Sources

- Postiz: [pricing](https://postiz.com/pricing), [public API docs](https://docs.postiz.com/public-api), [MCP](https://postiz.com/mcp)
- Postproxy: [pricing](https://postproxy.dev/pricing), [X API pricing 2026](https://postproxy.dev/blog/x-api-pricing-2026/)
- Zernio: [pricing](https://zernio.com/pricing)
- SocialAPI.ai: [pricing](https://social-api.ai/pricing)
- Ayrshare: [pricing](https://www.ayrshare.com/pricing)
- LinkedIn partner: [Community Management overview](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/community-management-overview), [approval walkthrough](https://singhamandeep.com/linkedin-community-management-api-access/)
- Buffer API history: [Postproxy analysis](https://postproxy.dev/blog/what-happened-to-buffer-api-alternatives-for-developers/)
- AGPL: [fastCRW — AGPL for SaaS](https://fastcrw.com/blog/agpl-3-for-saas-explained)
