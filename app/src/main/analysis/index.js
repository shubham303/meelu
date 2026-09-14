import { ENV_DEFAULTS, meeluAuthHeaders } from "../config.js";
import { apiFetch } from "../net.js";
import { extractPage } from "./extract.js";
import { textSimilarity } from "./similarity.js";

const SIMILARITY_SKIP = 0.9;
const BEAT_EVERY = 5;

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
    return json?.data ?? json;
  });
}

export function requestAnalysisStop(jobId) {
  const live = running.get(jobId);
  if (!live) return false;
  live.stop = true;
  return true;
}

export async function runAnalysis(params, emit, options = {}) {
  const { siteId, trigger = "user" } = params ?? {};
  const cookieHeader = options.cookieHeader ?? "";
  const llm = options.llm ?? null;
  if (!siteId) throw new Error("An analysis needs a website — no siteId was passed.");

  const opened = await api("/site/analysis-jobs", {
    method: "POST",
    siteId,
    cookieHeader,
    body: { trigger },
  });

  if (!opened.started) {
    emit("analysis:done", {
      ok: false,
      jobId: opened.job?.id ?? null,
      siteId,
      error: opened.reason ?? "A page analysis of this website is already running.",
    });
    return { jobId: opened.job?.id ?? null, started: false, reason: opened.reason };
  }

  const jobId = opened.job.id;
  running.set(jobId, { stop: false });
  void drive(jobId, siteId, cookieHeader, llm, emit).finally(() => running.delete(jobId));
  return { jobId, siteId, started: true };
}

async function drive(jobId, siteId, cookieHeader, llm, broadcast) {
  const emit = (event, data) => broadcast(event, { jobId, siteId, ...data });
  const call = (path, opts = {}) => api(path, { siteId, cookieHeader, ...opts });

  let plan;
  try {
    plan = await call(`/site/analysis-jobs/${jobId}/claim`, { method: "POST" });
  } catch (e) {
    emit("analysis:done", { ok: false, error: readable(e) });
    return;
  }

  const pages = plan.pages ?? [];
  const total = pages.length;
  const counters = { processed: 0, skippedUnchanged: 0, skippedSimilar: 0, failed: 0 };
  emit("analysis:started", { total });

  let sinceBeat = 0;
  let stopped = false;

  const beat = async (force = false) => {
    sinceBeat++;
    if (!force && sinceBeat < BEAT_EVERY) return;
    sinceBeat = 0;
    const res = await call(`/site/analysis-jobs/${jobId}`, {
      method: "PATCH",
      body: { heartbeat: true, ...counters },
    }).catch(() => ({ stop: false }));
    if (res.stop) stopped = true;
  };

  try {
    for (const candidate of pages) {
      if (running.get(jobId)?.stop || stopped) {
        stopped = true;
        break;
      }

      if (candidate.contentHash && candidate.analyzedFromHash === candidate.contentHash) {
        counters.skippedUnchanged++;
        await beat();
        emit("analysis:progress", { total, ...counters });
        continue;
      }

      try {
        const page = await call(`/site/pages/${candidate.pageId}`);
        if (!page.bodyText) {
          counters.failed++;
          await beat();
          continue;
        }

        if (candidate.analyzedFromHash) {
          const prior = await call(`/site/page-analysis?pageId=${candidate.pageId}`).catch(
            () => null,
          );
          if (prior?.analyzedText && textSimilarity(prior.analyzedText, page.bodyText) >= SIMILARITY_SKIP) {
            await call("/site/page-analysis", {
              method: "POST",
              body: {
                pageId: candidate.pageId,
                refreshOnly: true,
                analyzedFromHash: page.contentHash ?? null,
              },
            });
            counters.skippedSimilar++;
            await beat();
            emit("analysis:progress", { total, ...counters });
            continue;
          }
        }

        const extracted = await extractPage(page, llm);
        await call("/site/page-analysis", {
          method: "POST",
          body: {
            pageId: candidate.pageId,
            topics: extracted.topics,
            keywords: extracted.keywords,
            questionsAnswered: extracted.questionsAnswered,
            analyzedFromHash: page.contentHash ?? null,
            analyzedText: page.bodyText,
            model: extracted.model,
          },
        });
        counters.processed++;
      } catch (e) {
        counters.failed++;
        emit("analysis:page-failed", { url: candidate.url, error: readable(e) });
      }

      await beat(true);
      emit("analysis:progress", { total, ...counters });
    }

    const status = stopped ? "cancelled" : "completed";
    await call(`/site/analysis-jobs/${jobId}`, {
      method: "PATCH",
      body: { status, ...counters },
    }).catch(() => undefined);
    emit("analysis:done", { ok: true, stopped, total, ...counters });
  } catch (e) {
    await call(`/site/analysis-jobs/${jobId}`, {
      method: "PATCH",
      body: { status: "failed", error: readable(e), ...counters },
    }).catch(() => undefined);
    emit("analysis:done", { ok: false, error: readable(e), total, ...counters });
  }
}

function readable(e) {
  return e instanceof Error ? e.message : String(e);
}
