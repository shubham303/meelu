import { ENV_DEFAULTS, meeluAuthHeaders } from "../config.js";
import { apiFetch } from "../net.js";

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
  }).then(async (res) => {
    const json = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(json?.error?.message ?? `${method} ${path} failed (${res.status})`);
    }
    return json?.data ?? json;
  });
}

export function fetchCampaigns(siteId, cookieHeader) {
  return api("/lead-management/campaigns", { siteId, cookieHeader }).then((rows) =>
    Array.isArray(rows) ? rows : [],
  );
}

export function fetchCampaign(siteId, campaignId, cookieHeader) {
  return api(`/lead-management/campaigns/${campaignId}`, { siteId, cookieHeader });
}

export function fetchSite(siteId, cookieHeader) {
  return api(`/sites/${siteId}`, { siteId, cookieHeader });
}

export function fetchProfile(cookieHeader) {
  return api("/profile", { cookieHeader }).catch(() => null);
}

export function createRun(siteId, campaignId, cookieHeader) {
  return api("/lead-management/runs", { method: "POST", body: { campaignId }, siteId, cookieHeader });
}

export function patchRun(siteId, runId, patch, cookieHeader) {
  return api(`/lead-management/runs/${runId}`, { method: "PATCH", body: patch, siteId, cookieHeader });
}

export function latestRun(siteId, campaignId, cookieHeader) {
  return api(`/lead-management/runs?campaignId=${campaignId}&page=1&page_size=1`, {
    siteId,
    cookieHeader,
  }).then((runs) => (Array.isArray(runs) ? runs[0] ?? null : null));
}

export function bulkLeads(siteId, { runId, campaignId, leads }, cookieHeader) {
  return api("/lead-management/leads/bulk", {
    method: "POST",
    body: { runId, campaignId, leads },
    siteId,
    cookieHeader,
  });
}

export function listLeads(siteId, { stage = null, page = 1, pageSize = 100 } = {}, cookieHeader) {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (stage) params.set("stage", stage);
  return api(`/lead-management/leads?${params}`, { siteId, cookieHeader }).then((rows) =>
    Array.isArray(rows) ? rows : [],
  );
}

export function getLead(siteId, leadId, cookieHeader) {
  return api(`/lead-management/leads/${leadId}`, { siteId, cookieHeader });
}

export function toApiLead(p) {
  return {
    name: p.name,
    company: p.company ?? null,
    role: p.role ?? null,
    email: p.email ?? null,
    emailVerified: Boolean(p.emailVerified),
    website: p.website ?? null,
    source: p.source ?? null,
    sourceUrl: p.sourceUrl ?? null,
    channelHandles: p.channelHandles ?? {},
    fitScore: p.fitScore ?? null,
    fitReason: p.fitReason ?? null,
    evidence: Array.isArray(p.evidence) ? p.evidence : [],
  };
}
