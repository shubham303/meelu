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

export function patchRun(siteId, runId, patch, cookieHeader) {
  return api(`/social-listening/runs/${runId}`, {
    method: "PATCH",
    body: patch,
    siteId,
    cookieHeader,
  });
}

export function savePosts(siteId, runId, posts, cookieHeader) {
  if (posts.length === 0) return Promise.resolve({ inserted: 0, known: 0, duplicates: 0 });
  return api("/social-listening/posts/bulk", {
    method: "POST",
    body: { runId, posts },
    siteId,
    cookieHeader,
  });
}

export function gatePosts(siteId, cookieHeader) {
  return api("/social-listening/posts/gate", { method: "POST", body: {}, siteId, cookieHeader });
}

export function saveJudged(siteId, posts, cookieHeader) {
  if (posts.length === 0) return Promise.resolve({ updated: 0 });
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
    const rows = await api(
      `/social-listening/posts?status=matched&sort=similarity&page=${page}&page_size=100`,
      { siteId, cookieHeader },
    );
    if (!Array.isArray(rows) || rows.length === 0) break;
    out.push(...rows);
    if (rows.length < 100) break;
  }
  return out;
}

export async function listRejectedTexts(siteId, queryId, cookieHeader, limit = 5) {
  const rows = await api(
    `/social-listening/posts?status=rejected&queryId=${encodeURIComponent(queryId)}&sort=newest&page=1&page_size=${limit}`,
    { siteId, cookieHeader },
  ).catch(() => []);
  return (Array.isArray(rows) ? rows : [])
    .map((r) => [r.title, r.text].filter(Boolean).join(" — "))
    .filter(Boolean);
}

export function toIngestPost(p, dropReason = null) {
  return {
    url: p.url,
    platform: p.platform,
    externalId: p.id != null && String(p.id) !== p.url ? String(p.id) : null,
    queryId: p.queryId ?? null,
    title: p.title ?? null,
    text: p.text ?? null,
    authorHandle: p.author?.handle ?? null,
    authorName: p.author?.displayName ?? null,
    postedAt: p.createdAt ?? null,
    engagement: p.engagement ?? {},
    context: p.context ?? {},
    dropReason,
  };
}

export function toVerdict(p, status, dropReason = null) {
  return {
    id: p.id,
    status,
    dropReason: status === "dropped" ? dropReason : null,
    relevance: p.relevance ?? null,
    compositeScore: p.compositeScore ?? null,
    keepReason: p.why ?? null,
    suggestedAngle: status === "to_reply" ? p.angle ?? null : null,
  };
}
