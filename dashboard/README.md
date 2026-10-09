# Meelu Dashboard

The web frontend for **Meelu — an AI marketing assistant for your website**.
It is a Next.js app and nothing else: every `/api/auth/*` and `/api/v1/*`
path it serves is a rewrite to the Python backend in `../api`, and it holds
no database credentials and no vendor keys. The intelligence lives in the
agent server (`../api/src/agent`), a streamable-HTTP MCP service that the Meelu
app's harness — or any MCP client — connects to with a workspace API key;
this UI is where its output lands and gets reviewed, edited and sent.

- REST contract (what the UI calls): [`API.md`](./API.md)
- The backend that serves it: `../api`
- The agent server: `../api/src/agent`, served by the `agent` compose service
- Design system & frontend conventions: [`DESIGN.md`](./DESIGN.md)
- Docker: [`../DOCKER.md`](../DOCKER.md)

## Stack

- **Next.js 16** (App Router, TypeScript, Turbopack) + **Tailwind v4**
- **GSAP** (`@gsap/react`) for all motion
- **Auth** is a `meelu_session` cookie issued by the backend; the frontend
  only forwards it (`src/lib/server-session.ts`, `src/lib/session.ts`).

## Run locally

Start the backend first (`../api`, or `docker compose up -d` from the repo
root, which publishes it on `localhost:8100`), then:

```bash
npm install
export MEELU_API_URL=http://localhost:8100   # the default; set it if yours differs
npm run dev
# open http://localhost:3000
```

Sign up with any email/password (nothing is sent anywhere), walk through
onboarding, and you land on a populated dashboard.

## Run in Docker

From the repo root, `docker compose up -d --build` brings up Postgres, runs
the Alembic migrations, starts the backend and serves a production build of
this app on port 3000. See [`../DOCKER.md`](../DOCKER.md). Use `npm run dev`
for day-to-day development — Docker is for deployment.

## Auth model

Every `/api/v1/*` endpoint behind the rewrite accepts either:

1. the browser **session cookie**, or
2. an **`x-api-key`** header — a workspace API key, managed in
   Settings → Connect your coworker. The same keys authenticate against the
   agent server (`../api/src/agent`).

```bash
curl -H "x-api-key: emcp_..." http://localhost:3000/api/v1/site
```

## Layout

```
src/lib/        session forwarding, API hooks, app-mode detection, shared types and helpers
src/features/   prompt chips
src/components/ ui kit, GSAP primitives, charts, sidebar, logo
src/app/        landing, login/signup, onboarding, dashboard/*
src/proxy.ts    redirects the desktop app's user agent straight to /dashboard
next.config.ts  the /api rewrites to MEELU_API_URL and the CSP
```
