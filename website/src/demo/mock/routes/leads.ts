import type { Lead, LeadBrief, LeadReviewStatus, LeadRun, LeadSource, LeadSummary } from "@demo/lib/types";
import * as data from "../data/leads";
import { SITE_ID } from "../data/site";
import { b, MockHttpError, newId, now, ok, paginate, type Route } from "../core";

const REVIEW: LeadReviewStatus[] = ["new", "contacted", "discarded"];
const SOURCES: LeadSource[] = ["posts", "linkedin", "web"];
const MAX_BRIEFS = 10;

const state = {
  briefs: data.BRIEFS.map((x) => ({ ...x, sources: [...x.sources] })) as LeadBrief[],
  leads: data.LEADS.map((l) => ({ ...l })) as Lead[],
  runs: data.RUNS.map((r) => ({ ...r })) as LeadRun[],
  pool: [...data.POOL],
};

function summary(): LeadSummary {
  const count = (s: string) => state.leads.filter((l) => l.status === s).length;
  const lastRun = [...state.runs].sort((a, c) => c.startedAt.localeCompare(a.startedAt))[0] ?? null;
  return {
    new: count("new"),
    contacted: count("contacted"),
    discarded: count("discarded"),
    unprocessed: count("candidate") + count("shortlisted"),
    lastRun,
  };
}

function findBrief(id: string): LeadBrief {
  const brief = state.briefs.find((x) => x.id === id);
  if (!brief) throw new MockHttpError(404, "Not found");
  return brief;
}

function cleanSources(value: unknown): LeadSource[] | null {
  if (!Array.isArray(value)) return null;
  const out = value.map(String).filter((s): s is LeadSource => (SOURCES as string[]).includes(s));
  if (out.length === 0) throw new MockHttpError(400, "Pick at least one place to look.");
  return [...new Set(out)];
}

function cleanText(value: unknown): string {
  const text = String(value ?? "").split(/\s+/).filter(Boolean).join(" ");
  if (!text) throw new MockHttpError(400, "Describe who you are looking for.");
  return text;
}

function listLeads(q: URLSearchParams) {
  const status = q.get("status") ?? "new";
  const briefId = q.get("briefId");
  const needle = (q.get("q") ?? "").trim().toLowerCase();
  const rows = state.leads
    .filter((l) => l.status === status)
    .filter((l) => !briefId || l.briefId === briefId)
    .filter((l) => !needle || (l.name ?? "").toLowerCase().includes(needle))
    .sort((a, c) => {
      const key = (l: Lead) => (status === "contacted" ? l.contactedAt : status === "discarded" ? l.discardedAt : l.updatedAt) ?? "";
      return key(c).localeCompare(key(a));
    });
  return paginate(rows, q);
}

export const ROUTES: Route[] = [
  ["GET", /^\/api\/v1\/find-leads\/briefs$/, () => ok(state.briefs)],
  ["POST", /^\/api\/v1\/find-leads\/briefs$/, (_m, _q, body) => {
    if (state.briefs.length >= MAX_BRIEFS) throw new MockHttpError(400, `A website can keep at most ${MAX_BRIEFS} briefs.`);
    const brief: LeadBrief = {
      id: newId("lb"),
      createdAt: now(),
      updatedAt: now(),
      siteId: SITE_ID,
      text: cleanText(b(body, "text")),
      enabled: true,
      source: "user",
      sources: cleanSources(b(body, "sources")) ?? ["posts", "linkedin"],
      plan: {},
      found: 0,
      kept: 0,
    };
    state.briefs.push(brief);
    return ok(brief);
  }],
  ["PATCH", /^\/api\/v1\/find-leads\/briefs\/([^/]+)$/, (m, _q, body) => {
    const brief = findBrief(m[1]);
    if (typeof body.enabled === "boolean") brief.enabled = body.enabled;
    if ("text" in body) {
      const text = cleanText(body.text);
      if (text !== brief.text) Object.assign(brief, { text, plan: {} });
    }
    const sources = cleanSources(body.sources);
    if (sources) brief.sources = sources;
    brief.updatedAt = now();
    return ok(brief);
  }],
  ["DELETE", /^\/api\/v1\/find-leads\/briefs\/([^/]+)$/, (m) => {
    findBrief(m[1]);
    state.briefs = state.briefs.filter((x) => x.id !== m[1]);
    return ok({ id: m[1] });
  }],
  ["GET", /^\/api\/v1\/find-leads\/summary$/, () => ok(summary())],
  ["GET", /^\/api\/v1\/find-leads\/leads$/, (_m, q) => listLeads(q)],
  ["PATCH", /^\/api\/v1\/find-leads\/leads\/([^/]+)$/, (m, _q, body) => {
    const lead = state.leads.find((l) => l.id === m[1]);
    if (!lead) throw new MockHttpError(404, "Not found");
    const status = b(body, "status");
    if (typeof status !== "string" || !(REVIEW as string[]).includes(status)) {
      throw new MockHttpError(400, `status must be one of ${REVIEW.join(", ")}.`);
    }
    lead.status = status as LeadReviewStatus;
    lead.contactedAt = status === "contacted" ? now() : null;
    lead.discardedAt = status === "discarded" ? now() : null;
    lead.updatedAt = now();
    return ok(lead);
  }],
];

export function leadsWaiting(): number {
  return state.leads.filter((l) => l.status === "new").length;
}

export interface LeadRunEvent {
  jobId: string;
  event: string;
  data: Record<string, unknown>;
}

interface Job {
  siteId: string;
  stopped: boolean;
  startedAt: number;
  progress: Array<{ event: string; data: Record<string, unknown> }>;
}

const jobs = new Map<string, Job>();
const jobBySite = new Map<string, string>();
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

class Stopped extends Error {}

const POST_PLATFORMS: Array<[string, number]> = [
  ["reddit", 52],
  ["x", 31],
  ["hackernews", 11],
  ["bluesky", 8],
  ["linkedin", 14],
];

let leadCounter = 200;

async function drive(jobId: string, job: Job, target: number, emit: (e: LeadRunEvent) => void) {
  const send = (event: string, d: Record<string, unknown>) => {
    job.progress.push({ event, data: d });
    emit({ jobId, event, data: d });
  };
  const step = async (ms: number) => {
    await sleep(ms);
    if (job.stopped) throw new Stopped();
  };
  const finish = (event: string, d: Record<string, unknown>) => {
    jobs.delete(jobId);
    if (jobBySite.get(job.siteId) === jobId) jobBySite.delete(job.siteId);
    emit({ jobId, event, data: d });
  };

  const briefs = state.briefs.filter((x) => x.enabled);
  const sources = new Set(briefs.flatMap((x) => x.sources));
  const run: LeadRun = {
    id: newId("lr"),
    createdAt: now(),
    updatedAt: now(),
    siteId: SITE_ID,
    status: "running",
    startedAt: now(),
    finishedAt: null,
    foundCount: 0,
    shortlistedCount: 0,
    keptCount: 0,
    sourceStats: {},
    error: null,
  };
  state.runs.push(run);
  const close = (status: LeadRun["status"]) => Object.assign(run, { status, finishedAt: now(), updatedAt: now() });

  try {
    send("stage", { stage: "plan" });
    await step(1200);
    send("plan", { briefs: briefs.length, searches: briefs.length * 3 + (sources.has("linkedin") ? 1 : 0) });
    await step(500);
    send("round", { round: 1, maxRounds: 3, kept: 0, target });

    let found = 0;
    if (sources.has("posts")) {
      for (const [platform, base] of POST_PLATFORMS) {
        const key = `posts:${platform}`;
        send("source", { key, status: "running", candidates: 0 });
        await step(600 + Math.random() * 500);
        const fromVendor = Math.round(base * (0.7 + Math.random() * 0.5));
        const fromStore = Math.round(fromVendor * 0.25);
        found += fromVendor + fromStore;
        run.sourceStats[key] = { status: "done", candidates: fromVendor + fromStore, fromVendor, fromStore };
        send("source", { key, status: "done", candidates: fromVendor + fromStore, fromVendor, fromStore });
      }
    }
    for (const key of ["linkedin", "web"] as const) {
      if (!sources.has(key)) continue;
      send("source", { key, status: "running", candidates: 0 });
      await step(900);
      const candidates = key === "linkedin" ? 38 : 17;
      found += candidates;
      run.sourceStats[key] = { status: "done", candidates };
      send("source", { key, status: "done", candidates });
    }
    run.foundCount = found;

    send("stage", { stage: "screen" });
    const shortlisted = Math.round(found * 0.16);
    for (const share of [0.4, 0.75, 1]) {
      await step(600);
      send("screened", { screened: Math.round(found * share), total: found, kept: Math.round(shortlisted * share) });
    }
    run.shortlistedCount = shortlisted;

    send("stage", { stage: "enrich" });
    send("enriched", { status: "running", people: 0, fromVendor: 0, fromStore: 0 });
    await step(1500);
    send("enriched", { status: "done", people: shortlisted, fromVendor: shortlisted - 4, fromStore: 4 });

    send("stage", { stage: "judge" });
    const picks = state.pool.filter((s) => briefs.some((x) => x.id === s.brief)).slice(0, Math.max(1, Math.min(target, 3)));
    let judged = 0;
    let kept = 0;
    const perBatch = Math.max(1, Math.ceil(shortlisted / 4));
    while (judged < shortlisted) {
      await step(850);
      judged = Math.min(shortlisted, judged + perBatch);
      const due = Math.min(picks.length, Math.round((judged / shortlisted) * picks.length));
      while (kept < due) {
        const seed = picks[kept];
        state.pool = state.pool.filter((s) => s !== seed);
        leadCounter += 1;
        state.leads.push(data.leadFromPool(seed, leadCounter, run.id));
        kept += 1;
      }
      run.keptCount = kept;
      send("judged", { judged, total: shortlisted, kept });
    }
    for (const x of briefs) {
      x.found += Math.round(found / briefs.length);
      x.kept += picks.filter((s) => s.brief === x.id).length;
    }
    close("done");
    finish("done", { found, shortlisted, kept });
  } catch (e) {
    if (e instanceof Stopped) {
      close("stopped");
      finish("stopped", {});
      return;
    }
    const message = e instanceof Error ? e.message : String(e);
    close("error");
    run.error = message;
    finish("error", { message });
  }
}

export const leadsRun = {
  start(payload: { siteId: string; target?: number }, emit: (e: LeadRunEvent) => void): { jobId?: string; error?: string } {
    const { siteId } = payload;
    if (!siteId) return { error: "Pick a website first." };
    const active = jobBySite.get(siteId);
    if (active) return { error: "A run is already going for this site.", jobId: active };
    if (!state.briefs.some((x) => x.enabled)) return { error: "Turn on a brief first." };
    const jobId = newId("fljob");
    const job: Job = { siteId, stopped: false, startedAt: Date.now(), progress: [] };
    jobs.set(jobId, job);
    jobBySite.set(siteId, jobId);
    void drive(jobId, job, payload.target ?? 20, emit);
    return { jobId };
  },
  stop(jobId: string): { stopping: boolean } {
    const job = jobs.get(jobId);
    if (!job) return { stopping: false };
    job.stopped = true;
    return { stopping: true };
  },
  active(siteId: string) {
    const jobId = jobBySite.get(siteId) ?? null;
    const job = jobId ? jobs.get(jobId) : undefined;
    return {
      jobId,
      stopping: job?.stopped === true,
      startedAt: job?.startedAt ?? null,
      progress: job ? [...job.progress] : [],
    };
  },
};
