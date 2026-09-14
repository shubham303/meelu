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
| Caddy (VPS)  | `caddy:2-alpine`                 | optional overlay, terminates HTTPS                |

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

## VPS

Copy the repo to the host — `api/`, `dashboard/`,
`docker-compose.yml`, `docker-compose.prod.yml`, `Caddyfile`, `.env.example`.

Point an A record at the host, open ports 80 and 443, then:

```bash
cp .env.example .env
```

```dotenv
POSTGRES_PASSWORD=<openssl rand -base64 24>
MEELU_DOMAIN=meelu.example.com
```

`POSTGRES_PASSWORD` is read only when the volume is first created. Changing it
later does not change the existing database — reset with `down -v`, which also
deletes the data.

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Caddy requests and renews the Let's Encrypt certificate on its own and proxies
to the dashboard over the internal network. The dashboard's own port stays
bound to `127.0.0.1`, so nothing but Caddy can reach it from outside.

### Skipping HTTPS

For a quick internal test, leave off `-f docker-compose.prod.yml` and set
`DASHBOARD_BIND=0.0.0.0` in `.env` to publish port 3000 directly. Only do that
behind a firewall or VPN — sessions and API keys would cross the network in
plaintext.

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

The volume is the product now. Take a dump before anything destructive, and on
a schedule once there are real users:

```bash
docker compose exec -T postgres pg_dump -U craftmate craftmate > backup.sql
cat backup.sql | docker compose exec -T postgres psql -U craftmate craftmate
```

Restore into an empty database — `pg_dump` output is not idempotent against a
schema that already has rows.

## Troubleshooting

**Port 3000 already in use.** Set `DASHBOARD_PORT=3001` in `.env`.

**Caddy won't get a certificate.** DNS must already resolve to the host and
ports 80/443 must be free — `docker compose logs caddy` names the reason.

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
