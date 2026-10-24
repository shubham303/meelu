import { randomUUID } from "node:crypto";
import { BATCH_SIZE, judgeBatch } from "./classify.js";
import { expandLines } from "./expand.js";
import { deadIds } from "./filters.js";
import {
  checkPosts,
  createRun,
  fetchListeningSetup,
  gatePosts,
  getRun,
  listMatchedPosts,
  listSearches,
  patchQuery,
  patchRun,
  saveVerdicts,
  saveWebPosts,
  siteContextOf,
  startCollect,
} from "./store.js";
import { recentLines, searchWebLines, WEB_PLATFORM, WEB_SEARCHED_PLATFORMS } from "./web.js";

const KEYWORDS_PER_LINE = 2;
const JUDGE_CONCURRENCY = 5;
const JUDGE_ATTEMPTS = 2;
const POLL_MS = 3000;
const ALIVE_MS = 30_000;
const GATE_TIMEOUT_MS = 60 * 60 * 1000;
const CHECK_BATCH = 100;

const PROGRESS_EVENTS = new Set(["stage", "terms", "platform", "saved", "gate", "judged", "problem"]);

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
  const controller = new AbortController();
  let halt = () => {};
  const halted = new Promise((_, reject) => {
    halt = () => {
      controller.abort();
      reject(new Stopped());
    };
  });
  halted.catch(() => {});
  return {
    siteId,
    stopped: false,
    halted,
    halt,
    signal: controller.signal,
    startedAt: Date.now(),
    progress: [],
  };
}

export function startSignalsSearch(payload, emit, { cookieHeader = "" }) {
  const { siteId = null, platforms = [] } = payload;
  if (!siteId) return { error: "Pick a website first." };
  const active = runningBySite.get(siteId);
  if (active) return { error: "A run is already going for this site.", jobId: active };
  const jobId = randomUUID();
  const state = newRunState(siteId);
  running.set(jobId, state);
  runningBySite.set(siteId, jobId);
  const input = { siteId, platforms: Array.isArray(platforms) ? platforms : [] };
  const release = () => {
    running.delete(jobId);
    if (runningBySite.get(siteId) === jobId) runningBySite.delete(siteId);
  };
  void drive(jobId, input, state, emit, { cookieHeader, release }).finally(release);
  return { jobId };
}

export function stopSignalsSearch(jobId) {
  const state = running.get(jobId);
  if (!state) return false;
  if (!state.stopped) {
    state.stopped = true;
    state.halt();
  }
  return true;
}

export function activeSignalsSearch(siteId) {
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

async function searchTerms(lines, siteContext, ctx) {
  const { state, send, llm, siteId, cookieHeader } = ctx;
  send("stage", { stage: "terms" });
  const missing = lines.filter((l) => (l.keywords ?? []).length !== KEYWORDS_PER_LINE);
  const expanded = await until(
    state,
    expandLines({ lines: missing.map((l) => ({ id: l.id, text: l.text })), siteContext }, llm),
  );
  const out = [];
  for (const line of lines) {
    const keywords = expanded.get(line.id);
    if (keywords) {
      out.push(await until(state, patchQuery(siteId, line.id, { keywords }, cookieHeader)));
    } else if ((line.keywords ?? []).length === KEYWORDS_PER_LINE) {
      out.push(line);
    }
  }
  send("terms", { lines: out.length, phrases: new Set(out.flatMap((l) => l.keywords)).size });
  if (out.length === 0) throw new Error("No line could be turned into search terms.");
  return out;
}

function platformEvent(platform, stats) {
  if (stats.status === "running") return { platform, status: "fetching" };
  const failed = stats.status === "error" || (stats.error && !stats.candidates);
  return {
    platform,
    status: failed ? "error" : "done",
    count: (stats.fromVendor ?? 0) + (stats.fromDatabase ?? 0),
    fromVendor: stats.fromVendor ?? 0,
    fromDatabase: stats.fromDatabase ?? 0,
    candidates: stats.candidates ?? 0,
    failedKeywords: stats.failedKeywords ?? [],
    skippedQueries: stats.skippedQueries ?? [],
    error: stats.error ?? null,
  };
}

async function vendorStage(platforms, runId, ctx) {
  const { state, send, siteId, cookieHeader } = ctx;
  for (const platform of platforms) {
    await until(state, startCollect(siteId, runId, platform, cookieHeader));
    send("platform", { platform, status: "fetching" });
  }
  const reported = new Set();
  while (reported.size < platforms.length) {
    const run = await until(state, getRun(siteId, runId, cookieHeader));
    const stats = run?.platformStats ?? {};
    for (const platform of platforms) {
      const own = stats[platform];
      if (!own || own.status === "running" || reported.has(platform)) continue;
      reported.add(platform);
      send("platform", platformEvent(platform, own));
    }
    if (reported.size < platforms.length) await until(state, sleep(POLL_MS));
  }
}

async function webStage(source, lines, siteContext, selected, runId, ctx) {
  const { state, send, llm, siteId, cookieHeader } = ctx;
  send("platform", { platform: source, status: "fetching" });
  try {
    const searches = await until(state, listSearches(siteId, source, cookieHeader));
    const { fresh, skippedQueries } = recentLines(lines, searches);
    const found = fresh.length
      ? await until(
          state,
          searchWebLines({ lines: fresh, siteContext, source, selected, guard: () => guard(state) }, llm),
        )
      : { posts: [], searchedLines: 0, failedLines: 0, searchedQueries: [], error: null };
    const run = await until(
      state,
      saveWebPosts(siteId, runId, { platform: source, ...found, skippedQueries }, cookieHeader),
    );
    send("platform", platformEvent(source, run?.platformStats?.[source] ?? {}));
    return null;
  } catch (err) {
    if (err instanceof Stopped) throw err;
    const message = err instanceof Error ? err.message : String(err);
    send("platform", { platform: source, status: "error", error: message });
    return [source, { status: "error", error: message }];
  }
}

function searchedOnTheWeb(platform) {
  return platform === WEB_PLATFORM || WEB_SEARCHED_PLATFORMS.includes(platform);
}

async function collectStage(input, lines, siteContext, runId, ctx) {
  const { state, send, siteId, cookieHeader } = ctx;
  send("stage", { stage: "searching" });
  const vendor = input.platforms.filter((p) => !searchedOnTheWeb(p));
  const web = input.platforms.filter(searchedOnTheWeb);
  const [, ...webOutcomes] = await Promise.all([
    vendorStage(vendor, runId, ctx),
    ...web.map((source) => webStage(source, lines, siteContext, input.platforms, runId, ctx)),
  ]);
  const run = await until(state, getRun(siteId, runId, cookieHeader));
  const candidates = input.platforms.reduce(
    (n, p) => n + (run?.platformStats?.[p]?.candidates ?? 0),
    0,
  );
  send("saved", { fetched: run?.fetchedCount ?? 0, inserted: candidates });
  const platforms = { ...run?.platformStats, ...Object.fromEntries(webOutcomes.filter(Boolean)) };
  return { fetched: run?.fetchedCount ?? 0, inserted: candidates, platforms };
}

async function gateStage(ctx) {
  const { state, send, siteId, cookieHeader } = ctx;
  send("stage", { stage: "meaning" });
  const startedAt = Date.now();
  const totals = { kept: 0, dropped: 0 };
  const poll = async () => {
    const res = await until(state, gatePosts(siteId, cookieHeader));
    totals.kept += res?.matched ?? 0;
    totals.dropped += res?.removed ?? 0;
    send("gate", { pending: res?.pending ?? 0, ...totals });
    return res;
  };
  let result = await poll();
  while ((result?.pending ?? 0) > 0 && Date.now() - startedAt < GATE_TIMEOUT_MS) {
    await until(state, sleep(POLL_MS));
    result = await poll();
  }
  return totals.kept;
}

async function judgeWithRetry(posts, judgeCtx, ctx) {
  let lastError = null;
  for (let attempt = 0; attempt < JUDGE_ATTEMPTS; attempt += 1) {
    try {
      return await until(ctx.state, judgeBatch(posts, judgeCtx, ctx.llm));
    } catch (err) {
      if (err instanceof Stopped) throw err;
      lastError = err;
    }
  }
  ctx.problem(lastError instanceof Error ? lastError.message : String(lastError));
  return null;
}

async function checkMatched(posts, ctx) {
  const { state, siteId, cookieHeader } = ctx;
  const fits = new Set();
  let removed = 0;
  for (const part of chunk(posts, CHECK_BATCH)) {
    let result = null;
    let lastError = null;
    for (let attempt = 0; attempt < JUDGE_ATTEMPTS && !result; attempt += 1) {
      try {
        result = await until(
          state,
          checkPosts(
            siteId,
            part.map((p) => p.id),
            cookieHeader,
          ),
        );
      } catch (err) {
        if (err instanceof Stopped) throw err;
        lastError = err;
      }
    }
    if (!result) {
      ctx.problem(lastError instanceof Error ? lastError.message : String(lastError));
      continue;
    }
    for (const id of result.fits ?? []) fits.add(id);
    removed += result.removed ?? 0;
  }
  return { fitting: posts.filter((p) => fits.has(p.id)), removed };
}

async function judgeStage(lines, siteContext, ctx) {
  const { state, send, siteId, cookieHeader } = ctx;
  const matched = await until(state, listMatchedPosts(siteId, cookieHeader));
  send("stage", { stage: "judging" });
  send("judged", { judged: 0, total: matched.length, kept: 0 });
  const keptByPlatform = {};
  if (matched.length === 0) return { kept: 0, keptByPlatform };
  const { fitting: posts, removed } = await checkMatched(matched, ctx);
  send("judged", { judged: removed, total: matched.length, kept: 0 });

  const linesById = new Map(lines.map((l) => [l.id, l]));
  const byLine = new Map();
  for (const p of posts) {
    if (!byLine.has(p.queryId)) byLine.set(p.queryId, []);
    byLine.get(p.queryId).push(p);
  }
  const batches = [];
  for (const [queryId, own] of byLine) {
    const line = linesById.get(queryId)?.text ?? "the conversations the marketer listens for";
    for (const b of chunk(own, BATCH_SIZE)) batches.push({ judgeCtx: { line, siteContext }, posts: b });
  }

  let judged = removed;
  let kept = 0;
  let cursor = 0;
  const worker = async () => {
    while (cursor < batches.length) {
      guard(state);
      const batch = batches[cursor];
      cursor += 1;
      const results = await judgeWithRetry(batch.posts, batch.judgeCtx, ctx);
      if (!results) continue;
      const answered = results.filter((r) => r.verdict);
      const dead = await until(state, deadIds(answered.map((r) => r.post)));
      const verdicts = answered.map(({ post, verdict }) => {
        const keep = !dead.has(post.id);
        return {
          id: post.id,
          keep,
          keepReason: keep ? verdict.why : null,
          suggestedAngle: keep ? verdict.angle : null,
        };
      });
      const saved = await until(state, saveVerdicts(siteId, verdicts, cookieHeader));
      for (const { post } of answered.filter((r, i) => verdicts[i].keep)) {
        keptByPlatform[post.platform] = (keptByPlatform[post.platform] ?? 0) + 1;
      }
      judged += answered.length;
      kept += saved?.kept ?? 0;
      send("judged", { judged, total: matched.length, kept });
    }
  };
  await Promise.all(Array.from({ length: Math.min(JUDGE_CONCURRENCY, batches.length) }, worker));
  return { kept, keptByPlatform };
}

async function drive(jobId, input, state, emit, { cookieHeader, release }) {
  const send = (event, data) => {
    if (PROGRESS_EVENTS.has(event)) state.progress.push({ event, data });
    emit({ jobId, event, data });
  };
  const finish = (event, data) => {
    release();
    send(event, data);
  };
  const llm = {
    cookieHeader,
    siteId: input.siteId,
    purpose: "social_listening",
    signal: state.signal,
  };
  const problems = [];
  const problem = (message) => {
    if (problems.includes(message)) return;
    problems.push(message);
    send("problem", { message });
  };
  const ctx = { state, send, llm, cookieHeader, siteId: input.siteId, problem };
  let runId = null;
  let alive = null;
  const counts = { matchedCount: 0, keptCount: 0 };

  const finishPatch = (status, extra = {}) => {
    clearInterval(alive);
    if (!runId) return Promise.resolve();
    const error = problems.length ? { error: problems.join(" · ") } : {};
    return patchRun(input.siteId, runId, { status, ...counts, ...error, ...extra }, cookieHeader).catch(
      () => {},
    );
  };

  try {
    const setup = await until(state, fetchListeningSetup(input.siteId, cookieHeader));
    if (!input.platforms.length) {
      input.platforms = Array.isArray(setup.config.platforms) ? setup.config.platforms : [];
    }
    if (!input.platforms.length) throw new Error("Pick at least one platform.");
    const enabledLines = setup.queries.filter((q) => q?.enabled !== false);
    if (enabledLines.length === 0) throw new Error("Add a line to listen for first.");
    const siteContext = siteContextOf(setup.site);
    const run = await until(state, createRun(input.siteId, cookieHeader));
    runId = run?.id ?? null;
    alive = setInterval(() => {
      patchRun(input.siteId, runId, {}, cookieHeader).catch(() => {});
    }, ALIVE_MS);

    const lines = await searchTerms(enabledLines, siteContext, ctx);
    const collected = await collectStage(input, lines, siteContext, runId, ctx);
    counts.matchedCount = await gateStage(ctx);
    const judgedOut = await judgeStage(lines, siteContext, ctx);
    counts.keptCount = judgedOut.kept;
    guard(state);

    await finishPatch("done");
    finish("done", {
      fetched: collected.fetched,
      inserted: collected.inserted,
      matched: counts.matchedCount,
      kept: counts.keptCount,
      problems,
      platforms: Object.fromEntries(
        Object.entries(collected.platforms ?? {}).map(([id, stats]) => [
          id,
          { ...stats, kept: judgedOut.keptByPlatform[id] ?? 0 },
        ]),
      ),
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
