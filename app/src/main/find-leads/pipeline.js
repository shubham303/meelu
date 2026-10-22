import { randomUUID } from "node:crypto";
import { createProviders } from "../providers/index.js";
import { JUDGE_BATCH, judgeBatch } from "./judge.js";
import { morePlans, needsPlan, planBriefs } from "./plan.js";
import {
  createRun,
  fetchSetup,
  getRun,
  listLeads,
  patchBrief,
  patchRun,
  saveCandidates,
  saveJudged,
  siteContextOf,
  startCollect,
  startEnrich,
  startScreen,
} from "./store.js";
import { searchWeb } from "./web.js";

const LLM_CONCURRENCY = 5;
const WEB_CONCURRENCY = 2;
const ATTEMPTS = 2;
const POLL_MS = 3000;
const ALIVE_MS = 30_000;
export const MAX_ROUNDS = 10;
export const DEFAULT_TARGET = 20;
export const MAX_TARGET = 100;

const PROGRESS_EVENTS = new Set(["round", "stage", "plan", "source", "screened", "enriched", "judged", "problem"]);

const running = new Map();
const runningBySite = new Map();

class Stopped extends Error {
  constructor() {
    super("The search was stopped.");
  }
}

function chunk(list, size) {
  const out = [];
  for (let i = 0; i < list.length; i += size) out.push(list.slice(i, i + size));
  return out;
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function newRunState(siteId) {
  let halt = () => {};
  const halted = new Promise((_, reject) => {
    halt = () => reject(new Stopped());
  });
  halted.catch(() => {});
  return { siteId, stopped: false, halted, halt, startedAt: Date.now(), progress: [] };
}

export function targetOf(value) {
  const n = Math.floor(Number(value));
  if (!Number.isFinite(n) || n < 1) return DEFAULT_TARGET;
  return Math.min(n, MAX_TARGET);
}

export function startFindLeads(payload, emit, { cookieHeader = "" }) {
  const { siteId = null } = payload ?? {};
  const target = targetOf(payload?.target);
  if (!siteId) return { error: "Pick a website first." };
  const active = runningBySite.get(siteId);
  if (active) return { error: "A lead search is already going for this site.", jobId: active };
  const jobId = randomUUID();
  const state = newRunState(siteId);
  running.set(jobId, state);
  runningBySite.set(siteId, jobId);
  const release = () => {
    running.delete(jobId);
    if (runningBySite.get(siteId) === jobId) runningBySite.delete(siteId);
  };
  void drive(jobId, siteId, target, state, emit, { cookieHeader, release }).finally(release);
  return { jobId };
}

export function stopFindLeads(jobId) {
  const state = running.get(jobId);
  if (!state) return false;
  if (!state.stopped) {
    state.stopped = true;
    state.halt();
  }
  return true;
}

export function activeFindLeads(siteId) {
  const jobId = runningBySite.get(siteId) ?? null;
  const state = jobId ? running.get(jobId) : null;
  return {
    jobId,
    stopping: state?.stopped === true,
    startedAt: state?.startedAt ?? null,
    progress: state?.progress ?? [],
  };
}

function guard(state) {
  if (state.stopped) throw new Stopped();
}

function until(state, promise) {
  guard(state);
  return Promise.race([promise, state.halted]);
}

async function pool(items, size, work) {
  let cursor = 0;
  const worker = async () => {
    while (cursor < items.length) {
      const item = items[cursor];
      cursor += 1;
      await work(item);
    }
  };
  await Promise.all(Array.from({ length: Math.min(size, items.length) }, worker));
}

async function withRetry(ctx, call) {
  let lastError = null;
  for (let attempt = 0; attempt < ATTEMPTS; attempt += 1) {
    try {
      return await until(ctx.state, call());
    } catch (err) {
      if (err instanceof Stopped) throw err;
      lastError = err;
    }
  }
  ctx.problem(lastError instanceof Error ? lastError.message : String(lastError));
  return null;
}

function hasSource(brief, source) {
  return (brief.sources ?? []).includes(source);
}

async function planStage(briefs, siteContext, ctx) {
  const { state, send, llm, siteId, cookieHeader } = ctx;
  send("stage", { stage: "plan" });
  const missing = briefs.filter(needsPlan);
  const plans = await until(
    state,
    planBriefs({ briefs: missing.map((b) => ({ id: b.id, text: b.text })), siteContext }, llm),
  );
  const out = [];
  for (const brief of briefs) {
    const plan = plans.get(brief.id);
    out.push(
      plan ? await until(state, patchBrief(siteId, brief.id, { plan }, cookieHeader)) : brief,
    );
  }
  const searches = out.reduce(
    (n, b) =>
      n +
      (hasSource(b, "posts") ? (b.plan?.keywords ?? []).length : 0) +
      (hasSource(b, "linkedin") && b.plan?.linkedin?.query ? 1 : 0) +
      (hasSource(b, "web") ? 1 : 0),
    0,
  );
  send("plan", { briefs: out.length, searches });
  return out;
}

function sourceEvent(key, stats) {
  if (!stats || stats.status === "running") return { key, status: "running" };
  return {
    key,
    status: stats.status === "error" ? "error" : "done",
    candidates: stats.candidates ?? 0,
    ...(stats.fromVendor !== undefined ? { fromVendor: stats.fromVendor } : {}),
    ...(stats.fromStore !== undefined ? { fromStore: stats.fromStore } : {}),
    ...(stats.error ? { error: stats.error } : {}),
  };
}

async function webSource(briefs, siteContext, runId, ctx) {
  const { state, send, llm, siteId, cookieHeader } = ctx;
  const webBriefs = briefs.filter((b) => hasSource(b, "web"));
  if (webBriefs.length === 0) return;
  send("source", { key: "web", status: "running" });
  let candidates = 0;
  let failed = 0;
  let lastError = null;
  await pool(webBriefs, WEB_CONCURRENCY, async (brief) => {
    try {
      const found = await until(
        state,
        searchWeb({ brief, siteContext, guard: () => guard(state) }, llm),
      );
      const saved = await until(state, saveCandidates(siteId, runId, found, cookieHeader));
      candidates += saved?.inserted ?? 0;
    } catch (err) {
      if (err instanceof Stopped) throw err;
      failed += 1;
      lastError = err instanceof Error ? err.message : String(err);
    }
  });
  send("source", {
    key: "web",
    status: failed === webBriefs.length ? "error" : "done",
    candidates,
    ...(lastError ? { error: lastError } : {}),
  });
}

async function apiSources(briefs, platforms, runId, round, ctx) {
  const { state, send, siteId, cookieHeader } = ctx;
  const searches = briefs
    .filter((b) => hasSource(b, "posts"))
    .map((b) => ({ briefId: b.id, keywords: b.plan?.keywords ?? [] }));
  const keys = [];
  if (briefs.some((b) => hasSource(b, "posts") && (b.plan?.keywords ?? []).length > 0)) {
    for (const platform of platforms) {
      try {
        await until(
          state,
          startCollect(siteId, runId, { source: "posts", platform, round, searches }, cookieHeader),
        );
        keys.push(`posts:${platform}`);
        send("source", { key: `posts:${platform}`, status: "running" });
      } catch (err) {
        if (err instanceof Stopped) throw err;
        send("source", {
          key: `posts:${platform}`,
          status: "error",
          candidates: 0,
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }
  }
  if (briefs.some((b) => hasSource(b, "linkedin") && b.plan?.linkedin?.query)) {
    try {
      await until(state, startCollect(siteId, runId, { source: "linkedin", round }, cookieHeader));
      keys.push("linkedin");
      send("source", { key: "linkedin", status: "running" });
    } catch (err) {
      if (err instanceof Stopped) throw err;
      send("source", {
        key: "linkedin",
        status: "error",
        candidates: 0,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  }
  const reported = new Set();
  while (reported.size < keys.length) {
    const run = await until(state, getRun(siteId, runId, cookieHeader));
    const stats = run?.sourceStats ?? {};
    for (const key of keys) {
      const own = stats[key];
      if (!own || own.status === "running" || reported.has(key)) continue;
      reported.add(key);
      send("source", sourceEvent(key, own));
    }
    if (reported.size < keys.length) await until(state, sleep(POLL_MS));
  }
}

async function collectStage(briefs, platforms, siteContext, runId, round, ctx) {
  ctx.send("stage", { stage: "collect" });
  await Promise.all([
    apiSources(briefs, platforms, runId, round, ctx),
    webSource(briefs, siteContext, runId, ctx),
  ]);
  const run = await until(ctx.state, getRun(ctx.siteId, runId, ctx.cookieHeader));
  return run?.foundCount ?? 0;
}

function batchesByBrief(leads, briefs, size, siteContext) {
  const textOf = new Map(briefs.map((b) => [b.id, b.text]));
  const fallback = briefs.map((b) => b.text).join(" / ");
  const groups = new Map();
  for (const lead of leads) {
    const key = textOf.has(lead.briefId) ? lead.briefId : "";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(lead);
  }
  const out = [];
  for (const [key, own] of groups) {
    const judgeCtx = { brief: textOf.get(key) ?? fallback, siteContext };
    for (const leadsChunk of chunk(own, size)) out.push({ judgeCtx, leads: leadsChunk });
  }
  return out;
}

async function jobStats(runId, key, ctx) {
  const { state, siteId, cookieHeader } = ctx;
  while (true) {
    const run = await until(state, getRun(siteId, runId, cookieHeader));
    const stats = run?.sourceStats?.[key];
    if (stats && stats.status !== "running") return stats;
    await until(state, sleep(POLL_MS));
  }
}

async function screenStage(runId, ctx) {
  const { state, send, siteId, cookieHeader } = ctx;
  send("stage", { stage: "screen" });
  await until(state, startScreen(siteId, runId, cookieHeader));
  const stats = await jobStats(runId, "screen", ctx);
  send("screened", { screened: stats.screened ?? 0, total: stats.total ?? 0, kept: stats.kept ?? 0 });
  if (stats.error) ctx.problem(`Shortlisting: ${stats.error}`);
  return stats.kept ?? 0;
}

async function enrichStage(runId, ctx) {
  const { state, send, siteId, cookieHeader } = ctx;
  send("stage", { stage: "enrich" });
  await until(state, startEnrich(siteId, runId, cookieHeader));
  const stats = await jobStats(runId, "enrich", ctx);
  send("enriched", {
    status: stats.status === "error" ? "error" : "done",
    people: stats.people ?? 0,
    fromVendor: stats.fromVendor ?? 0,
    fromStore: stats.fromStore ?? 0,
    ...(stats.error ? { error: stats.error } : {}),
  });
}

async function judgeStage(briefs, siteContext, ctx) {
  const { state, send, llm, siteId, cookieHeader } = ctx;
  send("stage", { stage: "judge" });
  const shortlist = await until(state, listLeads(siteId, "shortlisted", cookieHeader));
  send("judged", { judged: 0, total: shortlist.length, kept: 0 });
  let judged = 0;
  let kept = 0;
  await pool(batchesByBrief(shortlist, briefs, JUDGE_BATCH, siteContext), LLM_CONCURRENCY, async (batch) => {
    guard(state);
    const verdicts = await withRetry(ctx, () => judgeBatch(batch.leads, batch.judgeCtx, llm));
    if (!verdicts) return;
    const saved = await until(state, saveJudged(siteId, verdicts, cookieHeader));
    judged += verdicts.length;
    kept += saved?.kept ?? 0;
    send("judged", { judged, total: shortlist.length, kept });
  });
  return kept;
}

async function availablePlatforms(cookieHeader) {
  try {
    const providers = createProviders({ cookieHeader });
    const platforms = await providers.listening.availablePlatforms();
    return platforms.filter((p) => p?.available).map((p) => p.id);
  } catch {
    return [];
  }
}

function remember(used, briefs) {
  for (const b of briefs) {
    const own = used.get(b.id) ?? { keywords: new Set(), web: new Set() };
    for (const k of b.plan?.keywords ?? []) own.keywords.add(k);
    for (const w of b.plan?.web ?? []) own.web.add(w);
    used.set(b.id, own);
  }
}

async function nextRoundBriefs(briefs, used, siteContext, ctx) {
  const { state, send, llm } = ctx;
  send("stage", { stage: "plan" });
  const plans = await until(
    state,
    morePlans(
      {
        briefs: briefs.map((b) => ({
          id: b.id,
          text: b.text,
          sources: b.sources ?? [],
          usedKeywords: [...(used.get(b.id)?.keywords ?? [])],
          usedWeb: [...(used.get(b.id)?.web ?? [])],
        })),
        siteContext,
      },
      llm,
    ),
  );
  const out = briefs.map((b) => {
    const plan = plans.get(b.id);
    const keywords = plan?.keywords ?? [];
    const web = plan?.web ?? [];
    const sources = (b.sources ?? []).filter((s) => s !== "web" || web.length > 0);
    return { ...b, sources, plan: { ...b.plan, keywords, web } };
  });
  send("plan", {
    briefs: out.length,
    searches: out.reduce(
      (n, b) =>
        n +
        (hasSource(b, "posts") ? b.plan.keywords.length : 0) +
        (hasSource(b, "linkedin") && b.plan?.linkedin?.query ? 1 : 0) +
        (hasSource(b, "web") ? b.plan.web.length : 0),
      0,
    ),
  });
  return out;
}

async function drive(jobId, siteId, target, state, emit, { cookieHeader, release }) {
  const send = (event, data) => {
    if (PROGRESS_EVENTS.has(event)) state.progress.push({ event, data });
    emit({ jobId, event, data });
  };
  const finish = (event, data) => {
    release();
    send(event, data);
  };
  const llm = { cookieHeader, siteId, purpose: "find_leads" };
  const problems = [];
  const problem = (message) => {
    if (problems.includes(message)) return;
    problems.push(message);
    send("problem", { message });
  };
  const ctx = { state, send, llm, cookieHeader, siteId, problem };
  let runId = null;
  let alive = null;
  const counts = { shortlistedCount: 0, keptCount: 0 };

  const finishPatch = (status, extra = {}) => {
    clearInterval(alive);
    if (!runId) return Promise.resolve();
    const error = problems.length ? { error: problems.join(" · ") } : {};
    return patchRun(siteId, runId, { status, ...counts, ...error, ...extra }, cookieHeader).catch(() => {});
  };

  try {
    const [setup, platforms] = await until(
      state,
      Promise.all([fetchSetup(siteId, cookieHeader), availablePlatforms(cookieHeader)]),
    );
    const enabled = setup.briefs.filter((b) => b?.enabled !== false);
    if (enabled.length === 0) throw new Error("Add a brief describing who you are looking for first.");
    const siteContext = siteContextOf(setup.site);
    const run = await until(state, createRun(siteId, target, cookieHeader));
    runId = run?.id ?? null;
    alive = setInterval(() => {
      patchRun(siteId, runId, {}, cookieHeader).catch(() => {});
    }, ALIVE_MS);

    const planned = await planStage(enabled, siteContext, ctx);
    const used = new Map();
    let found = 0;
    let round = 0;
    let roundBriefs = planned;
    while (round < MAX_ROUNDS && counts.keptCount < target) {
      round += 1;
      if (round > 1) roundBriefs = await nextRoundBriefs(planned, used, siteContext, ctx);
      remember(used, roundBriefs);
      send("round", { round, maxRounds: MAX_ROUNDS, kept: counts.keptCount, target });
      await until(state, patchRun(siteId, runId, { round, ...counts }, cookieHeader));
      found = await collectStage(roundBriefs, platforms, siteContext, runId, round, ctx);
      counts.shortlistedCount += await screenStage(runId, ctx);
      await enrichStage(runId, ctx);
      counts.keptCount += await judgeStage(planned, siteContext, ctx);
      guard(state);
    }

    await finishPatch("done");
    finish("done", {
      found,
      shortlisted: counts.shortlistedCount,
      kept: counts.keptCount,
      target,
      rounds: round,
      problems,
    });
  } catch (err) {
    if (err instanceof Stopped) {
      await finishPatch("stopped");
      finish("stopped", {});
      return;
    }
    const message = err instanceof Error ? err.message : String(err);
    await finishPatch("error", { error: message });
    finish("error", { message });
  }
}
