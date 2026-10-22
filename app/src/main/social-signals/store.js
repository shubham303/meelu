import { ENV_DEFAULTS, meeluAuthHeaders } from "../config.js";
import { apiFetch } from "../net.js";

const REQUEST_TIMEOUT_MS = 60_000;

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

export async function fetchListeningSetup(siteId, cookieHeader) {
  const opts = { siteId, cookieHeader };
  const [config, queries, site] = await Promise.all([
    api("/social-listening/config", opts),
    api("/social-listening/queries", opts),
    api(`/sites/${siteId}`, opts).catch(() => null),
  ]);
  return {
    config: config ?? {},
    queries: Array.isArray(queries) ? queries : [],
    site,
  };
}

export function siteContextOf(site) {
  return [
    site?.name ? `Site: ${site.name} (${site.domain ?? ""})` : "",
    site?.summary ? `What it is: ${site.summary}` : "",
  ]
    .filter(Boolean)
    .join("\n");
}

export function patchQuery(siteId, queryId, patch, cookieHeader) {
  return api(`/social-listening/queries/${queryId}`, {
    method: "PATCH",
    body: patch,
    siteId,
    cookieHeader,
  });
}

export function createRun(siteId, cookieHeader) {
  return api("/social-listening/runs", { method: "POST", body: {}, siteId, cookieHeader });
}

export function getRun(siteId, runId, cookieHeader) {
  return api(`/social-listening/runs/${runId}`, { siteId, cookieHeader });
}

export function patchRun(siteId, runId, patch, cookieHeader) {
  return api(`/social-listening/runs/${runId}`, {
    method: "PATCH",
    body: patch,
    siteId,
    cookieHeader,
  });
}

export function startCollect(siteId, runId, platform, cookieHeader) {
  return api(`/social-listening/runs/${runId}/collect`, {
    method: "POST",
    body: { platform },
    siteId,
    cookieHeader,
  });
}

export function gatePosts(siteId, cookieHeader) {
  return api("/social-listening/posts/gate", { method: "POST", body: {}, siteId, cookieHeader });
}

export function saveVerdicts(siteId, posts, cookieHeader) {
  if (posts.length === 0) return Promise.resolve({ kept: 0, removed: 0 });
  return api("/social-listening/posts/judged", {
    method: "POST",
    body: { posts },
    siteId,
    cookieHeader,
  });
}

export async function listMatchedPosts(siteId, cookieHeader) {
  const out = [];
  for (let page = 1; page <= 40; page += 1) {
    const rows = await api(`/social-listening/posts?status=matched&page=${page}&page_size=100`, {
      siteId,
      cookieHeader,
    });
    if (!Array.isArray(rows) || rows.length === 0) break;
    out.push(...rows);
    if (rows.length < 100) break;
  }
  return out;
}
