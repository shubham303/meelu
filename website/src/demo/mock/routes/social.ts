import type {
  SocialListeningConfig,
  SocialListeningPlatformStats,
  SocialListeningPost,
  SocialListeningQuery,
  SocialListeningReviewStatus,
  SocialListeningRun,
  SocialListeningSummary,
} from "@demo/lib/types";
import * as social from "../data/social";
import { SITE_ID } from "../data/site";
import { b, MockHttpError, newId, now, ok, paginate, type Route } from "../core";

type QueryRow = Omit<SocialListeningQuery, "found" | "kept">;

const REVIEW: SocialListeningReviewStatus[] = ["to_reply", "drafted", "replied", "skipped", "rejected"];
const DONE: SocialListeningReviewStatus[] = ["replied", "skipped", "rejected"];

const state = {
  config: { ...social.CONFIG } as SocialListeningConfig,
  queries: social.QUERIES.map((q) => ({ ...q, keywords: [...q.keywords] })) as QueryRow[],
  posts: social.POSTS.map((p) => ({ ...p })) as SocialListeningPost[],
  runs: social.RUNS.map((r) => ({ ...r })) as SocialListeningRun[],
  pool: [...social.POOL],
  extraFound: { ...social.FOUND_BEFORE_GATE } as Record<string, number>,
};

function isReview(status: string): status is SocialListeningReviewStatus {
  return (REVIEW as string[]).includes(status);
}

function queryResponse(q: QueryRow): SocialListeningQuery {
  const mine = state.posts.filter((p) => p.queryId === q.id);
  const kept = mine.filter((p) => isReview(p.status)).length;
  return { ...q, found: mine.length + (state.extraFound[q.id] ?? 0), kept };
}

function findQuery(id: string): QueryRow {
  const q = state.queries.find((x) => x.id === id);
  if (!q) throw new MockHttpError(404, "Not found");
  return q;
}

function summary(): SocialListeningSummary {
  const count = (s: string) => state.posts.filter((p) => p.status === s).length;
  const lastRun = [...state.runs].sort((a, b) => b.startedAt.localeCompare(a.startedAt))[0] ?? null;
  return {
    toReply: count("to_reply"),
    drafted: count("drafted"),
    replied: count("replied"),
    skipped: count("skipped"),
    rejected: count("rejected"),
    done: DONE.reduce((n, s) => n + count(s), 0),
    unprocessed: count("candidate") + count("matched"),
    lastRun,
  };
}

function listPosts(q: URLSearchParams) {
  const statuses = (q.get("status") ?? "").split(",").filter(Boolean);
  const platform = q.get("platform");
  const queryId = q.get("queryId");
  const runId = q.get("runId");
  const needle = (q.get("q") ?? "").trim().toLowerCase();
  const rows = state.posts
    .filter((p) => statuses.length === 0 || statuses.includes(p.status))
    .filter((p) => !platform || p.platform === platform)
    .filter((p) => !queryId || p.queryId === queryId)
    .filter((p) => !runId || p.runId === runId)
    .filter((p) => !needle || `${p.title ?? ""} ${p.text ?? ""}`.toLowerCase().includes(needle))
    .sort((a, b) => (b.postedAt ?? "").localeCompare(a.postedAt ?? "") || b.id.localeCompare(a.id));
  return paginate(rows, q);
}

function patchPost(id: string, body: Record<string, unknown>): SocialListeningPost {
  const post = state.posts.find((p) => p.id === id);
  if (!post) throw new MockHttpError(404, "Not found");
  const status = b(body, "status");
  if (status !== undefined && status !== null) {
    if (typeof status !== "string" || !isReview(status)) {
      throw new MockHttpError(400, `status must be one of ${REVIEW.join(", ")}.`);
    }
    if (!isReview(post.status)) throw new MockHttpError(409, "This post was never shown for review.");
    if (status === "replied" && post.status !== "replied") post.repliedAt = now();
    if (status !== "replied") post.repliedAt = null;
    post.status = status;
  }
  if ("replyText" in body) post.replyText = (b(body, "replyText") as string | null) ?? null;
  if ("suggestedAngle" in body) post.suggestedAngle = (b(body, "suggestedAngle") as string | null) ?? null;
  post.updatedAt = now();
  return post;
}

export const ROUTES: Route[] = [
  ["GET", /^\/api\/v1\/social-listening\/config$/, () => ok(state.config)],
  ["PUT", /^\/api\/v1\/social-listening\/config$/, (_m, _q, body) => {
    const platforms = b(body, "platforms");
    if (Array.isArray(platforms)) {
      const known = new Set(social.PLATFORMS.map((p) => p.id));
      const unknown = platforms.filter((p) => !known.has(String(p)));
      if (unknown.length) throw new MockHttpError(400, `Unknown platform: ${unknown.join(", ")}.`);
      state.config.platforms = [...new Set(platforms.map(String))];
    }
    state.config.updatedAt = now();
    return ok(state.config);
  }],
  ["GET", /^\/api\/v1\/social-listening\/queries$/, () => ok(state.queries.map(queryResponse))],
  ["POST", /^\/api\/v1\/social-listening\/queries$/, (_m, _q, body) => {
    const items = (Array.isArray(body) ? body : [body]) as Array<Record<string, unknown>>;
    const deduped = new Map<string, Record<string, unknown>>();
    for (const item of items) {
      const text = String(item.text ?? "").split(/\s+/).filter(Boolean).join(" ");
      if (text) deduped.set(text, item);
    }
    const existing = state.queries.filter((q) => deduped.has(q.text));
    const added = deduped.size - existing.length;
    if (added && state.queries.length + added > social.MAX_LINES) {
      throw new MockHttpError(400, `A website can listen for at most ${social.MAX_LINES} lines. Remove or edit a line before adding another.`);
    }
    for (const [text, item] of deduped) {
      const found = state.queries.find((q) => q.text === text);
      if (found) {
        Object.assign(found, { enabled: item.enabled !== false, updatedAt: now() });
        continue;
      }
      state.queries.push({
        id: newId("slq"),
        createdAt: now(),
        updatedAt: now(),
        siteId: SITE_ID,
        text,
        enabled: item.enabled !== false,
        source: item.source === "suggested" ? "suggested" : "user",
        keywords: [],
        embedded: true,
      });
    }
    return ok({ inserted: added, updated: existing.length });
  }],
  ["PATCH", /^\/api\/v1\/social-listening\/queries\/([^/]+)$/, (m, _q, body) => {
    const q = findQuery(m[1]);
    if (typeof body.enabled === "boolean") q.enabled = body.enabled;
    if (Array.isArray(body.keywords)) q.keywords = body.keywords.map(String);
    if (typeof body.text === "string") {
      const text = body.text.split(/\s+/).filter(Boolean).join(" ");
      if (!text) throw new MockHttpError(400, "text must not be empty.");
      if (text !== q.text) Object.assign(q, { text, keywords: [] });
    }
    q.updatedAt = now();
    return ok(queryResponse(q));
  }],
  ["DELETE", /^\/api\/v1\/social-listening\/queries\/([^/]+)$/, (m) => {
    findQuery(m[1]);
    state.queries = state.queries.filter((q) => q.id !== m[1]);
    return ok({ id: m[1] });
  }],
  ["GET", /^\/api\/v1\/social-listening\/summary$/, () => ok(summary())],
  ["GET", /^\/api\/v1\/social-listening\/runs$/, (_m, q) =>
    paginate([...state.runs].sort((a, b) => b.startedAt.localeCompare(a.startedAt)), q)],
  ["GET", /^\/api\/v1\/social-listening\/runs\/([^/]+)$/, (m) => {
    const run = state.runs.find((r) => r.id === m[1]);
    if (!run) throw new MockHttpError(404, "Not found");
    return ok(run);
  }],
  ["GET", /^\/api\/v1\/social-listening\/posts$/, (_m, q) => listPosts(q)],
  ["GET", /^\/api\/v1\/social-listening\/posts\/([^/]+)$/, (m) => {
    const post = state.posts.find((p) => p.id === m[1]);
    if (!post) throw new MockHttpError(404, "Not found");
    return ok(post);
  }],
  ["PATCH", /^\/api\/v1\/social-listening\/posts\/([^/]+)$/, (m, _q, body) => ok(patchPost(m[1], body))],
];

export interface SocialRunEvent {
  jobId: string;
  event: string;
  data: Record<string, unknown>;
}

export interface SocialRunSnapshot {
  jobId: string | null;
  stopping: boolean;
  startedAt: number | null;
  progress: Array<{ event: string; data: Record<string, unknown> }>;
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

const VENDOR_BASE: Record<string, number> = {
  reddit: 46, hackernews: 17, x: 29, linkedin: 8, bluesky: 12, stackexchange: 9, devto: 6, github: 5, facebook: 7,
};

async function drive(jobId: string, job: Job, platforms: string[], emit: (e: SocialRunEvent) => void) {
  const send = (event: string, data: Record<string, unknown>) => {
    job.progress.push({ event, data });
    emit({ jobId, event, data });
  };
  const step = async (ms: number) => {
    await sleep(ms);
    if (job.stopped) throw new Stopped();
  };
  const finish = (event: string, data: Record<string, unknown>) => {
    jobs.delete(jobId);
    if (jobBySite.get(job.siteId) === jobId) jobBySite.delete(job.siteId);
    emit({ jobId, event, data });
  };

  const lines = state.queries.filter((q) => q.enabled);
  const run: SocialListeningRun = {
    id: newId("slr"),
    createdAt: now(),
    updatedAt: now(),
    siteId: SITE_ID,
    status: "running",
    startedAt: now(),
    finishedAt: null,
    fetchedCount: 0,
    matchedCount: 0,
    keptCount: 0,
    platformStats: {},
    error: null,
  };
  state.runs.push(run);
  const close = (status: SocialListeningRun["status"]) => {
    Object.assign(run, { status, finishedAt: now(), updatedAt: now() });
  };

  try {
    send("stage", { stage: "terms" });
    await step(1100);
    for (const q of lines) {
      if (q.keywords.length === 0) q.keywords = keywordsFor(q.text);
    }
    send("terms", { lines: lines.length, phrases: new Set(lines.flatMap((q) => q.keywords)).size });
    await step(500);

    send("stage", { stage: "searching" });
    for (const p of platforms) {
      run.platformStats[p] = { status: "running" };
      send("platform", { platform: p, status: "fetching" });
    }
    const stats: Record<string, SocialListeningPlatformStats> = {};
    for (const p of platforms) {
      await step(700 + Math.random() * 700);
      const fromVendor = Math.round((VENDOR_BASE[p] ?? 6) * (0.8 + Math.random() * 0.5));
      const fromDatabase = Math.round(fromVendor * (0.08 + Math.random() * 0.1));
      stats[p] = {
        status: "done",
        keywords: lines.length * 2,
        fromVendor,
        fromDatabase,
        candidates: fromVendor + fromDatabase,
        failedKeywords: [],
      };
      run.platformStats[p] = stats[p];
      send("platform", { platform: p, status: "done", fromVendor, fromDatabase });
    }
    const fetched = Object.values(stats).reduce((n, s) => n + (s.fromVendor ?? 0), 0);
    const inserted = Object.values(stats).reduce((n, s) => n + (s.candidates ?? 0), 0);
    run.fetchedCount = fetched;
    send("saved", { fetched, inserted });
    await step(400);

    send("stage", { stage: "meaning" });
    const lineIds = new Set(lines.map((q) => q.id));
    const picks = state.pool
      .filter((s) => lineIds.has(s.query) && platforms.includes(s.platform))
      .slice(0, 3);
    const matched = picks.length === 0 ? Math.min(inserted, 4) : Math.min(inserted, picks.length * 3 + 2);
    let pending = inserted;
    let kept = 0;
    for (const share of [0.45, 0.8, 1]) {
      await step(650);
      pending = Math.round(inserted * (1 - share));
      kept = Math.round(matched * share);
      send("gate", { pending, kept, dropped: inserted - pending - kept });
    }
    run.matchedCount = matched;
    for (const q of lines) state.extraFound[q.id] = (state.extraFound[q.id] ?? 0) + Math.round(matched / lines.length);

    send("stage", { stage: "judging" });
    send("judged", { judged: 0, total: matched, kept: 0 });
    let judged = 0;
    let keptPosts = 0;
    const perBatch = Math.max(1, Math.ceil(matched / 4));
    while (judged < matched) {
      await step(900);
      judged = Math.min(matched, judged + perBatch);
      const due = Math.min(picks.length, Math.round((judged / matched) * picks.length));
      while (keptPosts < due) {
        const seed = picks[keptPosts];
        state.pool = state.pool.filter((s) => s !== seed);
        state.posts.push(social.postFrom(seed, run.id, Date.now()));
        keptPosts += 1;
      }
      run.keptCount = keptPosts;
      send("judged", { judged, total: matched, kept: keptPosts });
    }

    close("done");
    finish("done", { fetched, inserted, matched, kept: keptPosts, platforms: stats });
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

function keywordsFor(text: string): string[] {
  const words = text.toLowerCase().replace(/[^a-z0-9 ]/g, "").split(" ").filter((w) => w.length > 3);
  return [words.slice(0, 3).join(" "), words.slice(-3).join(" ")];
}

export const socialRun = {
  platforms(): { platforms: social.PlatformInfo[] } {
    return { platforms: social.PLATFORMS.map((p) => ({ ...p })) };
  },
  start(
    payload: { siteId: string; platforms?: string[] },
    emit: (e: SocialRunEvent) => void,
  ): { jobId?: string; error?: string } {
    const { siteId } = payload;
    if (!siteId) return { error: "Pick a website first." };
    const active = jobBySite.get(siteId);
    if (active) return { error: "A run is already going for this site.", jobId: active };
    const platforms = payload.platforms?.length ? payload.platforms : state.config.platforms;
    if (platforms.length === 0) return { error: "Pick at least one platform." };
    if (!state.queries.some((q) => q.enabled)) return { error: "Add a line to listen for first." };
    const jobId = newId("sljob");
    const job: Job = { siteId, stopped: false, startedAt: Date.now(), progress: [] };
    jobs.set(jobId, job);
    jobBySite.set(siteId, jobId);
    void drive(jobId, job, platforms, emit);
    return { jobId };
  },
  stop(jobId: string): { stopping: boolean } {
    const job = jobs.get(jobId);
    if (!job) return { stopping: false };
    job.stopped = true;
    return { stopping: true };
  },
  active(siteId: string): SocialRunSnapshot {
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
