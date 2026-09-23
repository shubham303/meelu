import fs from "node:fs/promises";
import path from "node:path";
import { ENV_DEFAULTS, meeluAuthHeaders } from "../config.js";
import { apiFetch } from "../net.js";
import { appDir } from "../paths.js";
import { crawlToken } from "../crawler/token.js";
import { closeWindow, renderPage } from "./page.js";

const BEAT_EVERY = 3;

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

export function requestRenderStop(jobId) {
  const live = running.get(jobId);
  if (!live) return false;
  live.stop = true;
  return true;
}

export async function runRender(params, emit, options = {}) {
  const { siteId, trigger = "user", scope = "sample", profile = "googlebot", limit, url } = params ?? {};
  const device = params?.device === "mobile" ? "mobile" : "desktop";
  const cookieHeader = options.cookieHeader ?? "";
  if (!siteId) throw new Error("A render needs a website — no siteId was passed.");

  const opened = await api("/site/render-jobs", {
    method: "POST",
    siteId,
    cookieHeader,
    body: {
      trigger,
      scope,
      userAgentProfile: profile,
      device,
      ...(Number.isFinite(Number(limit)) && Number(limit) > 0 ? { limit: Number(limit) } : {}),
      ...(typeof url === "string" && url.trim() ? { url: url.trim() } : {}),
    },
  });

  if (!opened.started) {
    emit("render:done", {
      ok: false,
      jobId: opened.job?.id ?? null,
      siteId,
      device,
      error: opened.reason ?? "A render of this website is already running.",
    });
    return { jobId: opened.job?.id ?? null, started: false, reason: opened.reason };
  }

  const jobId = opened.job.id;
  running.set(jobId, { stop: false });
  void drive(jobId, siteId, device, cookieHeader, emit).finally(() => {
    running.delete(jobId);
    if (running.size === 0) closeWindow();
  });
  return { jobId, siteId, device, started: true };
}

async function snapshot(siteId, device, pageId, html) {
  const dir = appDir("renders", siteId, device);
  const file = path.join(dir, `${pageId}.html`);
  await fs.writeFile(file, html, "utf8");
  return file;
}

async function drive(jobId, siteId, requestedDevice, cookieHeader, broadcast) {
  let device = requestedDevice;
  const emit = (event, data) => broadcast(event, { jobId, siteId, device, ...data });
  const call = (path, opts = {}) => api(path, { siteId, cookieHeader, ...opts });

  let plan;
  try {
    plan = await call(`/site/render-jobs/${jobId}/claim`, { method: "POST" });
  } catch (e) {
    emit("render:done", { ok: false, error: readable(e) });
    return;
  }

  const pages = plan.pages ?? [];
  const total = pages.length;
  const profile = plan.job?.userAgentProfile ?? "googlebot";
  device = plan.job?.device === "mobile" ? "mobile" : plan.job?.device === "desktop" ? "desktop" : device;
  const token = crawlToken(plan.target?.domain);
  const robotsTxt = plan.target?.robotsTxt ?? null;
  const counters = { rendered: 0, skipped: 0, failed: 0 };
  emit("render:started", { total, profile, scope: plan.job?.scope ?? "sample" });

  let sinceBeat = 0;
  let stopped = false;

  const beat = async (force = false) => {
    sinceBeat++;
    if (!force && sinceBeat < BEAT_EVERY) return;
    sinceBeat = 0;
    const res = await call(`/site/render-jobs/${jobId}`, {
      method: "PATCH",
      body: { heartbeat: true, rendered: counters.rendered, failed: counters.failed },
    }).catch(() => ({ stop: false }));
    if (res.stop) stopped = true;
  };

  try {
    for (const candidate of pages) {
      if (running.get(jobId)?.stop || stopped) {
        stopped = true;
        break;
      }

      if (candidate.contentHash && candidate.renderedFromHash === candidate.contentHash) {
        counters.skipped++;
        await beat();
        emit("render:progress", { total, url: candidate.url, ...counters });
        continue;
      }

      emit("render:progress", { total, url: candidate.url, current: candidate.url, ...counters });
      try {
        const result = await renderPage({
          url: candidate.url,
          device,
          profile,
          crawlToken: token,
          robotsTxt,
        });
        if (!result.ok) {
          await call("/site/page-renders", {
            method: "POST",
            body: {
              pageId: candidate.pageId,
              device,
              renderError: result.error,
              userAgentProfile: profile,
              renderedFromHash: candidate.contentHash ?? null,
            },
          });
          counters.failed++;
          emit("render:page-failed", { url: candidate.url, error: result.error });
        } else {
          const { html, ok: _ok, device: _device, ...facts } = result;
          const htmlPath = await snapshot(siteId, device, candidate.pageId, html).catch(() => null);
          await call("/site/page-renders", {
            method: "POST",
            body: {
              pageId: candidate.pageId,
              device,
              userAgentProfile: profile,
              renderedFromHash: candidate.contentHash ?? null,
              htmlPath,
              ...facts,
            },
          });
          counters.rendered++;
        }
      } catch (e) {
        counters.failed++;
        emit("render:page-failed", { url: candidate.url, error: readable(e) });
      }

      await beat(true);
      emit("render:progress", { total, url: candidate.url, ...counters });
    }

    const status = stopped ? "cancelled" : "completed";
    await call(`/site/render-jobs/${jobId}`, {
      method: "PATCH",
      body: { status, rendered: counters.rendered, failed: counters.failed },
    }).catch(() => undefined);
    emit("render:done", { ok: true, stopped, total, ...counters });
  } catch (e) {
    await call(`/site/render-jobs/${jobId}`, {
      method: "PATCH",
      body: { status: "failed", error: readable(e), rendered: counters.rendered, failed: counters.failed },
    }).catch(() => undefined);
    emit("render:done", { ok: false, error: readable(e), total, ...counters });
  }
}

function readable(e) {
  return e instanceof Error ? e.message : String(e);
}
