import {
  clickstreamVolumes,
  keywordSuggestions,
  organicTop10,
  type Spend,
  type Suggestion,
} from "./dataforseo";
import { CLUSTER_LIMITS, LOCATIONS, SERP_DIFFERENT, SERP_SAME } from "./limits";
import { decide, llmModel, structuredChat, type ChoiceQuestion } from "./openrouter";
import { serpOverlap } from "./serp";
import type {
  ClusterError,
  ClusterFlag,
  ClusterKeyword,
  ClusterRunInput,
  ClusterRunResult,
  DroppedKeyword,
  KeywordCluster,
  SearchIntent,
  SerpPair,
  SerpResult,
} from "./types";

export const RUN_STEPS = 5;

const RELEVANCE_BATCH = 25;
const IRRELEVANT_AT = 0.6;
const LLM_CONCURRENCY = 8;
const SERP_CONCURRENCY = 10;
const SPLIT_BATCH_KEYWORDS = 60;
const SPLIT_BATCH_GROUPS = 10;
const OVERSTATED_BELOW = 0.5;

type RunOptions = {
  signal?: AbortSignal;
  onPhase: (message: string, step: number) => void;
  dailyRuns: { used: number; limit: number };
};

export type RunOutcome = { ok: true; result: ClusterRunResult } | { ok: false; error: ClusterError };

async function mapLimit<T, R>(items: T[], limit: number, fn: (item: T) => Promise<R>) {
  const results: PromiseSettledResult<R>[] = new Array(items.length);
  let next = 0;
  async function worker() {
    while (next < items.length) {
      const index = next++;
      try {
        results[index] = { status: "fulfilled", value: await fn(items[index]) };
      } catch (reason) {
        results[index] = { status: "rejected", reason };
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
  return results;
}

function chunk<T>(items: T[], size: number): T[][] {
  const out: T[][] = [];
  for (let i = 0; i < items.length; i += size) out.push(items.slice(i, i + size));
  return out;
}

function reason(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function relevanceQuestion(keyword: string): ChoiceQuestion {
  return {
    type: "choice",
    instructions: `Is the search keyword "${keyword}" about the same subject as the seed keyword? Related means it is the seed itself, a narrower or broader version of it, a question about it, or a variant built from the seed's main words, even when that variant wants something different.`,
    criteria: {
      yes: "related: the keyword is about the seed's subject or is a close variant of the seed's words",
      no: "unrelated: the keyword is about a different subject, product or tool, and shares at most a word with the seed",
    },
  };
}

function wordsOf(phrase: string): Set<string> {
  return new Set(
    phrase
      .toLowerCase()
      .split(/[^a-z0-9]+/)
      .filter(Boolean)
      .map((w) => (w.length > 3 && w.endsWith("s") && !w.endsWith("ss") ? w.slice(0, -1) : w)),
  );
}

function containsAll(words: Set<string>, required: Set<string>): boolean {
  for (const w of required) if (!words.has(w)) return false;
  return true;
}

function noProbability(answer: { choice?: string; probabilities?: Record<string, number> } | undefined) {
  if (!answer) return 0;
  const p = answer.probabilities?.no;
  if (typeof p === "number") return p;
  return answer.choice === "no" ? 1 : 0;
}

const SPLIT_SYSTEM = `You split groups of search keywords into distinct searcher intents for SEO page planning.
You get several core-keyword groups. Split each one on its own and never move a keyword into another core group. Return one entry per core_keyword, spelled exactly as given.
Two keywords belong in the same intent only when one page could fully satisfy both searchers.
Separate keywords that want a different product, attribute, colour, material or problem, even when they share every word. Word order matters: "blue light glasses" (glasses that filter blue light) and "light blue glasses" (glasses coloured light blue) are different intents.
Separate a question about a topic from a search to buy, when one page could not serve both.
Plain modifiers one page normally covers (best, buy, cheap, online, singular or plural, filler words, punctuation) do not need their own intent unless they change what the searcher wants.
Over-splitting is acceptable. Merging two different intents is not.
Put every keyword of a core group in exactly one of its intents, spelled exactly as given.
label: a short page topic, two to six words. intent: one sentence saying what the searcher wants.`;

const INTENT_GROUP_SCHEMA = {
  type: "object",
  additionalProperties: false,
  required: ["label", "intent", "keywords"],
  properties: {
    label: { type: "string" },
    intent: { type: "string" },
    keywords: { type: "array", items: { type: "string" } },
  },
};

const SPLIT_SCHEMA = {
  type: "object",
  additionalProperties: false,
  required: ["cores"],
  properties: {
    cores: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        required: ["core_keyword", "intents"],
        properties: {
          core_keyword: { type: "string" },
          intents: { type: "array", items: INTENT_GROUP_SCHEMA },
        },
      },
    },
  },
};

type SplitReply = {
  cores: Array<{ core_keyword: string; intents: IntentGroup[] }>;
};

function packBatches<T extends [string, unknown[]]>(groups: T[]): T[][] {
  const batches: T[][] = [];
  let current: T[] = [];
  let size = 0;
  for (const group of groups) {
    const n = group[1].length;
    if (current.length > 0 && (size + n > SPLIT_BATCH_KEYWORDS || current.length >= SPLIT_BATCH_GROUPS)) {
      batches.push(current);
      current = [];
      size = 0;
    }
    current.push(group);
    size += n;
  }
  if (current.length > 0) batches.push(current);
  return batches;
}

type IntentGroup = { label: string; intent: string; keywords: string[] };

function assignGroups(keywords: string[], groups: IntentGroup[]): IntentGroup[] {
  const known = new Set(keywords);
  const placed = new Set<string>();
  const out: IntentGroup[] = [];
  for (const group of groups) {
    const members = group.keywords
      .map((k) => k.trim().toLowerCase())
      .filter((k) => known.has(k) && !placed.has(k));
    members.forEach((k) => placed.add(k));
    if (members.length > 0) {
      out.push({ label: group.label.trim() || members[0], intent: group.intent.trim(), keywords: members });
    }
  }
  for (const keyword of keywords) {
    if (!placed.has(keyword)) out.push({ label: keyword, intent: "", keywords: [keyword] });
  }
  return out;
}

function majorityIntent(keywords: ClusterKeyword[]): SearchIntent | null {
  const weight = new Map<SearchIntent, number>();
  for (const k of keywords) {
    if (!k.searchIntent) continue;
    weight.set(k.searchIntent, (weight.get(k.searchIntent) ?? 0) + Math.max(1, k.adsVolume));
  }
  let best: SearchIntent | null = null;
  let bestWeight = -1;
  for (const [intent, w] of weight) {
    if (w > bestWeight) {
      best = intent;
      bestWeight = w;
    }
  }
  return best;
}

function mergeKey(k: { adsVolume: number; cpc: number | null; coreKeyword: string }): string | null {
  if (k.adsVolume <= 0) return null;
  return `${k.coreKeyword}|${k.adsVolume}|${k.cpc ?? "none"}`;
}

function formatNumber(n: number): string {
  return n.toLocaleString("en-US");
}

export function cleanSeeds(raw: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const seed of raw) {
    const clean = seed.replace(/\s+/g, " ").trim().toLowerCase().slice(0, CLUSTER_LIMITS.maxSeedChars);
    if (clean && !seen.has(clean)) {
      seen.add(clean);
      out.push(clean);
    }
  }
  return out;
}

export async function runClustering(input: ClusterRunInput, options: RunOptions): Promise<RunOutcome> {
  const started = Date.now();
  const spend: Spend = { dataforseo: 0, openrouter: 0 };
  const notes: string[] = [];
  const dropped: DroppedKeyword[] = [];
  const locale = { locationCode: input.locationCode, languageCode: input.languageCode };
  const { signal } = options;

  const seedsUsed = input.seeds.slice(0, CLUSTER_LIMITS.maxSeeds);

  options.onPhase(
    `Expanding ${seedsUsed.length} seed${seedsUsed.length === 1 ? "" : "s"} into related searches`,
    1,
  );
  const expanded = await Promise.allSettled(
    seedsUsed.map((seed) =>
      keywordSuggestions(
        seed,
        locale,
        { limit: CLUSTER_LIMITS.suggestionsPerSeed, minVolume: input.minVolume },
        spend,
        signal,
      ),
    ),
  );

  const found = new Map<string, Suggestion>();
  const seedOf = new Map<string, string>();
  let failedSeeds = 0;
  expanded.forEach((outcome, i) => {
    if (outcome.status === "rejected") {
      failedSeeds += 1;
      notes.push(`Could not expand "${seedsUsed[i]}": ${reason(outcome.reason)}`);
      return;
    }
    for (const suggestion of outcome.value) {
      if (!seedOf.has(suggestion.keyword)) seedOf.set(suggestion.keyword, seedsUsed[i]);
      const existing = found.get(suggestion.keyword);
      if (!existing || (!existing.coreKeyword && suggestion.coreKeyword)) {
        found.set(suggestion.keyword, suggestion);
      }
    }
  });

  if (failedSeeds === seedsUsed.length) {
    return {
      ok: false,
      error: {
        code: "provider-failed",
        message: "The keyword data provider did not answer.",
        hint: notes[0],
      },
    };
  }

  const keywordsFound = found.size;
  const seedSet = new Set(seedsUsed);
  let pool = [...found.values()].filter((s) => {
    if (s.adsVolume >= input.minVolume) return true;
    dropped.push({ keyword: s.keyword, adsVolume: s.adsVolume, reason: "low-volume" });
    return false;
  });
  const droppedLowVolume = dropped.length;

  pool.sort((a, b) => b.adsVolume - a.adsVolume);
  const overCap = pool.slice(CLUSTER_LIMITS.maxKeywords);
  pool = pool.slice(0, CLUSTER_LIMITS.maxKeywords);
  for (const s of overCap) dropped.push({ keyword: s.keyword, adsVolume: s.adsVolume, reason: "over-cap" });

  if (pool.length === 0) {
    return {
      ok: false,
      error: {
        code: "no-keywords",
        message: `No related keywords reached ${formatNumber(input.minVolume)} searches a month.`,
        hint: "Lower the minimum volume, try broader seeds, or check the country and language.",
      },
    };
  }

  options.onPhase("Checking keywords that look different from their seed", 2);
  const seedBatches: { seed: string; items: Suggestion[] }[] = [];
  for (const seed of seedsUsed) {
    const seedWords = wordsOf(seed);
    const ofSeed = pool.filter(
      (s) => seedOf.get(s.keyword) === seed && !containsAll(wordsOf(s.keyword), seedWords),
    );
    for (const items of chunk(ofSeed, RELEVANCE_BATCH)) seedBatches.push({ seed, items });
  }
  const answers = await mapLimit(seedBatches, 4, async ({ seed, items }) => {
    const questions: Record<string, ChoiceQuestion> = {};
    items.forEach((s, i) => {
      questions[`k${i}`] = relevanceQuestion(s.keyword);
    });
    return decide({ seed_keyword: seed }, questions, spend, signal);
  });
  const irrelevant = new Map<string, number>();
  let failedBatches = 0;
  answers.forEach((outcome, b) => {
    if (outcome.status === "rejected") {
      failedBatches += 1;
      return;
    }
    seedBatches[b].items.forEach((s, i) => {
      const pNo = noProbability(outcome.value[`k${i}`]);
      if (pNo >= IRRELEVANT_AT && !seedSet.has(s.keyword)) irrelevant.set(s.keyword, pNo);
    });
  });
  if (failedBatches > 0) {
    notes.push(
      `The seed relevance check failed for ${failedBatches} of ${seedBatches.length} batches; those keywords were kept unchecked.`,
    );
  }
  pool = pool.filter((s) => {
    const pNo = irrelevant.get(s.keyword);
    if (pNo === undefined) return true;
    dropped.push({ keyword: s.keyword, adsVolume: s.adsVolume, reason: "irrelevant", confidence: pNo });
    return false;
  });
  const droppedIrrelevant = irrelevant.size;

  if (pool.length === 0) {
    return {
      ok: false,
      error: {
        code: "no-keywords",
        message: "Every related keyword was judged unrelated to its seed.",
        hint: "Try a broader or more common seed keyword.",
      },
    };
  }

  options.onPhase("Grouping by core keyword and splitting each group by intent", 3);

  const clickstreamPromise = clickstreamVolumes(
    pool.map((s) => s.keyword),
    locale,
    spend,
    signal,
  ).then(
    (volumes) => volumes,
    (error: unknown) => {
      notes.push(`Clickstream volumes were not available: ${reason(error)}`);
      return null;
    },
  );

  const coreGroups = new Map<string, Suggestion[]>();
  for (const s of pool) {
    const core = s.coreKeyword ?? s.keyword;
    const members = coreGroups.get(core) ?? [];
    members.push(s);
    coreGroups.set(core, members);
  }

  const groupVolume = (members: Suggestion[]) => Math.max(...members.map((m) => m.adsVolume));
  const orderedGroups = [...coreGroups.entries()].sort((a, b) => groupVolume(b[1]) - groupVolume(a[1]));
  const splittable = orderedGroups.filter(([, members]) => members.length > 1);
  const toSplit = splittable.slice(0, CLUSTER_LIMITS.maxSplitGroups);
  const toSplitCores = new Set(toSplit.map(([core]) => core));

  const batches = packBatches(toSplit);
  const replies = await mapLimit(batches, LLM_CONCURRENCY, (batch) =>
    structuredChat<SplitReply>(
      SPLIT_SYSTEM,
      JSON.stringify({
        groups: batch.map(([core, members]) => ({
          core_keyword: core,
          keywords: members.map((m) => m.keyword),
        })),
      }),
      "intent_split",
      SPLIT_SCHEMA,
      spend,
      signal,
    ),
  );

  const splitByCore = new Map<string, IntentGroup[] | null>();
  let failedSplits = 0;
  batches.forEach((batch, b) => {
    const outcome = replies[b];
    const byCore = new Map<string, IntentGroup[]>();
    if (outcome.status === "fulfilled" && Array.isArray(outcome.value?.cores)) {
      for (const entry of outcome.value.cores) {
        if (typeof entry?.core_keyword === "string" && Array.isArray(entry.intents)) {
          byCore.set(entry.core_keyword.trim().toLowerCase(), entry.intents);
        }
      }
    } else if (outcome.status === "rejected") {
      console.error("keyword-clusters: split failed", reason(outcome.reason));
    }
    for (const [core, members] of batch) {
      const intents = byCore.get(core);
      if (intents) {
        splitByCore.set(core, assignGroups(members.map((m) => m.keyword), intents));
      } else {
        failedSplits += 1;
        splitByCore.set(core, null);
      }
    }
  });
  if (failedSplits > 0) {
    notes.push(`The model could not split ${failedSplits} group${failedSplits === 1 ? "" : "s"}; they are shown whole and flagged.`);
  }

  const clickstream = await clickstreamPromise;
  const bySuggestion = new Map(pool.map((s) => [s.keyword, s]));

  const keywordOf = (keyword: string): ClusterKeyword => {
    const s = bySuggestion.get(keyword)!;
    return {
      keyword,
      coreKeyword: s.coreKeyword ?? s.keyword,
      adsVolume: s.adsVolume,
      clickstreamVolume: clickstream ? (clickstream.get(keyword) ?? 0) : null,
      cpc: s.cpc,
      searchIntent: s.searchIntent,
      sharedVolumeWith: [],
    };
  };

  const volumeOf = (k: ClusterKeyword) => (clickstream ? (k.clickstreamVolume ?? 0) : k.adsVolume);

  const clusters: KeywordCluster[] = [];
  for (const [core, members] of orderedGroups) {
    const split = splitByCore.get(core);
    const groups: IntentGroup[] =
      split ??
      [{ label: core, intent: "", keywords: members.map((m) => m.keyword) }];
    for (const group of groups) {
      const keywords = group.keywords.map(keywordOf).sort((a, b) => volumeOf(b) - volumeOf(a) || b.adsVolume - a.adsVolume);
      const flags: ClusterFlag[] = [];
      if (members.length > 1 && !split) {
        flags.push({
          kind: "not-split",
          message: toSplitCores.has(core)
            ? "The model could not split this group, so it is shown whole. Check it by hand for mixed intents."
            : `This group is past the ${CLUSTER_LIMITS.maxSplitGroups}-group cap for one run, so it was not split by intent. Check it by hand, or run it again as its own seed.`,
        });
      }
      clusters.push({
        id: "",
        label: group.label,
        intent: group.intent,
        searchIntent: majorityIntent(keywords),
        coreKeyword: core,
        headKeyword: keywords[0].keyword,
        keywords,
        adsVolume: 0,
        clickstreamVolume: null,
        cpc: keywords[0].cpc,
        serpChecked: false,
        serpPairs: [],
        flags,
      });
    }
  }

  const clusterOfKeyword = new Map<string, KeywordCluster>();
  const minClickstream = input.minVolume;
  if (clickstream) {
    for (const cluster of clusters) {
      cluster.keywords = cluster.keywords.filter((k) => {
        if (k.clickstreamVolume === null || k.clickstreamVolume >= minClickstream || seedSet.has(k.keyword)) {
          return true;
        }
        dropped.push({
          keyword: k.keyword,
          adsVolume: k.adsVolume,
          clickstreamVolume: k.clickstreamVolume,
          reason: "low-clickstream",
        });
        return false;
      });
      if (cluster.keywords.length > 0) cluster.headKeyword = cluster.keywords[0].keyword;
      cluster.cpc = cluster.keywords[0]?.cpc ?? null;
      cluster.searchIntent = majorityIntent(cluster.keywords);
    }
    for (let i = clusters.length - 1; i >= 0; i--) {
      if (clusters[i].keywords.length === 0) clusters.splice(i, 1);
    }
  }
  const droppedLowClickstream = dropped.filter((d) => d.reason === "low-clickstream").length;

  for (const cluster of clusters) {
    const seenKeys = new Set<string>();
    let ads = 0;
    let cs: number | null = null;
    for (const k of cluster.keywords) {
      clusterOfKeyword.set(k.keyword, cluster);
      const key = mergeKey(k) ?? `solo|${k.keyword}`;
      if (!seenKeys.has(key)) {
        seenKeys.add(key);
        ads += k.adsVolume;
      }
      if (k.clickstreamVolume !== null) cs = (cs ?? 0) + k.clickstreamVolume;
    }
    cluster.adsVolume = ads;
    cluster.clickstreamVolume = cs;
  }

  const mergeSets = new Map<string, ClusterKeyword[]>();
  for (const cluster of clusters) {
    for (const k of cluster.keywords) {
      const key = mergeKey(k);
      if (!key) continue;
      const set = mergeSets.get(key) ?? [];
      set.push(k);
      mergeSets.set(key, set);
    }
  }
  for (const set of mergeSets.values()) {
    if (set.length < 2) continue;
    for (const k of set) {
      k.sharedVolumeWith = set.filter((o) => o !== k).map((o) => o.keyword).slice(0, 8);
    }
  }

  const mergedWith = new Map<ClusterFlag, KeywordCluster>();
  for (const cluster of clusters) {
    let best: { mine: ClusterKeyword; other: ClusterKeyword; otherCluster: KeywordCluster } | null = null;
    for (const mine of cluster.keywords) {
      const key = mergeKey(mine);
      if (!key) continue;
      if (mine.clickstreamVolume !== null && mine.clickstreamVolume >= mine.adsVolume * OVERSTATED_BELOW) continue;
      for (const other of mergeSets.get(key) ?? []) {
        const otherCluster = clusterOfKeyword.get(other.keyword);
        if (!otherCluster || otherCluster === cluster) continue;
        if (!best || mine.adsVolume > best.mine.adsVolume) best = { mine, other, otherCluster };
      }
    }
    if (!best) continue;
    const { mine, other, otherCluster } = best;
    const realSplit =
      mine.clickstreamVolume !== null && other.clickstreamVolume !== null
        ? ` Clickstream puts "${mine.keyword}" at ${formatNumber(mine.clickstreamVolume)} a month and "${other.keyword}" at ${formatNumber(other.clickstreamVolume)}.`
        : "";
    const flag: ClusterFlag = {
      kind: "merged-volume",
      message: `Google Ads gives "${mine.keyword}" ${formatNumber(mine.adsVolume)} searches and the same CPC as "${other.keyword}" in "${otherCluster.label}". That figure is shared between the phrases, not this one's own demand.${realSplit}`,
    };
    cluster.flags.push(flag);
    mergedWith.set(flag, otherCluster);
  }

  clusters.sort((a, b) =>
    clickstream
      ? (b.clickstreamVolume ?? 0) - (a.clickstreamVolume ?? 0) || b.adsVolume - a.adsVolume
      : b.adsVolume - a.adsVolume,
  );
  clusters.forEach((cluster, i) => {
    cluster.id = `c${i + 1}`;
  });
  for (const [flag, other] of mergedWith) flag.otherClusterId = other.id;

  const siblings = new Map<string, number>();
  for (const c of clusters) siblings.set(c.coreKeyword, (siblings.get(c.coreKeyword) ?? 0) + 1);

  const tier1 = clusters.filter((c) => (siblings.get(c.coreKeyword) ?? 0) > 1).map((c) => c.headKeyword);
  const tier2 = clusters.filter((c) => (siblings.get(c.coreKeyword) ?? 0) <= 1).map((c) => c.headKeyword);
  const tier3 = clusters.filter((c) => c.keywords.length > 1).map((c) => c.keywords[1].keyword);
  const budget = CLUSTER_LIMITS.maxSerpCalls;
  const ordered = [
    ...tier1.slice(0, Math.round(budget * 0.5)),
    ...tier2.slice(0, Math.round(budget * 0.25)),
    ...tier3.slice(0, Math.round(budget * 0.25)),
    ...tier1,
    ...tier2,
    ...tier3,
  ];
  const plan: Array<{ keyword: string }> = [];
  const planned = new Set<string>();
  for (const keyword of ordered) {
    if (plan.length >= budget) break;
    if (planned.has(keyword)) continue;
    planned.add(keyword);
    plan.push({ keyword });
  }

  options.onPhase(`Reading Google's top 10 for ${plan.length} keywords`, 4);
  const fetched = await mapLimit(plan, SERP_CONCURRENCY, (p) => organicTop10(p.keyword, locale, spend, signal));
  const serps: SerpResult[] = [];
  const serpOf = new Map<string, string[]>();
  let failedSerps = 0;
  fetched.forEach((outcome, i) => {
    if (outcome.status === "fulfilled" && outcome.value.length > 0) {
      serps.push({ keyword: plan[i].keyword, urls: outcome.value });
      serpOf.set(plan[i].keyword, outcome.value);
    } else {
      failedSerps += 1;
    }
  });
  if (failedSerps > 0) notes.push(`${failedSerps} of ${plan.length} SERP lookups failed or came back empty.`);

  options.onPhase("Comparing search results with the intent groups", 5);

  const pairs = new Map<string, SerpPair[]>();
  const addPair = (cluster: KeywordCluster, pair: SerpPair) => {
    const list = pairs.get(cluster.id) ?? [];
    list.push(pair);
    pairs.set(cluster.id, list);
  };

  for (const cluster of clusters) {
    const head = serpOf.get(cluster.headKeyword);
    cluster.serpChecked = Boolean(head);
    if (!head || cluster.keywords.length < 2) continue;
    const second = cluster.keywords[1].keyword;
    const secondUrls = serpOf.get(second);
    if (!secondUrls) continue;
    const pair = serpOverlap(cluster.headKeyword, head, second, secondUrls);
    addPair(cluster, pair);
    if (pair.shared <= SERP_DIFFERENT) {
      cluster.flags.push({
        kind: "serp-splits-cluster",
        pair,
        message: `"${pair.a}" and "${pair.b}" share only ${pair.shared} of their top ${pair.compared} results. Google treats them as different searches, so they may need separate pages.`,
      });
    }
  }

  const checked = clusters.filter((c) => c.serpChecked);
  for (let i = 0; i < checked.length; i++) {
    for (let j = i + 1; j < checked.length; j++) {
      const a = checked[i];
      const b = checked[j];
      const pair = serpOverlap(a.headKeyword, serpOf.get(a.headKeyword)!, b.headKeyword, serpOf.get(b.headKeyword)!);
      const sameCore = a.coreKeyword === b.coreKeyword;
      if (sameCore) {
        addPair(a, pair);
        addPair(b, { ...pair, a: pair.b, b: pair.a });
      }
      if (pair.shared < SERP_SAME) continue;
      if (!sameCore) {
        addPair(a, pair);
        addPair(b, { ...pair, a: pair.b, b: pair.a });
      }
      const smaller = a.clickstreamVolume !== null && b.clickstreamVolume !== null && b.clickstreamVolume > a.clickstreamVolume ? a : b;
      const larger = smaller === a ? b : a;
      for (const [cluster, other] of [[a, b], [b, a]] as const) {
        cluster.flags.push(
          sameCore
            ? {
                kind: "serp-overlaps-other-intent",
                otherClusterId: other.id,
                pair,
                message: `Google shows ${pair.shared} of the same top ${pair.compared} organic pages for "${a.headKeyword}" and "${b.headKeyword}", but the model reads them as different intents. A SERP-only tool would merge them. Check whether the results for "${smaller.headKeyword}" really answer it, or just echo "${larger.headKeyword}".`,
              }
            : {
                kind: "serp-overlaps-other-cluster",
                otherClusterId: other.id,
                pair,
                message: `Shares ${pair.shared} of its top ${pair.compared} organic results with "${other.label}". Google may serve both with one page; decide whether they are the same intent.`,
              },
        );
      }
    }
  }

  for (const cluster of clusters) {
    const crossCluster = cluster.flags
      .filter((f) => f.kind === "serp-overlaps-other-cluster")
      .sort((x, y) => (y.pair?.shared ?? 0) - (x.pair?.shared ?? 0))
      .slice(2);
    cluster.flags = cluster.flags.filter((f) => !crossCluster.includes(f));
    cluster.serpPairs = (pairs.get(cluster.id) ?? []).sort((x, y) => y.shared - x.shared).slice(0, 6);
  }

  const location = LOCATIONS.find((l) => l.code === input.locationCode);
  return {
    ok: true,
    result: {
      input: { ...input, seeds: seedsUsed },
      locationName: location?.name ?? String(input.locationCode),
      startedAt: new Date(started).toISOString(),
      durationMs: Date.now() - started,
      model: llmModel(),
      clusters,
      serps,
      dropped: dropped.sort((a, b) => b.adsVolume - a.adsVolume).slice(0, 300),
      caps: {
        seedsGiven: input.seeds.length,
        seedsUsed: seedsUsed.length,
        maxSeeds: CLUSTER_LIMITS.maxSeeds,
        keywordsFound,
        keywordsKept: clusters.reduce((n, c) => n + c.keywords.length, 0),
        maxKeywords: CLUSTER_LIMITS.maxKeywords,
        droppedLowVolume,
        droppedLowClickstream,
        droppedIrrelevant,
        droppedOverCap: overCap.length,
        coreGroups: orderedGroups.length,
        groupsSplit: toSplit.length - failedSplits,
        groupsNotSplit: splittable.length - (toSplit.length - failedSplits),
        maxSplitGroups: CLUSTER_LIMITS.maxSplitGroups,
        serpCalls: plan.length,
        maxSerpCalls: CLUSTER_LIMITS.maxSerpCalls,
        clickstreamChecked: clickstream !== null,
      },
      notes,
      costUsd: {
        dataforseo: Math.round(spend.dataforseo * 10000) / 10000,
        openrouter: Math.round(spend.openrouter * 10000) / 10000,
      },
      dailyRuns: options.dailyRuns,
    },
  };
}
