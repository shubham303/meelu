# Running Meelu with Docker

One `docker compose up` brings up Postgres, the backend, the agent server,
the embedding worker and the dashboard.

| Piece        | Image                            | How it runs                                       |
| ------------ | -------------------------------- | ------------------------------------------------- |
| Postgres     | `paradedb/paradedb:0.25.2-pg17`  | long-running, data in the `pgdata` volume         |
| Migrator     | `meelu-migrate:latest`           | one-shot `alembic upgrade head` on every `up`     |
| API          | `meelu-api:latest`               | long-running FastAPI on port 8100 (loopback)      |
| Agent server | `meelu-agent:latest`             | long-running MCP over HTTP on port 8484 (loopback)|
| Embed worker | `meelu-embed-worker:latest`      | long-running, chunks and embeds pages             |
| Auth DB      | `paradedb/paradedb:0.25.2-pg17`  | one-shot: creates the `auth` database if missing  |
| Dashboard    | `meelu-dashboard:latest`         | long-running Next.js on port 3000, proxies /api, runs sign-in at /auth |

Startup order is enforced, not hoped for: Postgres has to report healthy, then
`migrate` has to exit 0, and only then do the api, the agent server, the
worker and the dashboard start. So the schema is never behind the code that queries it.

**Data lives in the `pgdata` volume and survives restarts, rebuilds and
`docker compose down`.** The one command that destroys it is `down -v`.

## Local

**Prerequisites:** Docker Desktop (or Docker Engine + Compose v2).

```bash
cp .env.example .env
# set POSTGRES_PASSWORD — e.g. openssl rand -base64 24
# set APP_DB_PASSWORD — a different one, for the meelu_app role
# set BETTER_AUTH_SECRET — e.g. openssl rand -base64 32
docker compose up -d --build
```

Sign-in is Better Auth, inside the dashboard. Its accounts live in a separate
`auth` database in the same Postgres; the `auth-db` one-shot creates it on every
`up` if it is missing, and the dashboard creates its tables when it starts. To
create it by hand instead (for `npm run dev` against the compose Postgres):

```bash
psql postgres://craftmate:$POSTGRES_PASSWORD@localhost:5434/craftmate -c 'CREATE DATABASE auth'
```

and run the dashboard with `AUTH_DATABASE_URL=postgres://craftmate:$POSTGRES_PASSWORD@localhost:5434/auth`,
`BETTER_AUTH_SECRET=<anything long>` and `BETTER_AUTH_URL=http://localhost:3000`. The api needs
`AUTH_JWKS_URL=http://localhost:3000/auth/jwks` and `AUTH_ISSUER` / `AUTH_AUDIENCE` set to the same
origin. Without `RESEND_API_KEY`, `npm run dev` prints each email code to its console.

The copied `.env` sets `SESSION_COOKIE_SECURE=false`. The api marks the session
cookie Secure by default, and the local dashboard is plain `http://localhost`,
so without it the browser drops the cookie and sign-in does not stick. Keep it
`true` (the default) anywhere that serves HTTPS. The api's `/docs` and
`/openapi.json` are off unless `API_DOCS_ENABLED=true`.

Open <http://localhost:3000>, sign up with an email and a password of at least
12 characters, enter the emailed code, walk through onboarding. The account is provisioned with a default workspace API key, and it
is still there after a restart — sign up once.

The backend's integration tests live in `api/tests`:

```bash
cd api && uv run pytest
```

### Connect the agent server

The agent server is the `agent` compose service — the api image started with
`src.agent.app` — so `docker compose up` brings it up alongside the api. To run
it from source instead:

```bash
cd api && uv run uvicorn src.agent.app:app --port 8484
```

It serves MCP over streamable HTTP at `http://127.0.0.1:8484/mcp/`;
authenticate with a workspace API key from **Dashboard → Settings** in the
`x-api-key` header (plus `x-meelu-site` to pin a website).

## Production and test (Coolify)

Meelu is used only through the desktop app. The servers run on one Hostinger
VPS (Ubuntu 24.04) under Coolify, from
`deploy/compose.yml`, behind Cloudflare.

| What | Production | Test |
|---|---|---|
| Git branch (auto-deploys on push) | `main` | `test` |
| UI the app loads | `https://ui.meelu.tech` | `https://test-ui.meelu.tech` |
| Agent server (MCP) | `https://agent.meelu.tech/mcp/` | `https://test-agent.meelu.tech/mcp/` |
| Sign-in (Better Auth, inside the UI) | `https://ui.meelu.tech/auth` | `https://test-ui.meelu.tech/auth` |
| Database | Coolify Postgres `meelu-db-production` | `meelu-db-test` |
| Backups to R2 `meelu-db-backups` | every 6 h, kept 30 days | daily, kept 7 days |

The api has no public domain; the UI proxies `/api/*` to it inside the Docker
network. A browser that opens the UI host is sent to `meelu.tech/download`.

**Services in `deploy/compose.yml`:** `migrate` (one-shot Alembic), `api`,
`agent`, `embed-worker` and `dashboard`. Sign-in is Better Auth, running inside
the dashboard at `/auth/*`: email + password, a 6-digit emailed code to confirm
the address and to reset a password, and at most 10 accounts (`SIGNUP_CAP` in
`dashboard/src/lib/auth-server.ts`). Each environment's Postgres holds two
databases: `meelu` for the app and `auth` for Better Auth, owned by its own
`auth_app` role, which has no privileges on any table in `meelu`. The dashboard creates Better
Auth's tables in `auth` when it starts. After sign-in it trades a 5-minute
Better Auth JWT for the api's `meelu_session` cookie; the api verifies the JWT
against `http://dashboard:3000/auth/jwks` inside the Docker network. Codes go
out through Resend from `noreply@meelu.tech`.

**Environment variables** live on each Coolify application. Nothing is
build-time; every secret is runtime-only. Required:
`DATABASE_URL` (the non-superuser `meelu_app` role:
`postgresql+psycopg://meelu_app:...@<db-host>:5432/meelu`), `MIGRATE_DATABASE_URL`
(the Postgres superuser; only the `migrate` service gets it, runs Alembic, then
creates `meelu_app` with that password and hands it every table), `CORS_ORIGINS`, `APP_ORIGINS`, `DODO_PAYMENTS_BASE_URL`,
`DODO_PAYMENTS_RETURN_URL`, `AUTH_DATABASE_URL`
(`postgres://auth_app:...@<db-host>:5432/auth`), `BETTER_AUTH_SECRET`,
`BETTER_AUTH_URL` (`https://ui.meelu.tech` or `https://test-ui.meelu.tech`),
`RESEND_API_KEY`, `AGENT_ALLOWED_HOSTS`, plus the vendor keys.
`CREDITS_SIGNUP_GRANT_USD` defaults to 1.

**Security layers:**
- Cloudflare proxies every web host (SSL Full strict, HSTS, managed WAF, a
  rate limit on sign-in endpoints, a rule that only lets `coolify.meelu.tech`
  answer from India except `/webhooks/`).
- The Hostinger firewall accepts 80/443 only from Cloudflare's IP ranges and
  22 from anywhere (SSH is key-only). Nothing reaches the server around
  Cloudflare.
- Traefik redirects http to https permanently at the entrypoint
  (`/data/coolify/proxy/docker-compose.yml`); re-add those three
  `redirections` lines if the proxy configuration is ever reset.
- Coolify is at `https://coolify.meelu.tech` and emails alerts (failed deploys
  and backups, disk, unreachable server) through Resend.

**Desktop app releases:** run the `App build` workflow (Actions → App build →
flavour `prod` or `test`) or push a tag `app-v*`. It builds the macOS arm64 and
x64 dmgs and the Windows installer, and uploads them with `SHA256SUMS.txt` to
the R2 bucket `meelu-downloads`, served at `https://downloads.meelu.tech`
(test builds under `/test/`). The installers are unsigned until the Apple and
Microsoft certificates arrive.

**Restoring a backup:** download the `pg-dump-all-*.gz` from R2 (or
`/data/coolify/backups/databases/...` on the server), start a scratch
`paradedb/paradedb:0.25.2-pg17` container with `POSTGRES_USER=meelu`, wait for
it to finish initialising, and pipe the dump into `psql -U meelu`. Restore into
a scratch container first and check it before touching a live database.

## Operating it

```bash
docker compose logs -f api dashboard  # follow logs
docker compose logs migrate           # what the last migration run did
docker compose ps                     # status + health
docker compose restart dashboard      # restart; data is untouched
docker compose up -d --build          # rebuild after a code change
docker compose down                   # stop and remove — keeps the data
docker compose down -v                # ...and destroy the database
```

Health: the container reports `healthy` once the landing page returns 200.
`docker compose ps` shows it; an unhealthy container is a real failure, not a
slow start (the check allows 20s of warm-up).

### Database

Tables are declared in `api/src/models` and migrations are Alembic revisions
under `api/alembic/versions`. After changing a model:

```bash
cd api && uv run alembic revision --autogenerate -m "what changed"
docker compose up -d --build           # migrate service applies it on boot
```

A psql prompt, without publishing the port:

```bash
docker compose exec postgres psql -U craftmate craftmate
```

For a GUI client, the port is already published on loopback — `POSTGRES_PORT`,
5434 by default, since 5432 and 5433 are usually taken by a Postgres installed
on the host:

```bash
psql postgres://craftmate:$POSTGRES_PASSWORD@localhost:5434/craftmate
```

#### Why the database is still called `craftmate`

The product is Meelu everywhere except three Postgres identifiers: the compose
project name, the role, and the database. They kept the old name on purpose,
because each one addresses data that already exists:

- `name: craftmate` in `docker-compose.yml` namespaces the volume. Rename it and
  compose creates an empty `meelu_pgdata`; the app comes up looking wiped.
- `POSTGRES_USER` / `POSTGRES_DB` only take effect on **first** boot of an empty
  volume. Rename them against an existing one and the app connects as a role the
  cluster has never heard of.

Nobody sees these but you. If you want them renamed anyway, back up first and
then migrate rather than edit:

```bash
docker compose exec -T postgres pg_dump -U craftmate craftmate > pre-rename.sql
docker compose down

# copy the volume under the new project name (the original is left intact)
docker volume create meelu_pgdata
docker run --rm -v craftmate_pgdata:/from -v meelu_pgdata:/to alpine \
  sh -c 'cd /from && cp -a . /to'

# then flip name/POSTGRES_USER/POSTGRES_DB to meelu in docker-compose.yml,
# bring Postgres up alone, and rename the role and database inside it:
docker compose up -d postgres
docker compose exec postgres psql -U craftmate -d postgres \
  -c 'ALTER DATABASE craftmate RENAME TO meelu' \
  -c 'ALTER ROLE craftmate RENAME TO meelu'
docker compose up -d
```

`ALTER ROLE … RENAME` preserves a SCRAM-SHA-256 password (the default since
Postgres 14), but it clears an MD5 one — check `\password` still works before
deleting `craftmate_pgdata`.

### Backups

Production backups are Coolify's scheduled backups to R2. Locally, take a dump
before anything destructive:

```bash
docker compose exec -T postgres pg_dump -U craftmate craftmate > backup.sql
cat backup.sql | docker compose exec -T postgres psql -U craftmate craftmate
```

Restore into an empty database — `pg_dump` output is not idempotent against a
schema that already has rows.

## Troubleshooting

**Port 3000 already in use.** Set `DASHBOARD_PORT=3001` in `.env`.

**Nothing starts / `migrate` exited non-zero.** The api, the worker and the
dashboard are gated on the migration succeeding, so they stay down by design. `docker compose logs
migrate` has the SQL error. The migrator retries for ~20s while Postgres comes
up, so a timeout there means Postgres itself is unhealthy — check
`docker compose logs postgres`.

**"password authentication failed".** `POSTGRES_PASSWORD` in `.env` no longer
matches the one baked into the volume when it was created. Either restore the
old value or `docker compose down -v` and start fresh, losing the data.

## What's in the images

The dashboard uses Next.js `output: "standalone"`, so the runtime layer carries
`server.js`, the traced subset of `node_modules`, `.next/static` and `public` —
no source, no build tools, no dev dependencies. It runs as an unprivileged user.
The api, migrator and embed worker are three targets of one `api/Dockerfile`
sharing a uv-installed base layer. No image contains a `.env` file; all
configuration arrives at runtime.
