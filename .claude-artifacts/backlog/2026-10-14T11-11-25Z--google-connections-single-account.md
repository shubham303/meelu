# Search Console and GA4 hold one Google account per machine, so agencies lose access to earlier clients

- **Recorded:** 2026-10-14
- **Severity:** bug
- **Area:** app, schema, dashboard
- **Files:** `app/src/main/connector-config.js:5`, `app/src/main/index.js:507`, `app/src/main/integrations/gsc/client.js:18`, `app/src/main/integrations/ga/client.js:17`, `app/src/main/integrations/gsc/sync.js`, `app/src/main/integrations/ga/sync.js`, `api/src/sites/models/site.py`, `api/src/sites/schemas.py`, `dashboard/src/app/dashboard/connections/page.tsx`

## Issue

The app stores exactly one Search Console refresh token and one GA4 refresh
token per machine. Each website stores only its property (`gsc_property`,
`ga_property` on the site row), not which Google account can read it.

An agency whose clients sit on different Google accounts (a client-created
login like `marketing@client.com`, account managers each using their own
account, a freelancer with a personal Gmail plus a client account) connects
account A for client 1, then account B for client 2. The second connect
overwrites the first token, and client 1's syncs, index checks and URL
inspections then fail ("No Search Console property matches …" or 403s), with
nothing telling the user why.

The common agency setup (one agency Google account that the clients add as a
user) works today and must keep working.

## Evidence

- `app/src/main/connector-config.js:5-8`: `CONNECTOR_FIELDS = { gsc: { refreshToken: "secret" }, ga4: { refreshToken: "secret" } }`, so there is one slot each.
- `app/src/main/index.js:507-528`: `connectors:connectGsc` / `connectors:connectGa4` call `saveConnector("gsc" | "ga4", { refreshToken })`, which replaces the record.
- `gsc/client.js` and `ga/client.js`: `accessToken()` reads `connectorValues("gsc"|"ga4")` with a single module-level `cached` token and `deadRefreshToken`.
- `gsc/sync.js` `drive()`: property auto-match runs over `listProperties()` from that one account only.

## Suggested fix

1. **Connections keyed by Google account.** On connect, also request the
   `openid email` scopes (or call the userinfo endpoint) to learn the account
   email. Store a list of connections per product:
   `{ gsc: { "<email>": { refreshToken } }, ga4: { "<email>": { refreshToken } } }`.
   Connecting the same email again replaces only that entry. Add disconnect per
   email.
2. **Clients take an account.** `accessToken(email)`, with the access-token
   cache and the dead-token marker keyed by email. `listProperties()` across
   all connections returns each property tagged with its email.
3. **Site stores the account.** Add `gsc_account` and `ga_account` (Google
   email) next to `gsc_property` / `ga_property` in
   `api/src/sites/models/site.py`, with schemas and the property-setting
   endpoints updated. Sync, index check and inspect read the site's account and
   use that token.
4. **Picker.** The auto-match in `gsc/sync.js` searches every connection. If
   exactly one property on one account matches, save both. If several match
   (same property on two accounts, or several property variants), return
   `needsProperty` with candidates grouped by email, as today.
5. **Connections page.** Show each connected Google email under Search Console
   and GA4, an "Add another Google account" button, and remove per account.

Unsure: whether to merge GSC and GA4 into one Google connection with both
scopes. That's simpler for users, but users who only want one product would
have to grant both, and the OAuth clients are separate today
(`GSC_OAUTH_CLIENT`, `GA_OAUTH_CLIENT`). Decide with the user.

## Risks / knock-on effects

- Schema change on `site`: needs an Alembic revision (or a squash into the baseline). Do not reset the local DB without asking.
- The existing `connectors.json` shape changes. Nothing is in production, so change it outright and do not read the old shape. Users reconnect once.
- The dashboard types in `dashboard/src/lib/types.ts` and the traffic sync UI in `dashboard/src/app/dashboard/seo/traffic/sync.ts` read the site's property fields.
- `api/src/agent_plans/library.py:245` and `api/src/agent_scope/guides.py:95` mention `gsc_property` / `ga_property`. Update them if columns are added or renamed.
- The app runs on the user's machine, so connections still do not follow the user to a second device. That is out of scope here.
- Google OAuth verification: adding `email` / `openid` scopes is non-sensitive, but check that it does not reopen the pending OAuth review.

## Verification

- `cd api && uv run alembic upgrade head && uv run pytest tests -k site`
- `cd dashboard && npx tsc --noEmit`
- Manual, in the app: connect Google account A, then account B. Both appear on Connections. A site whose property is on A and a site whose property is on B both run a search-data sync and a traffic sync successfully. Removing B only breaks B's site, with a clear "reconnect" message.
