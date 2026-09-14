import { ENV_DEFAULTS, meeluAuthHeaders } from "../config.js";
import { apiFetch } from "../net.js";
import { judge, pagePrompt, sitePrompt } from "./check.js";

const CONCURRENCY = 4;
const BATCH = 50;

const running = new Map();

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
    return json;
  });
}

export function requestIssueCheckStop(siteId) {
  const live = running.get(siteId);
  if (!live) return false;
  live.stop = true;
  return true;
}

export function issueCheckRunning(siteId) {
  return running.has(siteId);
}

export function runIssueCheck(params, emit, options = {}) {
  const { siteId } = params ?? {};
  const cookieHeader = options.cookieHeader ?? "";
  const llm = options.llm ?? null;
  if (!siteId) throw new Error("An issue check needs a website — no siteId was passed.");
  if (running.has(siteId)) return { siteId, started: false, reason: "An issue check is already running." };

  running.set(siteId, { stop: false });
  void drive(siteId, cookieHeader, llm, emit).finally(() => running.delete(siteId));
  return { siteId, started: true };
}

async function pending(call, path) {
  const res = await call(`${path}?llmCheckPending=true&page=1&page_size=${BATCH}`);
  return { items: res.data ?? [], total: res.pagination?.total ?? 0 };
}

async function mapLimit(items, limit, fn) {
  let index = 0;
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (index < items.length) {
      const item = items[index++];
      await fn(item);
    }
  });
  await Promise.all(workers);
}

async function drive(siteId, cookieHeader, llm, broadcast) {
  const emit = (event, data) => broadcast(event, { siteId, ...data });
  const call = (path, opts = {}) => api(path, { siteId, cookieHeader, ...opts });
  const stopped = () => running.get(siteId)?.stop === true;
  const counters = { checked: 0, kept: 0, updated: 0, deleted: 0, failed: 0 };
  const failedIds = new Set();

  try {
    const [site, sitePending, pagePending] = await Promise.all([
      call("/site").then((r) => r.data),
      pending(call, "/site/technical-seo/issues"),
      pending(call, "/site/technical-seo/page-issues"),
    ]);
    const total = sitePending.total + pagePending.total;
    emit("issue-check:started", { total });
    const progress = () => emit("issue-check:progress", { total, ...counters });

    const settle = async (path, issue, verdict) => {
      await call(`${path}/${issue.id}/llm-check`, {
        method: "POST",
        body: { verdict: verdict.verdict, ...(verdict.issue ? { issue: verdict.issue } : {}) },
      });
      counters.checked++;
      if (verdict.verdict === "keep") counters.kept++;
      if (verdict.verdict === "update") counters.updated++;
      if (verdict.verdict === "delete") counters.deleted++;
    };

    const fail = (issue, e) => {
      failedIds.add(issue.id);
      counters.failed++;
      emit("issue-check:issue-failed", { kind: issue.kind, url: issue.url ?? null, error: readable(e) });
    };

    const loop = async (path, subjectFor, promptFor) => {
      for (;;) {
        if (stopped()) return;
        const { items } = await pending(call, path);
        const fresh = items.filter((i) => !failedIds.has(i.id));
        if (fresh.length === 0) return;
        await mapLimit(fresh, CONCURRENCY, async (issue) => {
          if (stopped()) return;
          try {
            const subject = await subjectFor(issue);
            const verdict = await judge(promptFor(issue, subject), llm);
            await settle(path, issue, verdict);
          } catch (e) {
            fail(issue, e);
          }
          progress();
        });
      }
    };

    await loop("/site/technical-seo/issues", async () => site, sitePrompt);

    const pages = new Map();
    const pageFor = async (issue) => {
      if (!pages.has(issue.pageId)) {
        pages.set(issue.pageId, call(`/site/pages/${issue.pageId}`).then((r) => r.data));
      }
      return pages.get(issue.pageId);
    };
    await loop("/site/technical-seo/page-issues", pageFor, pagePrompt);

    emit("issue-check:done", { ok: true, stopped: stopped(), total, ...counters });
  } catch (e) {
    emit("issue-check:done", { ok: false, error: readable(e), ...counters });
  }
}

function readable(e) {
  return e instanceof Error ? e.message : String(e);
}
