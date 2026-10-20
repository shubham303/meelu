import { socialRun, type SocialRunEvent } from "./routes/social";
import { leadsRun, type LeadRunEvent } from "./routes/leads";
import { channel, sleep, type Listener } from "./agent/channel";
import { AVAILABLE_CHECKS, checkContent } from "./agent/checks";
import { siteSummary, writeSiteSummary } from "./agent/hooks";
import {
  crawlChannel,
  crawlSite,
  indexCheck,
  inspectPageUrl,
  renderChannel,
  renderSite,
  startSync,
  stopJob,
  stopSync,
  type JobMessage,
} from "./agent/jobs";
import { abortTurn, respondPermission, runTurn, turnChannel, usage, type Decision, type TurnEvent, type TurnPayload } from "./agent/turns";

interface SummaryEvent {
  event: "summary:start" | "summary:done";
  data: { siteId: string; ok?: boolean; skipped?: boolean; summary?: string; error?: string };
}

type ConnectorsView = Record<string, { fields: Record<string, string>; updatedAt: string | null }>;

const summaries = channel<SummaryEvent>();
const billing = channel<{ message: string }>();
const social = channel<SocialRunEvent>();
const leads = channel<LeadRunEvent>();

const DAY = 86_400_000;
const connectors: ConnectorsView = {
  gsc: { fields: {}, updatedAt: new Date(Date.now() - 12 * DAY).toISOString() },
  ga4: { fields: {}, updatedAt: new Date(Date.now() - 12 * DAY).toISOString() },
};

const OWN_MODELS = [
  { id: "claude-sonnet-5-5", name: "Claude Sonnet 5.5" },
  { id: "claude-opus-5-5", name: "Claude Opus 5.5" },
  { id: "claude-haiku-5-5", name: "Claude Haiku 5.5" },
];
const ownKeys = { anthropic: { saved: false, defaultModel: OWN_MODELS[0].id } };

const GSC_PROPERTIES = [
  { siteUrl: "sc-domain:ledgerly.app", permissionLevel: "siteOwner" },
  { siteUrl: "https://ledgerly.app/", permissionLevel: "siteFullUser" },
  { siteUrl: "https://blog.ledgerly.app/", permissionLevel: "siteOwner" },
];

const describing = new Set<string>();

function summaryFor(siteId: string): string {
  const existing = siteSummary(siteId);
  if (existing) return existing;
  return "A small business website. From the pages read so far it sells one main product with a pricing page, explains it on a handful of feature pages and runs a blog; the crawl has not read enough yet to say more without guessing.";
}

async function describe(siteId: string) {
  describing.add(siteId);
  summaries.emit({ event: "summary:start", data: { siteId } });
  await sleep(3200 + Math.random() * 1500);
  const summary = summaryFor(siteId);
  writeSiteSummary(siteId, summary);
  describing.delete(siteId);
  summaries.emit({ event: "summary:done", data: { siteId, ok: true, summary } });
}

function downloadText(name: string, content: string) {
  const type = name.endsWith(".html") ? "text/html" : name.endsWith(".csv") ? "text/csv" : "text/plain";
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const demoBridge = {
  runTurn: async (payload: TurnPayload) => runTurn(payload),
  onEvent: (cb: Listener<TurnEvent>) => turnChannel.on(cb),
  abort: (turnId: string) => abortTurn(turnId),
  respondPermission: async (requestId: string, decision: Decision) => respondPermission(requestId, decision),
  sessionUsage: async () => ({ ...usage }),

  describeSite: async (siteId: string) => {
    if (!describing.has(siteId)) void describe(siteId);
    return { started: true };
  },
  onSiteSummaryEvent: (cb: Listener<SummaryEvent>) => summaries.on(cb),
  onBillingBlocked: (cb: Listener<{ message: string }>) => billing.on(cb),
  crawlToken: async (domain: string) => ({
    token: `mlc_${Array.from(domain).reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7).toString(16).padStart(8, "0")}4f9c2e17b8a04d6e9c1b7f3a`,
  }),

  crawlSite: async (payload: { siteId: string | null; sitemapUrls?: string[] }) => crawlSite(payload),
  stopCrawl: async (jobId: string) => stopJob(jobId),
  onCrawlEvent: (cb: Listener<JobMessage>) => crawlChannel.on(cb),
  renderSite: async (payload: { siteId: string | null; device: string; scope?: string; limit?: number; url?: string }) => renderSite(payload),
  stopRender: async (jobId: string) => stopJob(jobId),
  onRenderEvent: (cb: Listener<JobMessage>) => renderChannel.on(cb),

  searchSync: async (payload: { siteId: string | null }) => startSync("search", payload),
  stopSearchSync: async (payload: { syncId: string; siteId: string | null }) => stopSync(payload),
  trafficSync: async (payload: { siteId: string | null }) => startSync("traffic", payload),
  stopTrafficSync: async (payload: { syncId: string; siteId: string | null }) => stopSync(payload),
  indexCheck: async (payload: { siteId: string | null }) => indexCheck(payload),
  inspectPageUrl: (payload: { siteId: string | null; url: string }) => inspectPageUrl(payload),
  gscProperties: async (domain: string) => {
    const bare = String(domain ?? "").replace(/^www\./, "");
    return {
      connected: "gsc" in connectors,
      properties: GSC_PROPERTIES,
      matching: GSC_PROPERTIES.filter((p) => p.siteUrl.includes(bare)),
    };
  },
  gaProperties: async () => ({
    connected: "ga4" in connectors,
    accounts: [
      {
        account: "accounts/118204",
        name: "Ledgerly",
        properties: [
          { property: "properties/384920111", propertyId: "384920111", name: "ledgerly.app — web", kind: "PROPERTY_TYPE_ORDINARY" },
          { property: "properties/384920577", propertyId: "384920577", name: "Ledgerly help centre", kind: "PROPERTY_TYPE_ORDINARY" },
        ],
      },
    ],
  }),

  contentChecks: async () => ({ tools: AVAILABLE_CHECKS }),
  checkContent: (payload: { text: string; tools?: string[]; siteId?: string; excludePageIds?: string[]; excludeUrls?: string[] }) =>
    checkContent(payload),

  getConnectors: async (): Promise<ConnectorsView> => ({ ...connectors }),
  removeConnector: async (provider: string): Promise<ConnectorsView> => {
    delete connectors[provider];
    return { ...connectors };
  },
  connectGsc: async (): Promise<ConnectorsView> => {
    await sleep(1200);
    connectors.gsc = { fields: {}, updatedAt: new Date().toISOString() };
    return { ...connectors };
  },
  connectGa4: async (): Promise<ConnectorsView> => {
    await sleep(1200);
    connectors.ga4 = { fields: {}, updatedAt: new Date().toISOString() };
    return { ...connectors };
  },

  getOwnKeys: async () => ({ anthropic: { ...ownKeys.anthropic } }),
  saveOwnAnthropic: async (payload: { apiKey?: string; defaultModel?: string }) => {
    if (payload.apiKey !== undefined) {
      const key = payload.apiKey.trim();
      if (key && !key.startsWith("sk-ant-")) return { error: "That does not look like an Anthropic key (it should start with sk-ant-)." };
      ownKeys.anthropic.saved = key !== "";
    }
    if (payload.defaultModel) ownKeys.anthropic.defaultModel = payload.defaultModel;
    return { anthropic: { ...ownKeys.anthropic } };
  },
  ownModels: async () => (ownKeys.anthropic.saved ? { models: OWN_MODELS } : { error: "Save your Anthropic key first." }),

  socialSignalsSearch: async (payload: { siteId: string; platforms?: string[] }) => socialRun.start(payload, (e) => social.emit(e)),
  socialSignalsStop: async (jobId: string) => socialRun.stop(jobId),
  socialSignalsActive: async (siteId: string) => socialRun.active(siteId),
  socialSignalsPlatforms: async () => socialRun.platforms(),
  onSocialSignalsEvent: (cb: Listener<SocialRunEvent>) => social.on(cb),

  findLeadsSearch: async (payload: { siteId: string; target?: number }) => leadsRun.start(payload, (e) => leads.emit(e)),
  findLeadsStop: async (jobId: string) => leadsRun.stop(jobId),
  findLeadsActive: async (siteId: string) => leadsRun.active(siteId),
  onFindLeadsEvent: (cb: Listener<LeadRunEvent>) => leads.on(cb),

  saveTextFile: async (params: { name: string; content: string }) => {
    downloadText(params.name, params.content);
    return { ok: true as const, path: `~/Downloads/${params.name}` };
  },

  appUpdate: async () => ({ update: null }),
  checkUpdate: async () => ({ currentVersion: "0.1.11", update: null }),
  downloadUpdate: async () => ({ ok: false }),
};

export type DemoBridge = typeof demoBridge;
