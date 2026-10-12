import { addReport, markCrawled, mockState } from "./api";
import { CSV } from "./data/analytics";
import { PAGES, SITE_ID } from "./data/site";
import { scopeFor } from "./data/misc";

type Listener<T> = (m: T) => void;

interface TurnEvent {
  turnId: string;
  event: string;
  data: Record<string, unknown>;
}

interface JobEvent {
  event: string;
  data: Record<string, unknown>;
}

interface RunEvent {
  jobId: string;
  event: string;
  data: Record<string, unknown>;
}

function channel<T>() {
  const listeners = new Set<Listener<T>>();
  return {
    on(cb: Listener<T>) {
      listeners.add(cb);
      return () => {
        listeners.delete(cb);
      };
    },
    emit(m: T) {
      for (const l of [...listeners]) l(m);
    },
  };
}

const turns = channel<TurnEvent>();
const crawl = channel<JobEvent>();
const render = channel<JobEvent>();
const social = channel<RunEvent>();

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

let seq = 0;
const id = (p: string) => `${p}_${(++seq).toString(36)}${Date.now().toString(36).slice(-3)}`;

const aborted = new Set<string>();

const usage = { tokens: 184_220, inputTokens: 171_900, outputTokens: 12_320, costUsd: 0.91, turns: 14, startedAt: Date.now() - 42 * 60_000 };

const TOOLS: Record<string, string[]> = {
  "ask-site": ["meelu_site_search", "meelu_site_page_details"],
  "ask-pages": ["meelu_site_search", "meelu_site_page_details"],
  "ask-social-listening": ["meelu_social_posts_list"],
  "content-piece": ["meelu_site_search", "content_channel_rules_read"],
  "content-draft": ["content_channel_rules_read"],
  "content-channel-rules": ["content_channel_rules_read"],
  "analyze-data": ["create_session", "profile", "group_aggregate"],
  "analytics-ask": ["run_sql"],
  "profile-setup": ["meelu_site_page_details"],
};

const FLAVOUR: Record<string, string> = {
  "ask-site": "I had a look at the pages the crawl read for ledgerly.app before answering.",
  "ask-pages": "I searched the passages the crawl read, not just the titles.",
  "ask-social-listening": "I went through the posts waiting for a reply first.",
  "content-piece": "I read the channel's rules and the pages that already cover this before drafting.",
  "content-draft": "I read the piece and the open issues the checks flagged.",
  "content-channel-rules": "I read the current rules for that channel first.",
  "analyze-data": "I loaded the attached sources into the analytics engine and profiled them.",
  "profile-setup": "I read the website record to fill in what it already knows.",
};

function reply(action: string, message: string): string {
  const flavour = FLAVOUR[action] ?? "I looked at what this desk holds before answering.";
  const quoted = message.length > 140 ? `${message.slice(0, 137).trimEnd()}…` : message;
  return [
    `${flavour}`,
    "",
    `You asked: *"${quoted}"*`,
    "",
    "This is the demo, so I'm not wired to a model — in the Meelu app this turn would run on your own machine, against the model and key you chose, with direct read access to everything this desk holds and only the writes the desk allows. Every change it makes shows up in the panel on the left as a marked proposal for you to keep or discard.",
    "",
    "What a real answer here looks like:",
    "",
    "- **Specific.** Page URLs, dates and numbers from your own data, not generic advice.",
    "- **Bounded.** It reads everything it was scoped and writes only with the tools listed under the title of this panel.",
    "- **Yours to accept.** Nothing is saved, sent or published until you say so.",
    "",
    "Click around the rest of the demo — the crawl, the checks, the link suggestions and the reports are all real screens working on sample data. [Download the app](https://meelu.tech/download) to run it on your own site.",
  ].join("\n");
}

async function stream(turnId: string, action: string, message: string) {
  await sleep(250);
  if (aborted.has(turnId)) return;
  turns.emit({ turnId, event: "session", data: { sessionId: "sess_demo" } });
  const scope = scopeFor(action);
  turns.emit({ turnId, event: "scope", data: { action, writes: scope.writes, readOnly: scope.writes.length === 0, servers: ["meelu-agent", "meelu-analytics"], notices: [] } });
  for (const tool of TOOLS[action] ?? ["meelu_site_search"]) {
    await sleep(420 + Math.random() * 380);
    if (aborted.has(turnId)) return;
    turns.emit({ turnId, event: "tool", data: { name: tool } });
  }
  await sleep(500);
  const text = reply(action, message);
  const words = text.split(/(?<=\s)/);
  for (let i = 0; i < words.length; i += 2) {
    if (aborted.has(turnId)) return;
    turns.emit({ turnId, event: "text", data: { text: words.slice(i, i + 2).join("") } });
    await sleep(18 + Math.random() * 30);
  }
  usage.turns += 1;
  usage.inputTokens += 6_400;
  usage.outputTokens += 310;
  usage.tokens = usage.inputTokens + usage.outputTokens;
  usage.costUsd = Math.round((usage.costUsd + 0.041) * 1000) / 1000;
  turns.emit({ turnId, event: "done", data: { ok: true } });
}

async function runCrawl(jobId: string, siteId: string | null) {
  const total = PAGES.length;
  crawl.emit({ event: "crawl:started", data: { siteId, jobId } });
  let fetched = 0;
  const stopAt = () => crawlStop.has(jobId);
  while (fetched < total && !stopAt()) {
    await sleep(140 + Math.random() * 120);
    fetched = Math.min(total, fetched + 1 + Math.floor(Math.random() * 4));
    crawl.emit({ event: "crawl:progress", data: { siteId, jobId, phase: fetched < total * 0.85 ? "sitemap" : "links", fetched, queued: total - fetched, skipped: 0, seen: total } });
  }
  markCrawled();
  crawl.emit({ event: "crawl:done", data: { siteId, jobId, ok: true, stopped: stopAt(), pagesStored: fetched, skipped: 0 } });
  crawlStop.delete(jobId);
}
const crawlStop = new Set<string>();

async function runRender(jobId: string, siteId: string | null, device: string, total: number) {
  render.emit({ event: "render:started", data: { siteId, jobId, device, total, rendered: 0, failed: 0 } });
  let rendered = 0;
  while (rendered < total && !renderStop.has(jobId)) {
    await sleep(320 + Math.random() * 300);
    rendered += 1;
    const page = PAGES[rendered % PAGES.length];
    render.emit({ event: "render:progress", data: { siteId, jobId, device, total, rendered, failed: 0, skipped: 0, current: page.url } });
  }
  render.emit({ event: "render:done", data: { siteId, jobId, device, ok: true, stopped: renderStop.has(jobId), rendered, total, failed: 0, skipped: 0 } });
  renderStop.delete(jobId);
}
const renderStop = new Set<string>();

async function runSync(kind: "search" | "traffic", syncId: string, siteId: string | null) {
  const daysTotal = 16;
  crawl.emit({ event: `${kind}:started`, data: { siteId, syncId, daysTotal } });
  for (let d = 1; d <= daysTotal; d++) {
    await sleep(260);
    crawl.emit({ event: `${kind}:progress`, data: { siteId, syncId, phase: "days", daysDone: d, daysTotal, rowsStored: d * 412, day: new Date(Date.now() - (daysTotal - d) * 86_400_000).toISOString().slice(0, 10) } });
  }
  crawl.emit({ event: `${kind}:done`, data: { siteId, syncId, ok: true, rowsStored: daysTotal * 412 } });
}

async function runIndexCheck(siteId: string | null) {
  const total = PAGES.length;
  for (let i = 1; i <= total; i += 3) {
    await sleep(120);
    crawl.emit({ event: "index:progress", data: { siteId, inspected: Math.min(i, total), total } });
  }
  crawl.emit({ event: "index:done", data: { siteId, ok: true, inspected: total, note: "Every page already had a fresh verdict; nothing changed." } });
}

async function runSocial(jobId: string, platforms: string[]) {
  const stop = () => socialStop.has(jobId);
  social.emit({ jobId, event: "stage", data: { stage: "expanding", query: "freelancers asking which bookkeeping app to use" } });
  await sleep(900);
  if (!stop()) {
    social.emit({ jobId, event: "stage", data: { stage: "fetching" } });
    for (const p of platforms) {
      if (stop()) break;
      social.emit({ jobId, event: "platform", data: { platform: p, status: "fetching" } });
      await sleep(500 + Math.random() * 500);
      social.emit({ jobId, event: "platform", data: { platform: p, status: "done", count: 20 + Math.floor(Math.random() * 60) } });
    }
  }
  if (!stop()) {
    social.emit({ jobId, event: "stage", data: { stage: "gating" } });
    for (let i = 0; i < 6; i++) {
      await sleep(260);
      social.emit({ jobId, event: "gate", data: { pending: 30 - i * 5, kept: 2, filtered: 3 } });
    }
  }
  if (!stop()) {
    social.emit({ jobId, event: "stage", data: { stage: "classifying", total: 12 } });
    for (let i = 1; i <= 12; i++) {
      if (stop()) break;
      await sleep(220);
      social.emit({ jobId, event: "classified", data: { judged: i, total: 12 } });
    }
  }
  social.emit({ jobId, event: stop() ? "stopped" : "done", data: { fetched: 212, kept: 9 } });
  socialStop.delete(jobId);
}
const socialStop = new Set<string>();


function parseCsv(text: string, limit: number) {
  const lines = text.split("\n").filter(Boolean);
  const columns = lines[0]?.split(",") ?? [];
  const rows = lines.slice(1, 1 + limit).map((l) => l.split(","));
  return { columns, rows, more: lines.length - 1 > limit };
}

let llm = { saved: true, provider: "anthropic" as const, model: "claude-sonnet-5", baseUrl: "", hasApiKey: true };

const connectors: Record<string, { fields: Record<string, string>; updatedAt: string | null }> = {
  gsc: { fields: { account: "maya@ledgerly.app", property: "sc-domain:ledgerly.app" }, updatedAt: new Date(Date.now() - 12 * 86_400_000).toISOString() },
  ga4: { fields: { account: "maya@ledgerly.app", property: "properties/384920111" }, updatedAt: new Date(Date.now() - 12 * 86_400_000).toISOString() },
  github: { fields: { token: "ghp_••••••••", repo: "ledgerly/website" }, updatedAt: new Date(Date.now() - 30 * 86_400_000).toISOString() },
};

export const demoBridge = {
  runTurn: async (payload: { action: string; siteId: string | null; message: string; sessionId?: string }) => {
    const turnId = id("turn");
    void stream(turnId, payload.action, payload.message);
    return { turnId };
  },
  onEvent: (cb: Listener<TurnEvent>) => turns.on(cb),
  abort: (turnId: string) => {
    aborted.add(turnId);
    turns.emit({ turnId, event: "done", data: { ok: true } });
  },
  respondPermission: async () => ({ ok: true }),
  sessionUsage: async () => ({ ...usage }),

  crawlToken: async () => ({ token: "mlc_4f9c2e17b8a04d6e9c1b7f3a5d2e8c41" }),
  crawlSite: async (payload: { siteId: string | null }) => {
    const jobId = id("crawl");
    void runCrawl(jobId, payload.siteId ?? SITE_ID);
    return { jobId, started: true };
  },
  stopCrawl: async (jobId: string) => {
    crawlStop.add(jobId);
    return { stopping: true };
  },
  onCrawlEvent: (cb: Listener<JobEvent>) => crawl.on(cb),
  indexCheck: async (payload: { siteId: string | null }) => {
    void runIndexCheck(payload.siteId ?? SITE_ID);
    return { started: true, total: PAGES.length, inspected: 0 };
  },

  renderSite: async (payload: { siteId: string | null; device: "desktop" | "mobile"; scope?: string; limit?: number; url?: string }) => {
    const jobId = id("render");
    const total = payload.url ? 1 : payload.scope === "all" ? PAGES.length : Math.min(payload.limit ?? 12, PAGES.length);
    void runRender(jobId, payload.siteId ?? SITE_ID, payload.device, total);
    return { jobId, started: true };
  },
  stopRender: async (jobId: string) => {
    renderStop.add(jobId);
    return { stopping: true };
  },
  onRenderEvent: (cb: Listener<JobEvent>) => render.on(cb),

  searchSync: async (payload: { siteId: string | null }) => {
    const syncId = id("gsc");
    void runSync("search", syncId, payload.siteId ?? SITE_ID);
    return { syncId, started: true };
  },
  stopSearchSync: async () => ({ stopping: true }),
  gscProperties: async () => ({
    connected: true,
    properties: [
      { siteUrl: "sc-domain:ledgerly.app", permissionLevel: "siteOwner" },
      { siteUrl: "https://ledgerly.app/", permissionLevel: "siteFullUser" },
      { siteUrl: "sc-domain:ledgerly.dev", permissionLevel: "siteOwner" },
    ],
    matching: [{ siteUrl: "sc-domain:ledgerly.app", permissionLevel: "siteOwner" }],
  }),
  connectGsc: async () => ({ ...connectors }),
  inspectPageUrl: async () => {
    await sleep(900);
    return { inspection: { verdict: "PASS", coverageState: "Submitted and indexed" } };
  },

  trafficSync: async (payload: { siteId: string | null }) => {
    const syncId = id("ga");
    void runSync("traffic", syncId, payload.siteId ?? SITE_ID);
    return { syncId, started: true };
  },
  stopTrafficSync: async () => ({ stopping: true }),
  gaProperties: async () => ({
    connected: true,
    accounts: [
      { account: "accounts/1182", name: "Ledgerly", properties: [{ property: "properties/384920111", propertyId: "384920111", name: "ledgerly.app — web", kind: "GA4" }] },
    ],
  }),
  connectGa4: async () => ({ ...connectors }),

  getConnectors: async () => ({ ...connectors }),
  setConnector: async (provider: string, values: Record<string, string>) => {
    connectors[provider] = { fields: values, updatedAt: new Date().toISOString() };
    return { ...connectors };
  },
  removeConnector: async (provider: string) => {
    delete connectors[provider];
    return { ...connectors };
  },
  getLlmConfig: async () => ({ ...llm }),
  setLlmConfig: async (cfg: { provider: typeof llm.provider; model: string; baseUrl: string; apiKey?: string }) => {
    llm = { saved: true, provider: cfg.provider, model: cfg.model, baseUrl: cfg.baseUrl, hasApiKey: cfg.apiKey === undefined ? llm.hasApiKey : cfg.apiKey !== "" };
    return { ...llm };
  },

  checkContent: async (payload: { text: string; channelKey?: string; hasMedia?: boolean }) => {
    await sleep(1400);
    const text = payload.text;
    const sentences = text.split(/(?<=[.!?])\s+/);
    const long = sentences.find((s) => s.split(/\s+/).length > 32);
    const results: Record<string, { summary: Record<string, unknown> | null; issues: Array<Record<string, unknown>> }> = {
      readability: {
        summary: { grade: 7.8, sentences: sentences.length },
        issues: long ? [{ code: "long_sentence", title: `One sentence runs to ${long.split(/\s+/).length} words`, detail: "Readers skim; split it.", anchorText: long.trim().slice(0, 200), suggestion: null }] : [],
      },
      ai_detector: { summary: { score: 0.11 }, issues: [] },
      seo: { summary: null, issues: text.length < 400 && payload.channelKey === "website" ? [{ code: "thin", title: "Under 400 characters for a website page", detail: "Thin pages rarely rank. Expand it.", anchorText: null, suggestion: null }] : [] },
      channel_rules: { summary: null, issues: payload.channelKey === "linkedin" && /\?\s*$/.test(text.trim()) ? [{ code: "closing_question", title: "Ends on a question — the LinkedIn rules ask for a takeaway", detail: "Make it specific or replace it with the takeaway.", anchorText: text.trim().split("\n").pop() ?? null, suggestion: null }] : [] },
    };
    return { results };
  },

  socialSignalsSearch: async (payload: { siteId: string; platforms?: string[] }) => {
    const jobId = id("sl");
    void runSocial(jobId, payload.platforms ?? ["reddit", "hackernews", "x"]);
    return { jobId };
  },
  socialSignalsStop: async (jobId: string) => {
    socialStop.add(jobId);
    return { stopping: true };
  },
  socialSignalsPlatforms: async () => ({
    platforms: [
      { id: "reddit", label: "Reddit", access: "apify" as const, available: true },
      { id: "hackernews", label: "Hacker News", access: "direct" as const, available: true },
      { id: "x", label: "X", access: "apify" as const, available: true },
      { id: "linkedin", label: "LinkedIn", access: "apify" as const, available: true },
      { id: "youtube", label: "YouTube", access: "apify" as const, available: true },
      { id: "bluesky", label: "Bluesky", access: "direct" as const, available: true },
    ],
  }),
  onSocialSignalsEvent: (cb: Listener<RunEvent>) => social.on(cb),

  analyticsSaveSource: async (params: { sessionId: string; sourceId: string; content: string; name?: string }) => {
    const relativePath = `analytics/${params.sessionId}/${params.sourceId}`;
    mockState().csv[relativePath] = params.content;
    return { relativePath, bytes: params.content.length };
  },
  analyticsCheckSession: async (params: { paths: string[] }) => {
    const missing = params.paths.filter((p) => !(p in mockState().csv) && !(p in CSV));
    return { engine: "present" as const, missing, ok: missing.length === 0 };
  },
  analyticsResolvePaths: async (params: { paths: string[] }) =>
    params.paths.map((p) => ({ relativePath: p, path: `/Users/maya/Library/Application Support/Meelu/data/${p}`, missing: !(p in mockState().csv) })),
  analyticsDeleteSource: async (params: { relativePath: string }) => {
    delete mockState().csv[params.relativePath];
    return { ok: true as const };
  },
  analyticsReadSource: async (params: { relativePath: string; limit?: number }) => {
    const text = mockState().csv[params.relativePath];
    if (!text) return { error: "That file is not on this machine any more." };
    const parsed = parseCsv(text, params.limit ?? 50);
    return { name: params.relativePath.split("/").pop() ?? "source.csv", path: `/Users/maya/Library/Application Support/Meelu/data/${params.relativePath}`, bytes: text.length, ...parsed };
  },
  analyticsRevealSource: async () => ({ ok: true as const }),
  analyticsExportSource: async () => ({ ok: true as const, path: "/Users/maya/Downloads/export.csv" }),
  analyticsExportText: async (params: { name: string }) => ({ ok: true as const, path: `/Users/maya/Downloads/${params.name}` }),
};

export function saveDemoReport(sessionId: string, title: string, html: string) {
  return addReport(sessionId, title, html);
}

export type DemoBridge = typeof demoBridge;
