# Production launch plan

Goal: get Meelu into real users' hands on macOS and Windows, then fix the
bugs they actually hit. This plan covers no test database and no test
framework yet. Those come later, if users show up.

Written 2026-10-08. Related: `deployment-security-checklist.md` (go through
it before the announcement).

Items marked **⚠** would block or hurt the launch.

---

## 0. Two corrections first

- **Cloudflare doesn't rent VPSes.** Use a cheap VPS, for example Hetzner
  CPX31 (4 vCPU / 8 GB, about €15/mo). The api and embed worker load
  embedding models, so 4 GB is tight. Put Cloudflare in front of it for DNS,
  TLS and a Tunnel, and use Cloudflare R2 to host the installers and update
  files. The stack is 4 long-running Python/Node processes plus models,
  which doesn't fit Workers or Containers well.
- **⚠ CLAUDE.md says "Nothing is in production… drop columns freely."**
  That stops being true on launch day. Once real users sign up, an Alembic
  migration that drops a column deletes their data. Old app versions will
  also call the new server. Update that section when you launch (section 8
  has the rules that replace it).

---

## 1. Accounts to set up

| What | Why | Cost |
|---|---|---|
| Supabase **Pro** + **IPv4 add-on** | Free tier pauses after a week of inactivity. IPv4 gives a direct connection, which the agent server needs (see 2) | ~$29/mo |
| Hetzner VPS (same region as Supabase, e.g. Falkenstein ↔ eu-central-1) | api, agent, worker, dashboard | ~€15/mo |
| Apple Developer Program | **Required.** Unsigned Mac apps barely open on recent macOS, and Mac auto-update refuses unsigned apps. Start this first: enrolment can take days | $99/yr |
| Cloudflare R2 bucket on `downloads.meelu.tech` | Installers + update files, no egress fees | ~free |
| SMTP provider (Resend or similar) | **⚠** Supabase's built-in email sends only a few emails per hour, so signup confirmations will fail | free tier |
| Sentry (free) | You can't fix bugs you can't see on other people's machines | free |
| Windows code signing | **Skip for now.** Users click "More info → Run anyway" on SmartScreen. Auto-update still works unsigned | later |

- [ ] Supabase Pro + IPv4 add-on
- [ ] VPS
- [ ] Apple Developer enrolment
- [ ] R2 bucket + custom domain
- [ ] SMTP provider, domain verified (SPF/DKIM)
- [ ] Sentry projects: `api`, `dashboard`, `app`

---

## 2. Database: Supabase

- [ ] Create the project (or reuse the one that already handles Auth) in the
      region next to the VPS. The api makes many small queries, so the
      distance between server and database matters a lot.
- [ ] **⚠ Turn off the Data API** (Project Settings → Data API). The
      publishable key is baked into the dashboard. With the Data API on,
      anyone holding it can read or write the `public` tables through
      PostgREST. Meelu doesn't use PostgREST.
- [ ] Use the **direct connection** (`db.<ref>.supabase.co:5432`, reachable
      over IPv4 with the add-on). Don't use the transaction pooler.
      `api/src/agent/security.py` creates a login role per user and the
      agent server connects as that role. That works unchanged on a direct
      connection. Through Supavisor, usernames would need a `.<ref>` suffix,
      and psycopg prepared statements fail in transaction mode.
- [ ] Connection budget: Pro Micro allows about 60 connections. Lower
      `DATABASE_POOL_MAX` from 20 to about 8 for the api, and check the
      agent and per-tenant limits (`agent_tenant_connections`) so the total
      stays under 60. Upgrade compute if it gets tight.
- [ ] Extensions: the migration needs only `vector` and `pg_trgm`, and
      Supabase has both. ParadeDB's `pg_search` isn't used anywhere, so
      moving off ParadeDB is safe.
- [ ] Auth → URL Configuration: Site URL `https://app.meelu.tech`, redirect
      URL `https://app.meelu.tech/auth/callback`.
- [ ] Auth → SMTP: your provider.
- [ ] Auth → Providers → Google: production OAuth credentials.
- [ ] Backups: Pro includes 7 days of daily backups. Add point-in-time
      recovery once you have paying users.

---

## 3. Server: VPS + Cloudflare

Domains:

| Hostname | Points to | Notes |
|---|---|---|
| `app.meelu.tech` | dashboard:3000 | Proxies `/api` to the api. The api itself gets no public address |
| `agent.meelu.tech` | agent:8484 | Desktop apps connect here over MCP, authenticated with the workspace API key |
| `downloads.meelu.tech` | R2 bucket | Installers and update files |

- [ ] Install Docker on the VPS, clone the repo, write `.env` (section 6).
- [ ] In the prod compose overlay, replace Caddy with a `cloudflared`
      container. A Tunnel needs no open ports, and Cloudflare handles TLS.
- [ ] In the same overlay, disable the `postgres` service and point
      `API_DATABASE_URL` at Supabase. Use `depends_on: !reset` to drop the
      postgres dependency. `migrate` then runs `alembic upgrade head` against
      Supabase on every deploy.
- [ ] Firewall: allow SSH only. With the Tunnel, nothing else needs to be
      open.
- [ ] Deploy script:
      `git pull && docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`.
      Run it by SSH or from a GitHub Action on push to `main`.
- [ ] Uptime check: a free UptimeRobot or Cloudflare health check on
      `app.meelu.tech`.

Watch for: Cloudflare cuts off a proxied response if no bytes arrive for 100
seconds (error 524). If an MCP tool call runs longer than that without
streaming, it will fail. That would be a code fix, not a config change.

---

## 4. Code changes

### Server and dashboard

- [ ] `api/src/auth.py:42` sets the session cookie with `secure=False`. Read
      it from settings and set it to true in production.
- [ ] Production `.env`: `CORS_ORIGINS=["https://app.meelu.tech"]`,
      `DODO_PAYMENTS_RETURN_URL`, and the dashboard build args with the
      production Supabase URL and key.
- [ ] **⚠ Google sign-in breaks inside the desktop app.**
      `app/src/main/index.js:620` sends any off-site navigation
      (accounts.google.com included) to the system browser, so the callback
      lands in the browser instead of the app. For launch, hide "Continue
      with Google" when the dashboard runs inside the app, and keep email +
      password there. Later, add a `meelu://` deep link. Google sign-in on
      the web is fine.
- [ ] Add a minimum app version check (cheap, and it gets you out of jams
      later). The app sends an `x-meelu-app-version` header and the scope
      response includes `min_app_version`. If the app is older, the
      dashboard shows an "Update Meelu" banner.
- [ ] Sentry in FastAPI (api + agent) and Next.js.

### Electron app (`app/`)

Today the app README says "packaging/signing/auto-update: deliberately
later". All of this is new.

- [ ] **Production defaults.** `app/src/main/config.js` falls back to
      `http://localhost:3000` and `http://127.0.0.1:8484/mcp/`. When
      `app.isPackaged`, it should default to `https://app.meelu.tech` and
      `https://agent.meelu.tech/mcp/`.
- [ ] **⚠ Never ship `app/.env`.** It holds your own keys. Exclude `.env`,
      `dev/`, `test/` and `scripts/` from the build. `oauth-client.json`
      must stay in it.
- [ ] **electron-builder config** (in `app/package.json` `build` or
      `electron-builder.yml`):
  - App id `tech.meelu.app`, product name `Meelu`.
  - Mac targets: `dmg` + `zip`. The zip is what Mac auto-update uses.
  - Windows target: `nsis`, x64.
  - `asarUnpack` for native files: `**/*.node`, `onnxruntime-node`, and the
    Agent SDK's platform binary package.
  - Mac: `hardenedRuntime: true`, entitlements (JIT and unsigned
    executable memory; library validation off if the bundled binaries need
    it), and notarization with `APPLE_ID`, `APPLE_APP_SPECIFIC_PASSWORD` and
    `APPLE_TEAM_ID`.
  - Icons: `build/icon.icns` and `build/icon.ico`.
  - `publish: { provider: generic, url: https://downloads.meelu.tech/app/ }`.
- [ ] **Auto-update.** Use `electron-updater`. Check for updates at boot and
      every 6 hours, download in the background, then show a "Restart to
      update" prompt.
- [ ] **Build on each OS.** The Agent SDK installs a platform-specific binary
      (`@anthropic-ai/claude-agent-sdk-darwin-arm64` on this Mac), so you
      can't cross-build. Add `.github/workflows/release.yml`, triggered by an
      `app-v*` tag:
  - Matrix: `macos-14` (Apple Silicon) and `windows-latest`.
  - Steps: `npm ci`, then `electron-builder --publish never` (signs and
    notarizes on Mac).
  - Upload `dist/*` (installers, `.blockmap`, `latest.yml`,
    `latest-mac.yml`) to R2 with the S3 API
    (`aws s3 cp --endpoint-url https://<account>.r2.cloudflarestorage.com`).
  - Also copy the installers to fixed names (`Meelu-mac-arm64.dmg`,
    `Meelu-Setup.exe`) so the website links never change.
  - Secrets: Apple credentials, the signing certificate (`CSC_LINK`,
    `CSC_KEY_PASSWORD`), and R2 keys.
- [ ] **Model access for end users.** By default the harness uses your
      Claude Code login, and users won't have one. Anthropic also doesn't
      allow third-party apps to offer claude.ai login. Users bring an
      Anthropic or OpenRouter API key through the Connections screen. Check
      that an agent action without a key shows a clear "add a key in
      Connections" message instead of failing quietly.
- [ ] Sentry in the main process and the renderer.
- [ ] A "Copy logs" or "Report a problem" action, so a tester can send you
      what happened.

### Website (`meelu-website`)

- [ ] Add a `/download` page. It detects the user's OS, shows one main
      button and a link for the other OS, and links to the fixed filenames
      on `downloads.meelu.tech`. Include a one-line SmartScreen note for
      Windows ("More info → Run anyway").
- [ ] Change the homepage "Join the waitlist" button (`#waitlist`) to
      "Download".
- [ ] Email the waitlist when it's live.

---

## 5. Third-party services in production mode

- [ ] **Google OAuth (Search Console / GA):** switch the consent screen from
      Testing to **In production**. In Testing, refresh tokens expire every
      7 days. `analytics.readonly` is a sensitive scope, so submit
      verification (privacy policy, homepage on meelu.tech, demo video).
      Until it clears, users see an "unverified app" warning and you're
      limited to 100 users.
- [ ] **Dodo:** switch to live mode (needs business verification) and set
      the webhook to
      `https://app.meelu.tech/api/v1/payments/webhooks/dodo`, subscribed to
      `payment.succeeded`, `payment.failed` and `payment.cancelled`. Until
      then you can launch with only the signup credit grant.
- [ ] **DataForSEO, Apify, OpenRouter:** production keys, plus spending
      limits on each vendor dashboard. A bug that loops should hit a cap,
      not your card.

---

## 6. Production `.env` (VPS)

```dotenv
API_DATABASE_URL=postgresql+psycopg://postgres:<password>@db.<ref>.supabase.co:5432/postgres
DATABASE_POOL_MAX=8

NEXT_PUBLIC_SUPABASE_URL=https://<ref>.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=

CORS_ORIGINS=["https://app.meelu.tech"]

DATAFORSEO_AUTH=
APIFY_API_KEY=
OPENROUTER_API_KEY=

DODO_PAYMENTS_API_KEY=
DODO_PAYMENTS_WEBHOOK_SECRET=
DODO_PAYMENTS_BASE_URL=https://live.dodopayments.com
DODO_PAYMENTS_CREDITS_PRODUCT_ID=
DODO_PAYMENTS_RETURN_URL=https://app.meelu.tech/dashboard

CREDITS_SIGNUP_GRANT_USD=5

CLOUDFLARE_TUNNEL_TOKEN=
SENTRY_DSN=
```

Keep this file only on the VPS and in a password manager. Never commit it.

---

## 7. Manual test pass (before you announce)

Test on a **clean** Apple Silicon Mac and a **clean** Windows 11 machine (a
friend's machine or a VM, not your dev Mac).

| # | Check | Mac | Win |
|---|---|---|---|
| 1 | Download from the website, install, open. Gatekeeper and SmartScreen behave as expected | [ ] | [ ] |
| 2 | Sign up with email, confirmation email arrives, onboarding finishes | [ ] | [ ] |
| 3 | Add a site. The crawl runs, page classification fills in on the server, pages become searchable | [ ] | [ ] |
| 4 | Connect Search Console and GA, data syncs | [ ] | [ ] |
| 5 | Add an API key in Connections, run an agent task | [ ] | [ ] |
| 6 | A paid vendor call deducts credits | [ ] | [ ] |
| 7 | Quit and reopen: still signed in, data still there | [ ] | [ ] |
| 8 | **Updater:** release 0.1.1 and confirm the app updates itself | [ ] | [ ] |

Check 8 matters most. A broken updater means every installed copy stays on
that version forever, and the only fix is asking each user to reinstall.

Windows is where most bugs will show up: paths with spaces or backslashes,
onnxruntime DLLs (may need the VC++ runtime), and long paths.

---

## 8. How changes reach users

There are three delivery channels, and most fixes need only the first two:

| What changed | How it ships | Who gets it, how fast |
|---|---|---|
| api, agent server, embed worker, migrations | Run the deploy script on the VPS | Every user, immediately |
| **Dashboard UI** (most screens and bug fixes) | Same deploy. The app window loads `https://app.meelu.tech`, so the UI is never bundled into the app | Every user, on their next page load. **No app release needed** |
| Electron main/preload (crawler, agent harness, GSC/GA sync, local pipelines) | Bump `app/package.json` version → push an `app-v0.1.x` tag → CI builds, signs and uploads to R2 → installed apps find the new version, download it, and install on restart | Users within hours |

### App release, step by step

1. Fix the bug in `app/`.
2. Bump `version` in `app/package.json` (for example 0.1.3 → 0.1.4).
3. Commit, then `git tag app-v0.1.4 && git push --tags`.
4. CI builds on macOS and Windows, signs, notarizes and uploads to R2,
   including the new `latest.yml` and `latest-mac.yml`.
5. Each installed app checks those files at boot and every 6 hours. When the
   version is newer, it downloads in the background and asks the user to
   restart. If they ignore it, the update installs on the next quit.
6. The website's fixed-name links now serve the new version to new users.

### Rules that apply from launch onward

- **Server changes can't break older apps.** When you change an endpoint the
  app's main process calls, add the new version first and remove the old
  one in a later release. If you can't, raise `min_app_version`.
- **The dashboard can be newer than the installed app.** Before calling a new
  `window.meelu.*` method, check that it exists. An older preload won't have
  it.
- **Migrations add before they drop.** Back up before any destructive
  migration. No more `down -v` or squashing migrations against production.
- **Rollback:** on the server, `git revert` and redeploy. For the app,
  publish a new version with a higher number. The updater never goes
  backwards.

---

## 9. Order to do it in

1. Buy the accounts in section 1. Start Apple enrolment today, since it
   takes the longest.
2. Supabase setup + the server code changes → deploy to the VPS → the web
   app works at `app.meelu.tech`.
3. App packaging + updater + CI → build installers for your own Mac and a
   Windows machine.
4. Clean-machine test pass (section 7), including the 0.1.1 updater test.
5. Website download page → announce.
6. Update CLAUDE.md: "Nothing is in production" is no longer true.
7. Then fix bugs from Sentry, using the delivery channels in section 8.

## Open decisions

- **Intel Macs at launch?** Recommendation: ship Apple Silicon + Windows
  first. Intel needs a second Mac build because of the per-arch Agent SDK
  binary.
- **Payments at launch, or signup credits only** until Dodo live mode is
  approved?
