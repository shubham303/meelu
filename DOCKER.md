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
| Dashboard    | `meelu-dashboard:latest`         | long-running Next.js on port 3000, proxies /api   |

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
docker compose up -d --build
```

Open <http://localhost:3000>, sign up with any email and password, walk through
onboarding. The account is provisioned with a default workspace API key, and it
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

Prod and test run on a VPS under [Coolify](https://coolify.io), from
`deploy/compose.yml`. That file has no Postgres, no container names and no
published ports, so the two environments run side by side and Coolify's proxy
handles domains and HTTPS.

1. Create the VPS from Hostinger's Coolify template, or run Coolify's installer
   on Ubuntu. Give it at least 8 GB of RAM.
2. Add Cloudflare R2 as an S3 storage target
   (`https://<account-id>.r2.cloudflarestorage.com`).
3. Create one project with two environments, `production` and `test`.
4. In each environment, add a PostgreSQL database. Set its image to
   `paradedb/paradedb:0.25.2-pg17`, add
   `shared_preload_libraries = 'pg_search'` to its custom configuration, and
   schedule backups to R2.
5. In each environment, add an application from the GitHub repo with the
   Docker Compose build pack and compose path `/deploy/compose.yml`. Use branch
   `main` for production and `test` for test, and turn on auto-deploy.
6. Set the environment variables. `DATABASE_URL` is the database's internal
   URL with the scheme changed to `postgresql+psycopg://`. `CORS_ORIGINS` and
   `DODO_PAYMENTS_RETURN_URL` must use the environment's domain. Add the vendor
   keys.
7. Give `dashboard` a domain on port 3000 and `agent` a domain on port 8484.
   The Electron app connects to the agent domain.

After the first scheduled backup, restore it into the test database once, to
prove the backups work.

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
