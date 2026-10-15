import { randomUUID } from "node:crypto";
import { BATCH_SIZE, judgeBatch } from "./classify.js";
import { expandLine } from "./expand.js";
import { dropDead, withinAge } from "./filters.js";
import { withScores } from "./rank.js";
import {
  createRun,
  fetchListeningSetup,
  gatePosts,
  listMatchedPosts,
  listRejectedTexts,
  patchQuery,
  patchRun,
  saveJudged,
  savePosts,
  siteContextOf,
  toIngestPost,
  toVerdict,
} from "./store.js";

const DEFAULT_MIN_RELEVANCE = 0.6;
const JUDGE_CONCURRENCY = 5;
const GATE_POLL_MS = 3000;
const GATE_TIMEOUT_MS = 10 * 60 * 1000;
const MAX_PER_LINE = 100;

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
  return { siteId, stopped: false, halted, halt };
}

export function startSignalsSearch(payload, emit, { providers, cookieHeader = "" }) {
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
  void drive(jobId, input, state, emit, { providers, cookieHeader, release }).finally(release);
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
  return { jobId, stopping: jobId ? running.get(jobId)?.stopped === true : false };
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
  const out = [];
  for (const line of lines) {
    const keywords = Array.isArray(line.keywords) ? line.keywords.filter(Boolean) : [];
    if (keywords.length > 0) {
      out.push({ ...line, keywords, negativeKeywords: line.negativeKeywords ?? [] });
      continue;
    }
    guard(state);
    const terms = await until(state, expandLine({ line: line.text, siteContext }, llm));
    const patched = await until(state, patchQuery(siteId, line.id, terms, cookieHeader));
    out.push({ ...line, ...patched });
  }
  send("terms", { lines: out.length, phrases: out.reduce((n, l) => n + l.keywords.length, 0) });
  return out;
}

async function searchPlatforms(input, lines, perLine, since, ctx, platformStats) {
  const { state, send, providers } = ctx;
  send("stage", { stage: "searching" });
  const fetched = [];
  await Promise.allSettled(
    input.platforms.map(async (platform) => {
      send("platform", { platform, status: "fetching" });
      const stat = { fetched: 0, kept: 0 };
      platformStats[platform] = stat;
      let lastError = null;
      for (const line of lines) {
        try {
          const posts = await until(
            state,
            providers.listening.searchPlatform({
              platform,
              keywords: line.keywords,
              since,
              limit: perLine(line),
              siteId: input.siteId,
            }),
          );
          for (const p of posts) fetched.push({ ...p, queryId: line.id });
          stat.fetched += posts.length;
        } catch (err) {
          if (err instanceof Stopped) throw err;
          lastError = err instanceof Error ? err.message : String(err);
        }
      }
      if (lastError) stat.error = lastError;
      if (lastError && stat.fetched === 0) {
        send("platform", { platform, status: "error", error: lastError });
      } else {
        send("platform", { platform, status: "done", count: stat.fetched });
      }
    }),
  );
  return fetched;
}

function excludedWord(post, line) {
  const hay = `${post.title ?? ""} ${post.text ?? ""}`.toLowerCase();
  return (line?.negativeKeywords ?? []).find((k) => hay.includes(String(k).toLowerCase())) ?? null;
}

async function fetchStage(input, setup, lines, ctx, platformStats, runId) {
  const { state, send, cookieHeader } = ctx;
  const config = setup.config;
  const lookbackDays = Number(config.maxAgeDays) > 0 ? Number(config.maxAgeDays) : null;
  const since = lookbackDays
    ? new Date(Date.now() - lookbackDays * 86_400_000).toISOString()
    : null;

  const perKeyword = Math.max(5, Number(config.resultsPerKeyword) || 50);
  const perLine = (line) => Math.min(perKeyword * line.keywords.length, MAX_PER_LINE);
  const fetched = await searchPlatforms(input, lines, perLine, since, ctx, platformStats);
  guard(state);

  const linesById = new Map(lines.map((l) => [l.id, l]));
  const fresh = new Set(withinAge(fetched, config.maxAgeDays));
  const payload = fetched.map((p) => {
    if (!fresh.has(p)) return toIngestPost(p, "too_old");
    if (excludedWord(p, linesById.get(p.queryId))) return toIngestPost(p, "excluded_word");
    return toIngestPost(p);
  });
  const totals = { inserted: 0, known: 0, duplicates: 0 };
  for (const batch of chunk(payload, 200)) {
    const res = await until(state, savePosts(input.siteId, runId, batch, cookieHeader));
    totals.inserted += res?.inserted ?? 0;
    totals.known += res?.known ?? 0;
    totals.duplicates += res?.duplicates ?? 0;
    guard(state);
  }
  send("saved", { fetched: fetched.length, ...totals });
  return { fetched: fetched.length, inserted: totals.inserted, lookbackDays };
}

async function gateStage(input, ctx) {
  const { state, send, cookieHeader } = ctx;
  send("stage", { stage: "meaning" });
  const startedAt = Date.now();
  const totals = { kept: 0, dropped: 0 };
  const poll = async () => {
    const res = await until(state, gatePosts(input.siteId, cookieHeader));
    totals.kept += res?.kept ?? 0;
    totals.dropped += res?.dropped ?? 0;
    send("gate", { pending: res?.pending ?? 0, ...totals });
    return res;
  };
  let result = await poll();
  while ((result?.pending ?? 0) > 0 && Date.now() - startedAt < GATE_TIMEOUT_MS) {
    await until(state, sleep(GATE_POLL_MS));
    result = await poll();
  }
  return totals.kept;
}

async function judgeStage(input, setup, lines, siteContext, ctx, platformStats) {
  const { state, send, llm, cookieHeader } = ctx;
  const posts = await until(state, listMatchedPosts(input.siteId, cookieHeader));
  send("stage", { stage: "judging" });
  send("judged", { judged: 0, total: posts.length, kept: 0 });
  if (posts.length === 0) return 0;

  const minRelevance = Number.isFinite(Number(setup.config.minRelevance))
    ? Number(setup.config.minRelevance)
    : DEFAULT_MIN_RELEVANCE;
  const linesById = new Map(lines.map((l) => [l.id, l]));
  const byLine = new Map();
  for (const p of posts) {
    if (!byLine.has(p.queryId)) byLine.set(p.queryId, []);
    byLine.get(p.queryId).push(p);
  }
  const batches = [];
  for (const [queryId, own] of byLine) {
    const rejected = queryId
      ? await until(state, listRejectedTexts(input.siteId, queryId, cookieHeader))
      : [];
    const line = linesById.get(queryId)?.text ?? "the conversations the marketer listens for";
    const judgeCtx = { line, siteContext, rejected };
    for (const b of chunk(own, BATCH_SIZE)) batches.push({ judgeCtx, posts: b });
  }

  let judged = 0;
  let kept = 0;
  let cursor = 0;
  const worker = async () => {
    while (cursor < batches.length) {
      guard(state);
      const batch = batches[cursor];
      cursor += 1;
      const results = withScores(await until(state, judgeBatch(batch.posts, batch.judgeCtx, llm)));
      const fitting = results.filter((p) => p.fits && p.relevance >= minRelevance);
      const alive = new Set(await until(state, dropDead(fitting)));
      const verdicts = results.map((p) => {
        if (!fitting.includes(p)) return toVerdict(p, "dropped", "judged_off_topic");
        if (!alive.has(p)) return toVerdict(p, "dropped", "dead");
        return toVerdict(p, "to_reply");
      });
      await until(state, saveJudged(input.siteId, verdicts, cookieHeader));
      judged += results.length;
      kept += alive.size;
      for (const p of alive) {
        const stat = platformStats[p.platform];
        if (stat) stat.kept += 1;
      }
      send("judged", { judged, total: posts.length, kept });
    }
  };
  await Promise.all(Array.from({ length: Math.min(JUDGE_CONCURRENCY, batches.length) }, worker));
  return kept;
}

async function drive(jobId, input, state, emit, { providers, cookieHeader, release }) {
  const send = (event, data) => emit({ jobId, event, data });
  const finish = (event, data) => {
    release();
    send(event, data);
  };
  const target = { cookieHeader, siteId: input.siteId, purpose: "social_listening" };
  const ctx = { state, send, llm: target, providers, cookieHeader, siteId: input.siteId };
  let runId = null;
  const platformStats = {};
  const counts = { fetchedCount: 0, matchedCount: 0, keptCount: 0 };

  const finishPatch = (status, extra = {}) => {
    if (!runId) return Promise.resolve();
    return patchRun(
      input.siteId,
      runId,
      { status, finishedAt: new Date().toISOString(), ...counts, platformStats, ...extra },
      cookieHeader,
    ).catch(() => {});
  };

  try {
    const setup = await until(state, fetchListeningSetup(input.siteId, cookieHeader));
    guard(state);
    if (!input.platforms.length) {
      input.platforms = Array.isArray(setup.config.platforms) ? setup.config.platforms : [];
    }
    if (!input.platforms.length) throw new Error("Pick at least one platform.");
    const enabledLines = setup.queries.filter((q) => q?.enabled !== false);
    if (enabledLines.length === 0) throw new Error("Add a line to listen for first.");
    const siteContext = siteContextOf(setup.site);
    const run = await createRun(input.siteId, cookieHeader);
    runId = run?.id ?? null;
    guard(state);

    const lines = await searchTerms(enabledLines, siteContext, ctx);
    guard(state);
    const fetchResult = await fetchStage(input, setup, lines, ctx, platformStats, runId);
    counts.fetchedCount = fetchResult.fetched;
    guard(state);
    counts.matchedCount = await gateStage(input, ctx);
    guard(state);
    counts.keptCount = await judgeStage(input, setup, lines, siteContext, ctx, platformStats);
    guard(state);

    await finishPatch("done");
    finish("done", {
      fetched: counts.fetchedCount,
      inserted: fetchResult.inserted,
      matched: counts.matchedCount,
      kept: counts.keptCount,
      lookbackDays: fetchResult.lookbackDays,
      platforms: platformStats,
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
