import { PAGES, SITE_ID } from "../data/site";
import { channel, sleep, uid } from "./channel";
import { inspectedUrl, syncEvent } from "./hooks";

export interface JobMessage {
  event: string;
  data: Record<string, unknown>;
}

export const crawlChannel = channel<JobMessage>();
export const renderChannel = channel<JobMessage>();

function sendCrawl(event: string, data: Record<string, unknown>) {
  if (!event.startsWith("crawl:")) syncEvent(event, data);
  crawlChannel.emit({ event, data });
}

function sendRender(event: string, data: Record<string, unknown>) {
  renderChannel.emit({ event, data });
}

const stops = new Set<string>();
let crawlRunning: string | null = null;
const renderRunning = new Map<string, string>();
const syncRunning = new Map<string, string>();
let indexRunning = false;

const day = (offset: number) => new Date(Date.now() - offset * 86_400_000).toISOString().slice(0, 10);

async function driveCrawl(jobId: string, siteId: string) {
  const total = PAGES.length;
  sendCrawl("crawl:started", { siteId, jobId, domain: "ledgerly.app", known: total });
  let fetched = 0;
  let seen = Math.round(total * 0.7);
  while (fetched < total && !stops.has(jobId)) {
    await sleep(160 + Math.random() * 160);
    fetched = Math.min(total, fetched + 1 + Math.floor(Math.random() * 4));
    seen = Math.min(total, Math.max(seen, fetched + Math.floor(Math.random() * 6)));
    sendCrawl("crawl:progress", {
      siteId,
      jobId,
      phase: fetched < total * 0.8 ? "sitemap" : "links",
      fetched,
      queued: Math.max(0, seen - fetched),
      seen,
    });
  }
  const stopped = stops.has(jobId);
  stops.delete(jobId);
  crawlRunning = null;
  sendCrawl("crawl:done", {
    siteId,
    jobId,
    ok: true,
    domain: "ledgerly.app",
    stopped,
    complete: !stopped,
    pagesStored: fetched,
    counts: { fetched, skipped: 0, failed: 0 },
  });
}

export function crawlSite(payload: { siteId: string | null }) {
  const siteId = payload.siteId ?? SITE_ID;
  if (crawlRunning) return { jobId: crawlRunning, started: false, reason: "A crawl of this website is already running." };
  const jobId = uid("crawl");
  crawlRunning = jobId;
  void driveCrawl(jobId, siteId);
  return { jobId, siteId, started: true };
}

export function stopJob(jobId: string) {
  stops.add(jobId);
  return { stopping: true };
}

async function driveRender(jobId: string, siteId: string, device: string, total: number, only?: string) {
  const urls = only ? [only] : PAGES.filter((p) => p.status === 200).map((p) => p.url);
  sendRender("render:started", { siteId, jobId, device, total, rendered: 0, failed: 0, skipped: 0 });
  let rendered = 0;
  let skipped = 0;
  let failed = 0;
  for (let i = 0; i < total && !stops.has(jobId); i++) {
    await sleep(260 + Math.random() * 340);
    const url = urls[i % urls.length];
    if (!only && i % 9 === 4) skipped += 1;
    else if (!only && i === total - 2 && total > 6) failed += 1;
    else rendered += 1;
    sendRender("render:progress", { siteId, jobId, device, total, rendered, failed, skipped, current: url });
  }
  const stopped = stops.has(jobId);
  stops.delete(jobId);
  renderRunning.delete(device);
  sendRender("render:done", { siteId, jobId, device, ok: true, stopped, rendered, total, failed, skipped });
}

export function renderSite(payload: { siteId: string | null; device: string; scope?: string; limit?: number; url?: string }) {
  const siteId = payload.siteId ?? SITE_ID;
  const busy = renderRunning.get(payload.device);
  if (busy) return { jobId: busy, started: false, reason: `A ${payload.device} render is already running.` };
  const live = PAGES.filter((p) => p.status === 200).length;
  const total = payload.url ? 1 : payload.scope === "all" ? live : Math.min(payload.limit ?? 12, live);
  const jobId = uid("render");
  renderRunning.set(payload.device, jobId);
  void driveRender(jobId, siteId, payload.device, total, payload.url);
  return { jobId, started: true };
}

async function driveSync(kind: "search" | "traffic", syncId: string, siteId: string) {
  const daysTotal = 21;
  const property = kind === "search" ? "sc-domain:ledgerly.app" : "properties/384920111";
  sendCrawl(`${kind}:started`, { siteId, syncId, property, daysTotal, resumeFrom: day(daysTotal + 1) });
  let daysDone = 0;
  let rowsStored = 0;
  const step = 3;
  while (daysDone < daysTotal && !stops.has(syncId)) {
    await sleep(380 + Math.random() * 260);
    daysDone = Math.min(daysTotal, daysDone + step);
    rowsStored += kind === "search" ? 1_180 + Math.floor(Math.random() * 400) : 310 + Math.floor(Math.random() * 90);
    sendCrawl(`${kind}:progress`, {
      siteId,
      syncId,
      phase: "days",
      daysDone,
      daysTotal,
      rowsStored,
      day: day(daysTotal - daysDone + 1),
      ...(kind === "traffic" ? { report: "landing_pages" } : {}),
    });
  }
  const stopped = stops.has(syncId);
  stops.delete(syncId);
  syncRunning.delete(kind);
  sendCrawl(`${kind}:done`, { siteId, syncId, ok: true, stopped, daysDone, rowsStored });
}

export function startSync(kind: "search" | "traffic", payload: { siteId: string | null }) {
  const siteId = payload.siteId ?? SITE_ID;
  const busy = syncRunning.get(kind);
  if (busy) return { syncId: busy, started: false, reason: "A sync is already running." };
  const syncId = uid(kind === "search" ? "gsc" : "ga");
  syncRunning.set(kind, syncId);
  void driveSync(kind, syncId, siteId);
  return { syncId, started: true };
}

export function stopSync(payload: { syncId: string }) {
  stops.add(payload.syncId);
  return { stopping: true };
}

async function driveIndexCheck(siteId: string, total: number) {
  for (let inspected = 0; inspected < total; ) {
    await sleep(220 + Math.random() * 180);
    inspected = Math.min(total, inspected + 1 + Math.floor(Math.random() * 3));
    sendCrawl("index:progress", { siteId, inspected, total });
  }
  indexRunning = false;
  sendCrawl("index:done", {
    siteId,
    ok: true,
    inspected: total,
    note: "Two pages moved from Discovered to Indexed since the last check.",
  });
}

export function indexCheck(payload: { siteId: string | null }) {
  if (indexRunning) return { error: "An index check is already running." };
  const siteId = payload.siteId ?? SITE_ID;
  const total = Math.min(24, PAGES.filter((p) => p.status === 200).length);
  indexRunning = true;
  void driveIndexCheck(siteId, total);
  return { started: true, total, inspected: 0 };
}

export async function inspectPageUrl(payload: { siteId: string | null; url: string }) {
  await sleep(900 + Math.random() * 600);
  inspectedUrl(payload.url);
  return {
    inspection: {
      verdict: "PASS",
      coverageState: "Submitted and indexed",
      indexingState: "INDEXING_ALLOWED",
      lastCrawlTime: new Date(Date.now() - 3 * 86_400_000).toISOString(),
      googleCanonical: payload.url,
      userCanonical: payload.url,
    },
  };
}
