import { GA_OAUTH_CLIENT } from "../../config.js";
import { connectorValues } from "../../connector-config.js";
import { apiFetch } from "../../net.js";

const TOKEN_URL = "https://oauth2.googleapis.com/token";
const ADMIN = "https://analyticsadmin.googleapis.com/v1alpha";
const DATA = "https://analyticsdata.googleapis.com/v1beta";

const ROW_LIMIT = 10_000;
const REFRESH_MARGIN_MS = 10 * 60_000;
const MAX_ATTEMPTS = 5;
const BACKOFF_CAP_MS = 64_000;

let cached = null;
let deadRefreshToken = null;

export function gaConnected() {
  const values = connectorValues("ga4");
  return !!values?.refreshToken;
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function backoffMs(attempt) {
  return Math.random() * Math.min(BACKOFF_CAP_MS, 1000 * 2 ** attempt);
}

async function accessToken() {
  const values = connectorValues("ga4");
  if (!values?.refreshToken) {
    throw new Error("Google Analytics is not connected on this machine.");
  }
  if (values.refreshToken === deadRefreshToken) {
    throw new Error(
      "Google no longer accepts this Analytics connection. Reconnect it from Settings.",
    );
  }
  if (cached && cached.expiresAt - REFRESH_MARGIN_MS > Date.now()) return cached.token;

  const res = await apiFetch(TOKEN_URL, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: GA_OAUTH_CLIENT.clientId,
      client_secret: GA_OAUTH_CLIENT.clientSecret,
      refresh_token: values.refreshToken,
      grant_type: "refresh_token",
    }).toString(),
  });
  const payload = await res.json().catch(() => ({}));
  if (!res.ok || !payload.access_token) {
    if (payload.error === "invalid_grant") {
      deadRefreshToken = values.refreshToken;
      cached = null;
      throw new Error("Google revoked this Analytics connection. Reconnect it from Settings.");
    }
    throw new Error(
      `Google refused the token refresh: ${payload.error_description ?? payload.error ?? res.status}`,
    );
  }
  cached = {
    token: payload.access_token,
    expiresAt: Date.now() + (payload.expires_in ?? 3600) * 1000,
  };
  return cached.token;
}

function retryable(status, reason) {
  if (status === 429 || status === 500 || status === 503) return true;
  if (status === 403) return reason === "RESOURCE_EXHAUSTED";
  return false;
}

async function call(url, body) {
  let refreshedOn401 = false;
  let attempt = 0;
  for (;;) {
    const token = await accessToken();
    const res = await apiFetch(url, {
      method: body ? "POST" : "GET",
      headers: {
        authorization: `Bearer ${token}`,
        ...(body ? { "content-type": "application/json" } : {}),
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
    });
    const payload = await res.json().catch(() => ({}));
    if (res.ok) return payload;

    if (res.status === 401 && !refreshedOn401) {
      refreshedOn401 = true;
      cached = null;
      continue;
    }
    const reason = payload.error?.status ?? "";
    if (retryable(res.status, reason) && attempt < MAX_ATTEMPTS - 1) {
      await sleep(backoffMs(attempt));
      attempt += 1;
      continue;
    }
    const err = new Error(payload.error?.message ?? `Google returned ${res.status}`);
    err.status = res.status;
    err.reason = reason;
    throw err;
  }
}

export function propertyId(property) {
  return String(property ?? "").replace(/^properties\//, "");
}

export async function listProperties() {
  const accounts = [];
  let pageToken = "";
  for (;;) {
    const params = new URLSearchParams({ pageSize: "200" });
    if (pageToken) params.set("pageToken", pageToken);
    const data = await call(`${ADMIN}/accountSummaries?${params}`);
    for (const summary of data.accountSummaries ?? []) {
      accounts.push({
        account: summary.account ?? summary.name ?? "",
        name: summary.displayName ?? "",
        properties: (summary.propertySummaries ?? []).map((p) => ({
          property: p.property ?? "",
          propertyId: propertyId(p.property),
          name: p.displayName ?? "",
          kind: p.propertyType ?? null,
        })),
      });
    }
    pageToken = data.nextPageToken ?? "";
    if (!pageToken) break;
  }
  return accounts;
}

function zip(headers, values, asNumber) {
  const row = {};
  (headers ?? []).forEach((header, i) => {
    const value = values?.[i]?.value ?? null;
    row[header.name] = asNumber ? Number(value ?? 0) || 0 : (value ?? "");
  });
  return row;
}

export async function runReport(property, { startDate, endDate, dimensions, metrics }) {
  const id = propertyId(property);
  if (!id) throw new Error("A report needs the Analytics property it reads.");

  const rows = [];
  for (let offset = 0; ; offset += ROW_LIMIT) {
    const data = await call(`${DATA}/properties/${encodeURIComponent(id)}:runReport`, {
      dateRanges: [{ startDate, endDate }],
      dimensions: dimensions.map((name) => ({ name })),
      metrics: metrics.map((name) => ({ name })),
      limit: ROW_LIMIT,
      offset,
      keepEmptyRows: false,
    });
    const batch = data.rows ?? [];
    for (const r of batch) {
      rows.push({
        ...zip(data.dimensionHeaders, r.dimensionValues, false),
        ...zip(data.metricHeaders, r.metricValues, true),
      });
    }
    if (batch.length < ROW_LIMIT) break;
  }
  return rows;
}
