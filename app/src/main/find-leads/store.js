import { ENV_DEFAULTS, meeluAuthHeaders } from "../config.js";
import { apiFetch } from "../net.js";

const PAGE_SIZE = 100;
const MAX_PAGES = 40;
const REQUEST_TIMEOUT_MS = 30_000;

function api(path, { method = "GET", body, siteId, cookieHeader } = {}) {
  const headers = {
    ...meeluAuthHeaders(cookieHeader),
    ...(body ? { "content-type": "application/json" } : {}),
    ...(siteId ? { "x-meelu-site": siteId } : {}),
  };
  return apiFetch(`${ENV_DEFAULTS.meeluBaseUrl}/api/v1${path}`, {
    method,
    headers,
    ...(body ? { body: JSON.stringify(body) } : {}),
    signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
  }).then(async (res) => {
    const json = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(json?.error?.message ?? `${method} ${path} failed (${res.status})`);
    }
    return json?.data ?? json;
  });
}

export async function fetchSetup(siteId, cookieHeader) {
  const opts = { siteId, cookieHeader };
  const [briefs, site] = await Promise.all([
    api("/find-leads/briefs", opts),
    api(`/sites/${siteId}`, opts).catch(() => null),
  ]);
  return { briefs: Array.isArray(briefs) ? briefs : [], site };
}

export function siteContextOf(site) {
  return [
    site?.name ? `Site: ${site.name} (${site.domain ?? ""})` : "",
    site?.summary ? `What it is: ${site.summary}` : "",
  ]
    .filter(Boolean)
    .join("\n");
}

export function patchBrief(siteId, briefId, patch, cookieHeader) {
  return api(`/find-leads/briefs/${briefId}`, { method: "PATCH", body: patch, siteId, cookieHeader });
}

export function createRun(siteId, targetCount, cookieHeader) {
  return api("/find-leads/runs", { method: "POST", body: { targetCount }, siteId, cookieHeader });
}

export function getRun(siteId, runId, cookieHeader) {
  return api(`/find-leads/runs/${runId}`, { siteId, cookieHeader });
}

export function patchRun(siteId, runId, patch, cookieHeader) {
  return api(`/find-leads/runs/${runId}`, { method: "PATCH", body: patch, siteId, cookieHeader });
}

export function startCollect(siteId, runId, request, cookieHeader) {
  return api(`/find-leads/runs/${runId}/collect`, {
    method: "POST",
    body: request,
    siteId,
    cookieHeader,
  });
}

export function startScreen(siteId, runId, cookieHeader) {
  return api(`/find-leads/runs/${runId}/screen`, { method: "POST", body: {}, siteId, cookieHeader });
}

export function startEnrich(siteId, runId, cookieHeader) {
  return api(`/find-leads/runs/${runId}/enrich`, { method: "POST", body: {}, siteId, cookieHeader });
}

export function saveCandidates(siteId, runId, leads, cookieHeader) {
  if (leads.length === 0) return Promise.resolve({ inserted: 0, skipped: 0 });
  return api("/find-leads/leads/candidates", {
    method: "POST",
    body: { runId, leads },
    siteId,
    cookieHeader,
  });
}

export function saveJudged(siteId, leads, cookieHeader) {
  if (leads.length === 0) return Promise.resolve({ kept: 0, removed: 0 });
  return api("/find-leads/leads/judged", { method: "POST", body: { leads }, siteId, cookieHeader });
}

export async function listLeads(siteId, status, cookieHeader) {
  const out = [];
  for (let page = 1; page <= MAX_PAGES; page += 1) {
    const rows = await api(`/find-leads/leads?status=${status}&page=${page}&page_size=${PAGE_SIZE}`, {
      siteId,
      cookieHeader,
    });
    if (!Array.isArray(rows) || rows.length === 0) break;
    out.push(...rows);
    if (rows.length < PAGE_SIZE) break;
  }
  return out;
}
