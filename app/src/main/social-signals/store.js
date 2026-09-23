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
  const [config, queries, targets] = await Promise.all([
    api("/social-listening/config", opts),
    api("/social-listening/queries", opts),
    api("/social-listening/targets", opts),
  ]);
  return {
    config: config ?? {},
    queries: Array.isArray(queries) ? queries : [],
    targets: Array.isArray(targets) ? targets : [],
  };
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
  if (posts.length === 0) return Promise.resolve({ inserted: 0, updated: 0 });
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

export function saveClassified(siteId, posts, cookieHeader) {
  if (posts.length === 0) return Promise.resolve({ inserted: 0, updated: 0 });
  return api("/social-listening/posts/classified", {
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

export function knownPostUrls(siteId, urls, cookieHeader) {
  if (!Array.isArray(urls) || urls.length === 0) return Promise.resolve([]);
  return api("/social-listening/posts/known", {
    method: "POST",
    body: { urls },
    siteId,
    cookieHeader,
  }).then((known) => (Array.isArray(known) ? known : []));
}

export function latestSuccessfulRun(siteId, cookieHeader) {
  return api("/social-listening/runs?page=1&page_size=20", { siteId, cookieHeader }).then(
    (runs) => (Array.isArray(runs) ? runs.find((r) => r?.status === "done") ?? null : null),
  );
}

export function latestRun(siteId, cookieHeader) {
  return api("/social-listening/runs?page=1&page_size=1", { siteId, cookieHeader }).then(
    (runs) => (Array.isArray(runs) ? runs[0] ?? null : null),
  );
}

function classesFor(p) {
  const intent = p.classification?.intent;
  const out = [];
  if (p.classification?.isQuestion) out.push("question");
  if (intent === "praising") out.push("praise");
  if (intent === "complaining") out.push("complaint");
  if (p.kind === "competitor" && ["complaining", "seeking_tool", "seeking_help"].includes(intent)) {
    out.push("switch_opportunity");
  }
  if (p.kind === "brand" && ["seeking_tool", "seeking_help"].includes(intent)) {
    out.push("feature_request");
  }
  return out;
}

export function toFetchedPost(p, status = "fetched", keepReason = null) {
  return {
    status,
    keepReason,
    url: p.url,
    platform: p.platform,
    kind: p.kind ?? "topic",
    queryId: p.queryId ?? null,
    title: p.title ?? null,
    text: p.text ?? null,
    authorHandle: p.author?.handle ?? null,
    authorName: p.author?.displayName ?? null,
    postedAt: p.createdAt ?? null,
    engagement: p.engagement ?? {},
    context: p.context ?? {},
    matchedTargets: Array.isArray(p.matchedTargets) ? p.matchedTargets : [],
  };
}

export function toVerdict(p, status) {
  return {
    id: p.id,
    status,
    intent: p.classification?.intent ?? null,
    sentiment: p.classification?.sentiment ?? null,
    isQuestion: p.classification?.isQuestion ?? null,
    classes: classesFor(p),
    relevance: p.relevanceScore ?? null,
    compositeScore: p.compositeScore ?? null,
    keepReason: p.keepReason ?? null,
  };
}

export function fromApiPost(row) {
  return {
    id: row.id,
    url: row.url,
    platform: row.platform,
    kind: row.kind,
    queryId: row.queryId ?? null,
    title: row.title ?? null,
    text: row.text ?? "",
    author: { handle: row.authorHandle ?? "unknown", displayName: row.authorName ?? null },
    createdAt: row.postedAt ?? row.createdAt,
    engagement: row.engagement ?? {},
    context: row.context ?? {},
    matchedTargets: row.matchedTargets ?? [],
    similarity: row.similarity ?? null,
  };
}
