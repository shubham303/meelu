import { randomUUID } from "node:crypto";
import { BATCH_SIZE, classifyBatch } from "./classify.js";
import { expandQuery } from "./expand.js";
import { dropDead, withinAge } from "./filters.js";
import { withScores } from "./rank.js";
import {
  createRun,
  fetchListeningSetup,
  fromApiPost,
  gatePosts,
  knownPostUrls,
  latestSuccessfulRun,
  listMatchedPosts,
  patchQuery,
  patchRun,
  saveClassified,
  savePosts,
  toFetchedPost,
  toVerdict,
} from "./store.js";

const KEEP_THRESHOLD = 0.4;
const CLASSIFY_CONCURRENCY = 3;
const GATE_POLL_MS = 3000;
const GATE_TIMEOUT_MS = 10 * 60 * 1000;

const running = new Map();

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

export function startSignalsSearch(payload, emit, { providers, llm, cookieHeader = "" }) {
  const { siteId = null, platforms = [] } = payload;
  if (!siteId) return { error: "Pick a website first." };
  const jobId = randomUUID();
  const state = { stopped: false };
  running.set(jobId, state);
  const input = { siteId, platforms: Array.isArray(platforms) ? platforms : [] };
  void drive(jobId, input, state, emit, { providers, llm, cookieHeader }).finally(() =>
    running.delete(jobId),
  );
  return { jobId };
}

export function stopSignalsSearch(jobId) {
  const state = running.get(jobId);
  if (!state) return false;
  state.stopped = true;
  return true;
}

function guard(state) {
  if (state.stopped) throw new Stopped();
}

function enabled(rows) {
  return rows.filter((r) => r?.enabled !== false);
}

function matched(post, terms) {
  const hay = `${post.title ?? ""} ${post.text ?? ""}`.toLowerCase();
  return terms.filter((t) => hay.includes(t.toLowerCase()));
}

async function expandQueries(queries, state, send, llm, siteId, cookieHeader) {
  const out = [];
  for (const q of queries) {
    const keywords = Array.isArray(q.keywords) ? q.keywords.filter(Boolean) : [];
    if (keywords.length > 0) {
      out.push({ ...q, keywords, negativeKeywords: q.negativeKeywords ?? [] });
      continue;
    }
    guard(state);
    send("stage", { stage: "expanding", query: q.text });
    const expansion = await expandQuery({ mode: "topic", topic: q.text, siteContext: "" }, llm);
    const patched = await patchQuery(
      siteId,
      q.id,
      { keywords: expansion.keywords, negativeKeywords: expansion.negativeKeywords },
      cookieHeader,
    );
    out.push({ ...q, ...patched });
  }
  return out;
}

function buildGroups(queries, targets) {
  const names = (kind) =>
    enabled(targets)
      .filter((t) => t.kind === kind)
      .map((t) => String(t.name ?? "").trim())
      .filter(Boolean);
  const groups = [];
  const brands = names("brand");
  const competitors = names("competitor");
  if (brands.length) {
    groups.push({ kind: "brand", queryId: null, keywords: brands, negativeKeywords: [] });
  }
  if (competitors.length) {
    groups.push({ kind: "competitor", queryId: null, keywords: competitors, negativeKeywords: [] });
  }
  for (const q of queries) {
    groups.push({
      kind: "topic",
      queryId: q.id,
      keywords: q.keywords,
      negativeKeywords: q.negativeKeywords ?? [],
    });
  }
  return groups;
}

async function fetchAll(input, groups, perGroupLimit, since, send, providers, statsRef) {
  const fetched = [];
  await Promise.allSettled(
    input.platforms.map(async (platform) => {
      send("platform", { platform, status: "fetching" });
      const stat = { fetched: 0, kept: 0 };
      statsRef[platform] = stat;
      let count = 0;
      let lastError = null;
      for (const group of groups) {
        try {
          const posts = await providers.listening.searchPlatform({
            platform,
            keywords: group.keywords,
            since,
            limit: perGroupLimit(group),
            siteId: input.siteId,
          });
          for (const p of posts) fetched.push({ ...p, kind: group.kind, queryId: group.queryId });
          count += posts.length;
        } catch (err) {
          lastError = err instanceof Error ? err.message : String(err);
        }
      }
      stat.fetched = count;
      if (lastError && count === 0) {
        stat.error = lastError;
        send("platform", { platform, status: "error", error: lastError });
      } else {
        if (lastError) stat.error = lastError;
        send("platform", { platform, status: "done", count });
      }
    }),
  );
  return fetched;
}

function dedupeByUrl(posts) {
  const seen = new Map();
  for (const p of posts) {
    if (!seen.has(p.url)) seen.set(p.url, p);
  }
  return [...seen.values()];
}

function mergeByUrl(posts) {
  const priority = { brand: 0, competitor: 1, topic: 2 };
  const ordered = [...posts].sort((a, b) => (priority[a.kind] ?? 3) - (priority[b.kind] ?? 3));
  return dedupeByUrl(ordered);
}

function negativeHit(post, groups) {
  const group = groups.find((g) => g.kind === post.kind && g.queryId === post.queryId);
  const hay = `${post.title ?? ""} ${post.text ?? ""}`.toLowerCase();
  return (group?.negativeKeywords ?? []).find((k) => hay.includes(String(k).toLowerCase())) ?? null;
}

async function fetchStage(input, setup, queries, state, send, providers, platformStats, cookieHeader, runId) {
  const config = setup.config;
  const groups = buildGroups(queries, setup.targets);
  if (groups.length === 0) return 0;

  let since = null;
  const lastDone = await latestSuccessfulRun(input.siteId, cookieHeader).catch(() => null);
  const startedAt = Date.parse(lastDone?.startedAt ?? "");
  if (Number.isFinite(startedAt)) since = new Date(startedAt - 86_400_000).toISOString();
  else if (Number(config.maxAgeDays) > 0) {
    since = new Date(Date.now() - Number(config.maxAgeDays) * 86_400_000).toISOString();
  }
  guard(state);

  const resultsPerKeyword = Math.max(5, Number(config.resultsPerKeyword) || 50);
  const perGroupLimit = (group) => Math.min(resultsPerKeyword * group.keywords.length, 100);

  send("stage", { stage: "fetching" });
  const fetched = await fetchAll(input, groups, perGroupLimit, since, send, providers, platformStats);
  guard(state);

  const targetNames = enabled(setup.targets).map((t) => t.name);
  let posts = mergeByUrl(fetched).map((p) => ({ ...p, matchedTargets: matched(p, targetNames) }));
  const known = new Set(await knownPostUrls(input.siteId, posts.map((p) => p.url), cookieHeader));
  posts = posts.filter((p) => {
    if (!known.has(p.url)) return true;
    const stat = platformStats[p.platform];
    if (stat) stat.known = (stat.known ?? 0) + 1;
    return false;
  });
  guard(state);

  const fresh = new Set(withinAge(posts, config.maxAgeDays).map((p) => p.url));
  const payload = posts.map((p) => {
    if (!fresh.has(p.url)) return toFetchedPost(p, "filtered", "Older than the age limit");
    const hit = negativeHit(p, groups);
    if (hit) return toFetchedPost(p, "filtered", `Mentions "${hit}"`);
    return toFetchedPost(p);
  });
  for (const batch of chunk(payload, 200)) {
    await savePosts(input.siteId, runId, batch, cookieHeader);
    guard(state);
  }
  send("saved", { fetched: fetched.length, new: payload.length });
  return fetched.length;
}

async function gateStage(input, state, send, cookieHeader) {
  send("stage", { stage: "gating" });
  const startedAt = Date.now();
  let result = await gatePosts(input.siteId, cookieHeader);
  send("gate", result);
  while (result.pending > 0 && Date.now() - startedAt < GATE_TIMEOUT_MS) {
    guard(state);
    await sleep(GATE_POLL_MS);
    guard(state);
    result = await gatePosts(input.siteId, cookieHeader);
    send("gate", result);
  }
  return result;
}

function classifyContext(post, queriesById, setup) {
  if (post.kind === "topic") {
    const query = queriesById.get(post.queryId);
    return { mode: "topic", topic: query?.text ?? "the listening queries", siteContext: "" };
  }
  const names = enabled(setup.targets)
    .filter((t) => t.kind === post.kind)
    .map((t) => t.name);
  return { mode: "brand", topic: names.join(", "), siteContext: "" };
}

async function classifyStage(input, setup, queries, state, send, llm, cookieHeader, platformStats) {
  const rows = await listMatchedPosts(input.siteId, cookieHeader);
  const posts = rows.map(fromApiPost);
  send("stage", { stage: "classifying", total: posts.length });
  if (posts.length === 0) return 0;

  const queriesById = new Map(queries.map((q) => [q.id, q]));
  const keepThreshold = Number.isFinite(Number(setup.config.minRelevance))
    ? Number(setup.config.minRelevance)
    : KEEP_THRESHOLD;
  const byContext = new Map();
  for (const p of posts) {
    const key = `${p.kind}:${p.queryId ?? ""}`;
    if (!byContext.has(key)) byContext.set(key, { ctx: classifyContext(p, queriesById, setup), posts: [] });
    byContext.get(key).posts.push(p);
  }
  const batches = [];
  for (const { ctx, posts: own } of byContext.values()) {
    for (const b of chunk(own, BATCH_SIZE)) batches.push({ ctx, posts: b });
  }

  let judged = 0;
  let kept = 0;
  let cursor = 0;
  const worker = async () => {
    while (cursor < batches.length) {
      guard(state);
      const batch = batches[cursor];
      cursor += 1;
      const results = withScores(await classifyBatch(batch.posts, batch.ctx, llm), batch.ctx.mode);
      let keepers = results.filter((p) => (p.relevanceScore ?? 0) >= keepThreshold);
      if (setup.config.dropDeadPosts !== false && keepers.length > 0) {
        const alive = new Set((await dropDead(keepers)).map((p) => p.url));
        keepers = keepers.filter((p) => alive.has(p.url));
      }
      const keptUrls = new Set(keepers.map((p) => p.url));
      const verdicts = results.map((p) => toVerdict(p, keptUrls.has(p.url) ? "needs_reply" : "filtered"));
      await saveClassified(input.siteId, verdicts, cookieHeader);
      judged += results.length;
      kept += keepers.length;
      for (const p of keepers) {
        const stat = platformStats[p.platform];
        if (stat) stat.kept += 1;
      }
      send("classified", { judged, total: posts.length, kept });
    }
  };
  await Promise.all(Array.from({ length: Math.min(CLASSIFY_CONCURRENCY, batches.length) }, worker));
  return kept;
}

async function drive(jobId, input, state, emit, { providers, llm, cookieHeader }) {
  const send = (event, data) => emit({ jobId, event, data });
  let runId = null;
  const platformStats = {};
  let fetchedCount = 0;
  let keptCount = 0;

  const finishPatch = (status, extra = {}) => {
    if (!runId) return Promise.resolve();
    return patchRun(
      input.siteId,
      runId,
      { status, finishedAt: new Date().toISOString(), fetchedCount, keptCount, platformStats, ...extra },
      cookieHeader,
    ).catch(() => {});
  };

  try {
    const setup = await fetchListeningSetup(input.siteId, cookieHeader);
    guard(state);
    if (!input.platforms.length) {
      input.platforms = Array.isArray(setup.config.platforms) ? setup.config.platforms : [];
    }
    if (!input.platforms.length) throw new Error("Pick at least one platform.");
    const hasWork =
      enabled(setup.queries).length > 0 || enabled(setup.targets).length > 0;
    if (!hasWork) throw new Error("Nothing to search — add a query or a brand to watch first.");
    const run = await createRun(input.siteId, cookieHeader);
    runId = run?.id ?? null;
    guard(state);

    const queries = await expandQueries(
      enabled(setup.queries),
      state,
      send,
      llm,
      input.siteId,
      cookieHeader,
    );
    guard(state);

    fetchedCount = await fetchStage(
      input,
      setup,
      queries,
      state,
      send,
      providers,
      platformStats,
      cookieHeader,
      runId,
    );
    guard(state);

    await gateStage(input, state, send, cookieHeader);
    guard(state);

    keptCount = await classifyStage(
      input,
      setup,
      queries,
      state,
      send,
      llm,
      cookieHeader,
      platformStats,
    );
    guard(state);

    send("done", { fetched: fetchedCount, kept: keptCount });
    await finishPatch("done");
  } catch (err) {
    if (err instanceof Stopped) {
      send("stopped", {});
      await finishPatch("stopped");
      return;
    }
    const message = err instanceof Error ? err.message : String(err);
    send("error", { message });
    await finishPatch("error", { error: message });
  }
}
