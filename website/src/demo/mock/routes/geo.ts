import type { GeoCheck, GeoQuery, GeoSummary } from "@demo/lib/types";
import * as data from "../data/geo";
import { SITE_ID } from "../data/site";
import { MockHttpError, newId, now, ok, type Route } from "../core";

const MAX_QUERIES = 50;
const RECHECK_DAYS = 7;
const STEP_MS = 1800;

const state = {
  queries: data.QUERIES.map((q) => ({ ...q })) as GeoQuery[],
  seeds: new Map(data.SEEDS.map((s) => [s.id, s])),
  timers: new Map<string, ReturnType<typeof setTimeout>>(),
};

function findQuery(id: string): GeoQuery {
  const q = state.queries.find((x) => x.id === id);
  if (!q) throw new MockHttpError(404, "Not found");
  return q;
}

function summary(): GeoSummary {
  const done = state.queries.map((q) => q.latestCheck).filter((c): c is GeoCheck => c?.status === "done");
  const verdicts = (v: string) => done.filter((c) => c.verdict === v).length;
  const last = done.map((c) => c.finishedAt ?? c.startedAt).sort().pop();
  return {
    queries: state.queries.length,
    unchecked: state.queries.filter((q) => !q.latestCheck).length,
    running: state.queries.filter((q) => q.latestCheck?.status === "running").length,
    noPage: verdicts("no_page"),
    partial: verdicts("partial"),
    lowRank: verdicts("low_rank"),
    covered: verdicts("covered"),
    cited: done.filter((c) => c.aiAnswers.some((a) => a.citedUs)).length,
    lastCheckedAt: last,
  };
}

function seedFor(q: GeoQuery): data.GeoSeed {
  const seed = state.seeds.get(q.id);
  if (seed && seed.points.length > 0) return seed;
  return { ...data.FALLBACK, id: q.id, text: q.text, source: q.source, checkedDaysAgo: 0 };
}

function advance(q: GeoQuery, stage: number) {
  const check = q.latestCheck;
  if (!check || check.status !== "running") return;
  const seed = seedFor(q);
  if (stage === 1) check.progress = { stage: "question", pagesFound: seed.pages.length + 2, pagesJudged: 0, answersFetched: 0 };
  else if (stage === 2) check.progress = { ...check.progress, stage: "judge", points: seed.points.length, pagesJudged: 1, answersFetched: 1 };
  else if (stage === 3) check.progress = { ...check.progress, stage: "compare", pagesJudged: seed.pages.length + 2, answersFetched: 3 };
  else {
    q.latestCheck = { ...data.checkFrom(seed, check.startedAt, now()), id: check.id };
    state.timers.delete(q.id);
    return;
  }
  check.updatedAt = now();
  state.timers.set(q.id, setTimeout(() => advance(q, stage + 1), STEP_MS + Math.random() * 900));
}

function start(q: GeoQuery): GeoCheck {
  const check: GeoCheck = {
    id: newId("gc"),
    createdAt: now(),
    updatedAt: now(),
    siteId: SITE_ID,
    queryId: q.id,
    status: "running",
    progress: { stage: "pages", pagesJudged: 0, answersFetched: 0 },
    startedAt: now(),
    requiredPoints: [],
    pages: [],
    aiAnswers: [],
    pageAdds: [],
  };
  q.latestCheck = check;
  state.timers.set(q.id, setTimeout(() => advance(q, 1), STEP_MS));
  return check;
}

function fresh(q: GeoQuery): boolean {
  const c = q.latestCheck;
  if (!c || c.status !== "done") return false;
  return Date.now() - Date.parse(c.finishedAt ?? c.startedAt) < RECHECK_DAYS * 86_400_000;
}

export const ROUTES: Route[] = [
  ["GET", /^\/api\/v1\/geo\/queries$/, () => ok(state.queries)],
  ["GET", /^\/api\/v1\/geo\/summary$/, () => ok(summary())],
  ["GET", /^\/api\/v1\/geo\/queries\/([^/]+)$/, (m) => ok(findQuery(m[1]))],
  ["POST", /^\/api\/v1\/geo\/queries$/, (_m, _q, body) => {
    const items = (Array.isArray(body) ? body : [body]) as Array<Record<string, unknown>>;
    const texts = [...new Set(items.map((i) => String(i.text ?? "").split(/\s+/).filter(Boolean).join(" ")).filter(Boolean))];
    const added = texts.filter((t) => !state.queries.some((q) => q.text === t));
    if (state.queries.length + added.length > MAX_QUERIES) {
      throw new MockHttpError(400, `A website can track at most ${MAX_QUERIES} questions.`);
    }
    const rows = added.map((text): GeoQuery => ({
      id: newId("gq"),
      createdAt: now(),
      updatedAt: now(),
      siteId: SITE_ID,
      text,
      source: items.find((i) => i.text === text)?.source === "suggested" ? "suggested" : "user",
      enabled: true,
    }));
    state.queries.push(...rows);
    return ok(rows);
  }],
  ["DELETE", /^\/api\/v1\/geo\/queries\/([^/]+)$/, (m) => {
    findQuery(m[1]);
    clearTimeout(state.timers.get(m[1]));
    state.timers.delete(m[1]);
    state.queries = state.queries.filter((q) => q.id !== m[1]);
    return ok({ id: m[1] });
  }],
  ["POST", /^\/api\/v1\/geo\/checks$/, (_m, _q, body) => {
    const ids = Array.isArray(body.queryIds) ? body.queryIds.map(String) : null;
    const targets = ids ? ids.map(findQuery) : state.queries.filter((q) => q.enabled && !fresh(q));
    const alreadyRunning = targets.filter((q) => q.latestCheck?.status === "running").length;
    const started = targets.filter((q) => q.latestCheck?.status !== "running").map(start);
    return ok({ started, alreadyRunning });
  }],
  ["POST", /^\/api\/v1\/geo\/checks\/stop$/, () => {
    let stopped = 0;
    for (const q of state.queries) {
      if (q.latestCheck?.status !== "running") continue;
      clearTimeout(state.timers.get(q.id));
      state.timers.delete(q.id);
      q.latestCheck = { ...q.latestCheck, status: "stopped", finishedAt: now(), updatedAt: now() };
      stopped += 1;
    }
    return ok({ stopped });
  }],
];
