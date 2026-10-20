# Database access

CloudBeaver Community Edition (`dbeaver/cloudbeaver:26.2.2`, free and
self-hosted) gives browser access to the prod and test Postgres: a spreadsheet
style data editor and a SQL editor. It runs as the `cloudbeaver` service in the
**Monitoring** project in Coolify and reaches both databases over the internal
`coolify` Docker network. Neither database has a public port.

URL: https://db.meelu.tech

## How access is protected

A request passes four layers before it reaches any data:

1. **Cloudflare WAF.** The rule "Database viewer only from India; ACME challenge
   allowed" blocks `db.meelu.tech` outside India. Only Let's Encrypt's
   `/.well-known/acme-challenge/` path is open, so the origin certificate can
   renew. The Hostinger firewall only lets Cloudflare reach the VPS, so nothing
   skips this rule.
2. **Basic auth.** A Traefik middleware asks for a user name and password before
   the page loads. The browser shows its own sign-in box.
3. **CloudBeaver login.** One local admin account. Anonymous access is off,
   users cannot add their own connections, and Community Edition has no sign-up
   page, so nobody can register.
4. **Postgres roles.** CloudBeaver connects as `viewer_ro` or `editor_rw`, never
   as the superuser.

Travelling outside India blocks you too. To allow it for a while, disable the
WAF rule in the Cloudflare dashboard (meelu.tech → Security → WAF → Custom
rules), and enable it again when you are back.

## Which connection to use

The four connections appear in the navigator after you sign in, in the
**Production** and **Test** folders.

| Connection | Role | Use it for |
|---|---|---|
| Prod — Read only | `viewer_ro` | Everyday browsing and SQL on prod. Start here. |
| Prod — Edit | `editor_rw` | Fixing rows on prod by hand. Only when you mean to change data. |
| Test — Read only | `viewer_ro` | Browsing the test database. |
| Test — Edit | `editor_rw` | Practising an edit before you do it on prod. |

What each role can do, in the `meelu` database on both servers:

- `viewer_ro` reads every table in `public`, including tables that later
  migrations add. Every session is read-only. It cannot write, create, drop or
  truncate.
- `editor_rw` reads, inserts, updates and deletes rows in every `public` table,
  including future ones. It cannot create, alter, drop or truncate tables, and
  it cannot write `alembic_version`.
- Both roles have `BYPASSRLS`. The app tables have row-level security for the
  agent, and without it these roles would see no rows.
- Neither role can connect to the `auth` database (Better Auth users, password
  hashes and sessions), and neither can see the agent's `ws_*` workspace
  schemas.
- Queries stop after 2 minutes. An `editor_rw` transaction left open and idle
  ends after 10 minutes, so a forgotten edit does not hold locks.
- Each role allows 10 connections at most.

## Backups

Coolify backs up both databases to the R2 bucket `meelu-db-backups` and keeps
local copies on the VPS:

| Database | Schedule | Local copies |
|---|---|---|
| `meelu-db-production` | Every 6 hours (`0 */6 * * *`) | 8 |
| `meelu-db-test` | Daily at 03:00 (`0 3 * * *`) | 3 |

A failed backup sends an email (see `MONITORING.md`). Before a bulk edit on
prod, take a manual backup: Coolify → `meelu-db-production` → Backups →
**Backup Now**.

## Where the credentials are

All values are in `~/.config/meelu-deploy/secrets.env`. The names are:

| Secret | What it is |
|---|---|
| `CLOUDBEAVER_BASIC_AUTH_USER`, `CLOUDBEAVER_BASIC_AUTH_PASSWORD` | Browser sign-in box (layer 2) |
| `CLOUDBEAVER_ADMIN_NAME`, `CLOUDBEAVER_ADMIN_PASSWORD` | CloudBeaver login (layer 3) |
| `PRODUCTION_VIEWER_RO_PASSWORD`, `PRODUCTION_EDITOR_RW_PASSWORD` | Prod role passwords |
| `TEST_VIEWER_RO_PASSWORD`, `TEST_EDITOR_RW_PASSWORD` | Test role passwords |
| `CLOUDBEAVER_UUID` | The Coolify service UUID |

Coolify keeps copies in the service's environment variables: `CB_ADMIN_NAME`,
`CB_ADMIN_PASSWORD`, `PROD_VIEWER_RO_PASSWORD`, `PROD_EDITOR_RW_PASSWORD`,
`TEST_VIEWER_RO_PASSWORD` and `TEST_EDITOR_RW_PASSWORD`. The basic auth label in
the compose file holds only a bcrypt hash.

The connections do not store passwords. Each one holds a reference such as
`${PROD_VIEWER_RO_PASSWORD}`, and CloudBeaver reads the value from its
environment when it connects (`CLOUDBEAVER_SYSTEM_VARIABLES_RESOLVING_ENABLED`).

## Changing the setup

- **Rotate a role password.** Run `ALTER ROLE viewer_ro PASSWORD '...'` as
  `meelu` on that database. Then update `secrets.env` and the matching Coolify
  environment variable, and restart the service.
- **Rotate the basic auth password.** Generate a new hash with
  `htpasswd -niB -C 10 <user>` and replace it in the
  `traefik.http.middlewares.cloudbeaver-auth.basicauth.users` label. Write
  single `$` signs: Coolify escapes them itself.
- **Change the admin password** in CloudBeaver (Settings → Users), then update
  `secrets.env`. `CB_ADMIN_PASSWORD` is only read the first time the server
  starts.
- **The connection list** lives in the workspace volume
  (`cloudbeaver-workspace`, mounted at `/opt/cloudbeaver/workspace`). It was
  seeded once from `conf/initial-data-sources.conf`, which Coolify writes from
  the compose file. Change connections in the CloudBeaver admin UI. Coolify does
  not update that file when the compose changes. A new seed only takes effect
  if you delete and re-create the service.
- **Restoring a database onto a new server.** A database backup does not carry
  roles. Create the two roles again, as `meelu`, with the SQL below.

```sql
CREATE ROLE viewer_ro;
CREATE ROLE editor_rw;
ALTER ROLE viewer_ro WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION BYPASSRLS CONNECTION LIMIT 10 PASSWORD '...';
ALTER ROLE editor_rw WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION BYPASSRLS CONNECTION LIMIT 10 PASSWORD '...';
ALTER ROLE viewer_ro SET default_transaction_read_only = on;
ALTER ROLE viewer_ro SET statement_timeout = '2min';
ALTER ROLE editor_rw SET statement_timeout = '2min';
ALTER ROLE editor_rw SET idle_in_transaction_session_timeout = '10min';
GRANT CONNECT ON DATABASE meelu TO viewer_ro, editor_rw;
GRANT USAGE ON SCHEMA public TO viewer_ro, editor_rw;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO viewer_ro;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO viewer_ro;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO editor_rw;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO editor_rw;
REVOKE INSERT, UPDATE, DELETE ON public.alembic_version FROM editor_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE meelu IN SCHEMA public GRANT SELECT ON TABLES TO viewer_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE meelu IN SCHEMA public GRANT SELECT ON SEQUENCES TO viewer_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE meelu IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO editor_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE meelu IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO editor_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE meelu_app IN SCHEMA public GRANT SELECT ON TABLES TO viewer_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE meelu_app IN SCHEMA public GRANT SELECT ON SEQUENCES TO viewer_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE meelu_app IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO editor_rw;
ALTER DEFAULT PRIVILEGES FOR ROLE meelu_app IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO editor_rw;
```

Migrations create tables as `meelu`, and each deploy hands them to `meelu_app`.
That is why the default privileges are set for both roles. Grants stay on a
table when its owner changes.

## Monitoring

Uptime Kuma checks `http://cloudbeaver-<uuid>:8978/status` every 60 seconds
over the `coolify` network (monitor "CloudBeaver (internal)"). The public URL
cannot be used, because the VPS is outside India and the WAF rule blocks it.
