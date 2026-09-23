import { randomUUID } from "node:crypto";
import { dedupeProspects } from "./dedupe.js";
import { enrichEmail } from "./enrich.js";
import { expandBrief } from "./expand.js";
import { BATCH_SIZE, qualifyBatch } from "./qualify.js";
import {
  bulkLeads,
  createRun,
  fetchCampaign,
  fetchCampaigns,
  fetchProfile,
  fetchSite,
  patchRun,
  toApiLead,
} from "./store.js";

const KEEP_THRESHOLD = 0.6;
const QUALIFY_CONCURRENCY = 3;
const PER_SOURCE_LIMIT = 25;
const MAX_PROSPECTS = 100;

const running = new Map();

class Stopped extends Error {
  constructor() {
    super("The run was stopped.");
  }
}

function guard(state) {
  if (state.stopped) throw new Stopped();
}

function chunk(list, size) {
  const out = [];
  for (let i = 0; i < list.length; i += size) out.push(list.slice(i, i + size));
  return out;
}

export function startLeadsRun(payload, emit, { providers, llm, cookieHeader = "" }) {
  const { siteId = null, campaignId = null, all = false } = payload;
  if (!siteId) return { error: "No site selected." };
  if (!campaignId && !all) return { error: "Pick a campaign to run." };
  const jobId = randomUUID();
  const state = { stopped: false };
  running.set(jobId, state);
  void drive(jobId, { siteId, campaignId, all }, state, emit, {
    providers,
    llm,
    cookieHeader,
  }).finally(() => running.delete(jobId));
  return { jobId };
}

export function stopLeadsRun(jobId) {
  const state = running.get(jobId);
  if (!state) return false;
  state.stopped = true;
  return true;
}

function siteContextOf(site, profile) {
  return [
    site?.name ? `Site: ${site.name} (${site.domain ?? ""})` : "",
    site?.summary ? `Summary: ${site.summary}` : "",
    profile?.fullName
      ? `Sender: ${profile.fullName}${profile.role ? `, ${profile.role}` : ""}${profile.company ? ` at ${profile.company}` : ""}`
      : "",
    profile?.bio ? `Sender bio: ${profile.bio}` : "",
  ]
    .filter(Boolean)
    .join("\n");
}

async function fanOut(input, campaign, queries, send, providers, sourceStats, state) {
  const fetched = [];
  const sources = Array.isArray(campaign.sources) ? campaign.sources : [];
  await Promise.allSettled(
    sources.map(async (source) => {
      send("source", { campaignId: campaign.id, source, status: "fetching" });
      const stat = { found: 0, qualified: 0 };
      sourceStats[source] = stat;
      try {
        const prospects = await providers.prospects.searchSource({
          source,
          queries,
          limit: PER_SOURCE_LIMIT,
          siteId: input.siteId,
        });
        guard(state);
        stat.found = prospects.length;
        fetched.push(...prospects);
        send("source", { campaignId: campaign.id, source, status: "done", count: prospects.length });
      } catch (err) {
        if (err instanceof Stopped) return;
        stat.error = err instanceof Error ? err.message : String(err);
        send("source", { campaignId: campaign.id, source, status: "error", error: stat.error });
      }
    }),
  );
  return fetched;
}

async function runCampaign(campaign, context, send, state, deps) {
  const { siteId, cookieHeader } = context;
  const { providers, llm } = deps;
  const sourceStats = {};
  let runId = null;
  let found = 0;

  const finishPatch = (status, extra = {}) => {
    if (!runId) return Promise.resolve();
    return patchRun(
      siteId,
      runId,
      { status, finishedAt: new Date().toISOString(), found, sourceStats, ...extra },
      cookieHeader,
    ).catch(() => {});
  };

  try {
    send("stage", { campaignId: campaign.id, stage: "expanding" });
    const queries = await expandBrief(campaign, context.siteContext, llm);
    guard(state);
    if (queries.length === 0) throw new Error("The brief produced no search queries.");

    const run = await createRun(siteId, campaign.id, cookieHeader);
    runId = run?.id ?? null;
    guard(state);

    send("stage", { campaignId: campaign.id, stage: "fetching", queries });
    const fetched = await fanOut(context, campaign, queries, send, providers, sourceStats, state);
    guard(state);
    found = fetched.length;

    let prospects = dedupeProspects(fetched).slice(0, MAX_PROSPECTS);

    send("stage", { campaignId: campaign.id, stage: "qualifying", total: prospects.length });
    const batches = chunk(prospects, BATCH_SIZE);
    const judged = [];
    let cursor = 0;
    const worker = async () => {
      while (cursor < batches.length) {
        guard(state);
        const batch = batches[cursor];
        cursor += 1;
        const results = await qualifyBatch(batch, campaign, context.siteContext, llm);
        judged.push(...results);
        send("stage", {
          campaignId: campaign.id,
          stage: "qualifying",
          judged: judged.length,
          total: prospects.length,
        });
      }
    };
    await Promise.all(
      Array.from({ length: Math.min(QUALIFY_CONCURRENCY, batches.length) }, worker),
    );
    guard(state);

    let kept = judged
      .filter((p) => (p.fitScore ?? 0) >= KEEP_THRESHOLD)
      .sort((a, b) => (b.fitScore ?? 0) - (a.fitScore ?? 0));
    for (const p of kept) {
      const stat = sourceStats[p.source];
      if (stat) stat.qualified += 1;
    }

    send("stage", { campaignId: campaign.id, stage: "enriching", total: kept.length });
    const enriched = [];
    for (const lead of kept) {
      guard(state);
      enriched.push(await enrichEmail(lead));
    }
    kept = enriched;

    let inserted = 0;
    let skipped = 0;
    if (kept.length > 0) {
      const result = await bulkLeads(
        siteId,
        { runId, campaignId: campaign.id, leads: kept.map(toApiLead) },
        cookieHeader,
      );
      inserted = Number(result?.inserted) || 0;
      skipped = Number(result?.skipped) || 0;
    }
    guard(state);

    await finishPatch("done", { qualified: inserted, skippedKnown: skipped });
    send("done", {
      campaignId: campaign.id,
      runId,
      found,
      qualified: inserted,
      skippedKnown: skipped,
      sourceStats,
    });
  } catch (err) {
    if (err instanceof Stopped) {
      await finishPatch("stopped");
      throw err;
    }
    const message = err instanceof Error ? err.message : String(err);
    await finishPatch("error", { error: message });
    send("error", { campaignId: campaign.id, message });
  }
}

async function drive(jobId, input, state, emit, deps) {
  const send = (event, data) => emit({ jobId, event, data });
  const { cookieHeader } = deps;
  try {
    const [site, profile] = await Promise.all([
      fetchSite(input.siteId, cookieHeader).catch(() => null),
      fetchProfile(cookieHeader),
    ]);
    guard(state);
    const context = {
      siteId: input.siteId,
      cookieHeader,
      siteContext: siteContextOf(site, profile),
    };
    let campaigns;
    if (input.all) {
      campaigns = (await fetchCampaigns(input.siteId, cookieHeader)).filter(
        (c) => c?.status === "active",
      );
    } else {
      campaigns = [await fetchCampaign(input.siteId, input.campaignId, cookieHeader)];
    }
    guard(state);
    if (campaigns.length === 0) throw new Error("No active campaign to run.");
    for (const campaign of campaigns) {
      guard(state);
      await runCampaign(campaign, context, send, state, deps);
    }
  } catch (err) {
    if (err instanceof Stopped) {
      send("stopped", {});
      return;
    }
    send("error", { message: err instanceof Error ? err.message : String(err) });
  }
}
