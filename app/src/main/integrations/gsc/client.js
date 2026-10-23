import { GSC_OAUTH_CLIENT } from "../../config.js";
import { connectorValues } from "../../connector-config.js";
import { apiFetch } from "../../net.js";

const TOKEN_URL = "https://oauth2.googleapis.com/token";
const WEBMASTERS = "https://www.googleapis.com/webmasters/v3";
const INSPECTION = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect";

const ROW_LIMIT = 25_000;
const MAX_ROWS_PER_QUERY = 200_000;
const REFRESH_MARGIN_MS = 10 * 60_000;
const MAX_ATTEMPTS = 5;
const BACKOFF_CAP_MS = 64_000;

let cached = null;
let deadRefreshToken = null;

export function gscConnected() {
  const values = connectorValues("gsc");
  return !!values?.refreshToken;
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function backoffMs(attempt) {
  return Math.random() * Math.min(BACKOFF_CAP_MS, 1000 * 2 ** attempt);
}

async function accessToken() {
  const values = connectorValues("gsc");
  if (!values?.refreshToken) {
    throw new Error("Search Console is not connected on this machine.");
  }
  if (values.refreshToken === deadRefreshToken) {
    throw new Error(
      "Google no longer accepts this Search Console connection. Reconnect it from Settings.",
    );
  }
  if (cached && cached.expiresAt - REFRESH_MARGIN_MS > Date.now()) return cached.token;

  const res = await apiFetch(TOKEN_URL, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: GSC_OAUTH_CLIENT.clientId,
      client_secret: GSC_OAUTH_CLIENT.clientSecret,
      refresh_token: values.refreshToken,
      grant_type: "refresh_token",
    }).toString(),
  });
  const payload = await res.json().catch(() => ({}));
  if (!res.ok || !payload.access_token) {
    if (payload.error === "invalid_grant") {
      deadRefreshToken = values.refreshToken;
      cached = null;
      throw new Error(
        "Google revoked this Search Console connection. Reconnect it from Settings.",
      );
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
  if (status === 403) {
    return (
      reason === "quotaExceeded" ||
      reason === "userRateLimitExceeded" ||
      reason === "rateLimitExceeded"
    );
  }
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
    const reason = payload.error?.errors?.[0]?.reason ?? "";
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

export async function listProperties() {
  const data = await call(`${WEBMASTERS}/sites`);
  return (data.siteEntry ?? [])
    .filter((p) => p.permissionLevel !== "siteUnverifiedUser")
    .map((p) => ({
      siteUrl: p.siteUrl,
      permissionLevel: p.permissionLevel,
    }));
}

export function matchingProperties(domain) {
  const bare = (s) =>
    String(s)
      .replace(/^sc-domain:/, "")
      .replace(/^https?:\/\//, "")
      .replace(/\/$/, "")
      .replace(/^www\./, "")
      .toLowerCase();
  const target = bare(domain);
  return (properties) => properties.filter((p) => bare(p.siteUrl) === target);
}

export async function querySearchAnalytics(property, body) {
  const dimensions = body.dimensions ?? [];
  const rows = [];
  let aggregationType = null;
  let firstIncompleteDate = null;
  let truncated = false;

  for (let startRow = 0; ; startRow += ROW_LIMIT) {
    const data = await call(
      `${WEBMASTERS}/sites/${encodeURIComponent(property)}/searchAnalytics/query`,
      {
        type: "web",
        dataState: "final",
        aggregationType: "auto",
        ...body,
        dimensions,
        rowLimit: ROW_LIMIT,
        startRow,
      },
    );
    aggregationType = data.responseAggregationType ?? aggregationType;
    firstIncompleteDate = data.metadata?.first_incomplete_date ?? firstIncompleteDate;

    const batch = data.rows ?? [];
    for (const r of batch) {
      const row = {
        clicks: r.clicks ?? 0,
        impressions: r.impressions ?? 0,
        position: r.position ?? 0,
      };
      dimensions.forEach((dim, i) => {
        row[dim] = r.keys?.[i] ?? "";
      });
      rows.push(row);
    }
    if (batch.length < ROW_LIMIT) break;
    if (startRow + ROW_LIMIT >= MAX_ROWS_PER_QUERY) {
      truncated = true;
      break;
    }
  }
  return { rows, aggregationType, firstIncompleteDate, truncated };
}

export async function searchAnalyticsDay(property, day) {
  const { rows } = await querySearchAnalytics(property, {
    startDate: day,
    endDate: day,
    dimensions: ["query", "page", "device", "country"],
  });
  return rows;
}

export async function searchTotalsDay(property, day, dataState = "final") {
  const { rows } = await querySearchAnalytics(property, {
    startDate: day,
    endDate: day,
    dataState,
    dimensions: ["device"],
  });
  return rows;
}

export async function searchPagesDay(property, day, dataState = "final") {
  const { rows } = await querySearchAnalytics(property, {
    startDate: day,
    endDate: day,
    dataState,
    dimensions: ["page"],
  });
  return rows;
}

export async function inspectUrl(property, url) {
  try {
    const data = await call(INSPECTION, {
      inspectionUrl: url,
      siteUrl: property,
      languageCode: "en-US",
    });
    const index = data.inspectionResult?.indexStatusResult ?? {};
    return {
      url,
      verdict: index.verdict ?? null,
      coverageState: index.coverageState ?? null,
      indexingState: index.indexingState ?? null,
      robotsTxtState: index.robotsTxtState ?? null,
      pageFetchState: index.pageFetchState ?? null,
      lastCrawlTime: index.lastCrawlTime ?? null,
      googleCanonical: index.googleCanonical ?? null,
      userCanonical: index.userCanonical ?? null,
    };
  } catch (e) {
    if (e.status === 401 || e.status === 403 || e.status === 429) throw e;
    return { url, verdict: null, coverageState: null, googleCanonical: null, error: e.message };
  }
}
