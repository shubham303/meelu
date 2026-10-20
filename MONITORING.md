# Monitoring

Four tools watch the VPS (`srv2048855`, 31.220.20.109). They run as services in the
**Monitoring** project in Coolify, behind Cloudflare. Every alert is sent through
Resend as `VPS Alerts <alerts@meelu.tech>` to `randiveshubham3+vps-alert@gmail.com`.

| Tool | URL | What it is for |
|---|---|---|
| Dozzle | https://logs.meelu.tech | Live logs of every container on the VPS, with search and regex. MCP endpoint for Claude Code. |
| Bugsink | https://errors.meelu.tech | API exceptions with stack traces and request context, grouped into issues. Emails on new, regressed and unmuted issues. |
| Uptime Kuma | https://uptime.meelu.tech | HTTP checks of the public endpoints every 60 s. Emails on down and up. |
| Beszel | https://metrics.meelu.tech | CPU, memory, disk, network and per-container usage with history. Emails on thresholds and on the agent going silent. |
| Coolify notifications | https://coolify.meelu.tech → Notifications → Email | Failed deploys and backups, stopped or restarted containers, unreachable server, high disk, failed cleanup or scheduled tasks. |

Logins: the user is `admin` for Dozzle and Uptime Kuma, and
`randiveshubham3+vps-alert@gmail.com` for Bugsink and Beszel. The passwords are in
`~/.config/meelu-deploy/secrets.env` (`MONITORING_*_PASSWORD`), with the Coolify
service UUIDs (`MONITORING_*_UUID`) and the Bugsink DSNs
(`MONITORING_BUGSINK_DSN_API`, `MONITORING_BUGSINK_DSN_AGENT`).

## Alert matrix

Only Uptime Kuma lets you set the subject, so only its emails carry the
`[VPS-ALERT][uptime-kuma]` prefix. The others use fixed subjects in their code.
Filter on the recipient address, not on the subject.

| Event | Tool | Email subject |
|---|---|---|
| Public endpoint fails twice in a row (about 2 min) | Uptime Kuma | `[VPS-ALERT][uptime-kuma] <monitor> 🔴 Down` |
| Endpoint back up | Uptime Kuma | `[VPS-ALERT][uptime-kuma] <monitor> ✅ Up` |
| New exception type in the api or agent server | Bugsink | `"<exception>" in "<project>" (New issue)` |
| Resolved issue happens again | Bugsink | `"<exception>" in "<project>" (Regression)` |
| Muted issue crosses its unmute condition | Bugsink | `"<exception>" in "<project>" (Unmuted issue)` |
| CPU above 85% averaged over 5 min | Beszel | `meelu-vps CPU above threshold` |
| Memory above 85% averaged over 10 min | Beszel | `meelu-vps memory above threshold` |
| Disk above 80% averaged over 10 min | Beszel | `meelu-vps disk usage above threshold` |
| Any of the above recovers | Beszel | `meelu-vps <metric> below threshold` |
| Agent silent for 5 min | Beszel | `Connection to meelu-vps is down 🔴` |
| Agent back | Beszel | `Connection to meelu-vps is up ✅` |
| Deploy failed | Coolify | `Coolify: Deployment failed of <app>.` |
| Container stopped | Coolify | `Coolify: <resource> has been stopped` |
| Container restarted automatically | Coolify | `Coolify: A resource (<name>) has been restarted automatically on <server>` |
| Database backup failed | Coolify | `Coolify: [ACTION REQUIRED] Database Backup FAILED for <db>` |
| High disk usage | Coolify | `Coolify: Server (<server>) high disk usage detected!` |
| Docker cleanup failed | Coolify | `Coolify: [ACTION REQUIRED] Docker cleanup job failed on <server>` |
| Scheduled task failed | Coolify | `Coolify: [ACTION REQUIRED] Scheduled task (<task>) failed.` |
| Container hit its restart limit | Coolify | `Coolify: <resource> stopped - restart limit reached (<n>/<max>)` |

Dozzle does not send email.

## Email budget

Resend's free plan allows 3,000 emails a month and 100 a day, and the product's
sign-in codes use the same quota. Only emails you can act on are switched on:

- Coolify sends failures only. Success emails, server patches, Traefik
  outdated, and server unreachable or revived are off. Coolify runs on this VPS,
  so it could only report losing its own SSH connection.
- Uptime Kuma marks a monitor down after 2 failed retries, never repeats the
  email while it stays down (resend interval 0), and has TLS-expiry emails off.
  Cloudflare renews those certificates.
- Beszel averages memory and disk over 10 minutes, so a value sitting near the
  line does not flap. Beszel always sends a recovery email when an alert clears,
  and there is no setting to stop it, so each Beszel alert costs two emails.
- Bugsink emails once per new issue, regression or unmute, never per event.

To see what was sent, list the emails in the Resend dashboard and look for the
sender `alerts@meelu.tech`.

### Uptime Kuma monitors

| Monitor | URL | Up when |
|---|---|---|
| Prod UI | https://ui.meelu.tech/auth/jwks | 2xx |
| Prod API (via UI) | https://ui.meelu.tech/api/v1/credits | 401 (the api answered through the dashboard rewrite) |
| Prod agent server | https://agent.meelu.tech/health | 2xx |
| Test UI | https://test-ui.meelu.tech/auth/jwks | 2xx |
| Test API (via UI) | https://test-ui.meelu.tech/api/v1/credits | 401 |
| Test agent server | https://test-agent.meelu.tech/health | 2xx |
| Website | https://meelu.tech | 2xx |
| Downloads | https://downloads.meelu.tech/version.json | 2xx |
| Coolify (internal) | http://coolify:8080/api/health | 2xx |
| CloudBeaver (internal) | http://cloudbeaver-7tzyzcvh9jutufzfutoozp53:8978/status | 2xx |

Coolify and CloudBeaver are checked over the internal `coolify` Docker network.
The Cloudflare WAF rules only allow their dashboards from India, and the VPS is
outside India.

The CloudBeaver database viewer at https://db.meelu.tech also runs in the
Monitoring project. Its access, connections and credentials are in
`DATABASE.md`.

## Gmail filter

Search: `to:(randiveshubham3+vps-alert@gmail.com)`

Then **Create filter** → Apply the label `VPS Alerts`, Never send it to Spam, and
optionally Skip the Inbox. The `+vps-alert` address is the one thing every tool
has in common. Gmail ignores brackets in subject searches, so `[VPS-ALERT]`
would not match reliably anyway.

## Dozzle MCP for Claude Code

```bash
claude mcp add --transport http dozzle https://logs.meelu.tech/api/mcp
```

Then run `/mcp` in Claude Code and authenticate. A browser tab opens. Sign in as
`admin` and choose **Allow**. Access tokens last an hour and refresh on their own.
After 30 days you approve the client again. The tools are `list_containers`,
`list_hosts`, `get_container_logs`, `search_container_logs` and
`get_container_stats`, and they cover every container on the VPS.

## Bugsink SDK setup (not applied yet)

Bugsink speaks the Sentry protocol. Projects `api` and `agent` already exist in
team `Meelu`. To send errors from the backend:

1. `cd api && uv add "sentry-sdk[fastapi]"`
2. Add to `api/src/settings.py`:

   ```python
   sentry_dsn: str = ""
   sentry_environment: str = "local"
   ```

3. Initialise once in `src/app.py` and once in `src/agent/app.py`, before the
   FastAPI app is created:

   ```python
   import sentry_sdk

   if settings.sentry_dsn:
       sentry_sdk.init(
           dsn=settings.sentry_dsn,
           environment=settings.sentry_environment,
           send_default_pii=False,
           traces_sample_rate=0,
       )
   ```

   The FastAPI integration turns on by itself. It reports every unhandled
   exception with the request path, method and headers. `send_default_pii=False`
   keeps cookies, auth headers and request bodies out.
4. Pass `SENTRY_DSN` and `SENTRY_ENVIRONMENT` through `deploy/compose.yml` for the
   api, agent and embed-worker services.
5. In Coolify, set `SENTRY_DSN` per app: the api and embed worker use
   `MONITORING_BUGSINK_DSN_API` and the agent server uses
   `MONITORING_BUGSINK_DSN_AGENT`. Set `SENTRY_ENVIRONMENT` to `production` or
   `test`. Bugsink keeps the environment on each event, so prod and test share a
   project.

Bugsink only receives exceptions. A failure the code catches and logs with
`log.error(...)` does not reach Bugsink unless it also calls
`sentry_sdk.capture_exception(exc)`.

## Not covered

All four tools run on the VPS they watch. If the whole VPS goes down, nothing is
left to send the email. An outside check (for example a healthchecks.io dead-man
switch) would cover that. It was left out on purpose.

## Changing the setup

- Each service is a Coolify compose service. Change it in Coolify, or with the API
  using the UUIDs in `secrets.env`.
- Uptime Kuma is configured through its UI. The SMTP notification is the default
  for new monitors, so a new monitor emails without extra steps.
- Beszel alerts live under the bell icon on the system row. Email settings are in
  PocketBase at https://metrics.meelu.tech/_/ → Settings → Mail settings. The
  superuser login is the same as the Beszel login.
- The Resend key in Bugsink, Uptime Kuma and Beszel is a copy. If you rotate it,
  update it in all three: Bugsink's `EMAIL_HOST_PASSWORD` env in Coolify, the Kuma
  notification and the PocketBase mail settings. Coolify's own notifications keep
  the key that was set before this setup.
