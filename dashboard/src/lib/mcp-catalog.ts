export type CatalogCategory = "cms" | "data" | "design" | "social";

export interface CatalogField {
  key: string;
  label: string;
  help: string;
  placeholder: string;
  secret: boolean;
  optional?: boolean;
  url?: string;
}

export type CatalogTransport =
  | {
      kind: "http";
      url: string;
      auth: "oauth" | "header";
      headers?: Record<string, string>;
    }
  | {
      kind: "stdio";
      command: string;
      args: string[];
      env?: Record<string, string>;
    };

export interface CatalogEntry {
  id: string;
  name: string;
  blurb: string;
  category: CatalogCategory;
  docsUrl: string;
  publisher: "official" | "community";
  verifiedOn: string;
  transport: CatalogTransport;
  fields?: CatalogField[];
  connect?: string;
  agentGuidance?: string;
  quickPrompts?: string[];
  caveat?: string;
}

const GSC: CatalogEntry = {
  id: "gsc",
  name: "Google Search Console",
  blurb: "The real numbers: impressions, clicks and positions for your own site.",
  category: "data",
  docsUrl: "https://developers.google.com/webmaster-tools/v1/api_reference_index",
  publisher: "official",
  verifiedOn: "2026-08-13",
  transport: { kind: "stdio", command: "", args: [] },
  fields: [],
  connect: "gsc",
  agentGuidance: [
    "Google Search Console is the only MEASURED search data available: impressions, clicks, CTR and average position for pages and queries that are actually the user's. Everything else about search volume is modelled — never blur the two, and say which is which whenever both appear in an answer.",
    "The connection powers the SEO desk's Search performance screen: syncing imports the daily query and page rows from this machine, and questions are answered from that store rather than by calling Google per question.",
    "The data lags Google by about three days and the sync may be further behind — check the stored coverage before making trend claims.",
    "The connection is READ-ONLY: nothing here can change anything in the user's Search Console.",
  ].join(" "),
  quickPrompts: [
    "Which queries lost the most clicks in the last 28 days compared with the 28 before?",
    "Which pages get impressions but almost no clicks?",
  ],
  caveat:
    "Connecting opens Google's sign-in in your browser and asks for read-only Search Console access. The token is exchanged on your machine and stored in this device's keychain — it never touches a Meelu server. Sign in with the Google account that already has access to the property: if the property list comes back empty, that is the wrong account rather than an absence of data.",
};

const GA4: CatalogEntry = {
  id: "ga4",
  name: "Google Analytics 4",
  blurb:
    "What actually arrived: sessions, sources and key events for the pages you publish — the other half of the loop Search Console starts.",
  category: "data",
  docsUrl: "https://developers.google.com/analytics/devguides/reporting/data/v1",
  publisher: "official",
  verifiedOn: "2026-08-14",
  transport: { kind: "stdio", command: "", args: [] },
  fields: [],
  connect: "ga4",
  agentGuidance: [
    "Google Analytics is the only MEASURED traffic data available: sessions, users, channels, landing pages, events, countries and devices for the user's own site. Search Console clicks measure a different thing (arrivals from Google search only; sessions are arrivals from everywhere) — never blur the two.",
    "The connection powers the SEO desk's Traffic screen: syncing imports 16 months of daily rollups from this machine, and the desk answers from that store rather than calling Google per question.",
    "Analytics does not say which website a property measures, so the property is always chosen by the user — if none is set yet, send them to the Traffic screen to pick one.",
    "The connection is READ-ONLY: nothing here can change anything in the user's Analytics account.",
  ].join(" "),
  quickPrompts: [
    "Where does my traffic come from, and how did the mix change this quarter?",
    "Which landing pages get sessions but produce no key events?",
  ],
  caveat:
    "Connecting opens Google's sign-in in your browser and asks for read-only Analytics access. The token is exchanged on your machine and stored in this device's keychain — it never touches a Meelu server. Sign in with the Google account that can read the site's property: if the property list comes back empty, that is the wrong account rather than an absence of data.",
};


export const MCP_CATALOG: readonly CatalogEntry[] = [GSC, GA4];

export const CATEGORY_LABEL: Record<CatalogCategory, string> = {
  cms: "Content & docs",
  data: "Data & browsing",
  design: "Design",
  social: "Social",
};

export function catalogEntry(id: string): CatalogEntry | undefined {
  return MCP_CATALOG.find((e) => e.id === id);
}

export function isInstallable(entry: CatalogEntry): boolean {
  return entry.connect !== undefined || entry.transport.kind === "http" || entry.transport.command !== "";
}

export const MEELU_AGENT_MCP_URL = "http://127.0.0.1:8484/mcp/";

export interface MeeluOptions {
  url?: string;
  apiKey: string;
}

export type ServerConfig =
  | { type: "http"; url: string; headers?: Record<string, string> }
  | { command: string; args: string[]; env?: Record<string, string> };

const TOKEN = /\{\{(\w+)\}\}/g;

function fill(text: string, entry: CatalogEntry): string {
  return text.replace(TOKEN, (whole, key: string) => {
    const field = entry.fields?.find((f) => f.key === key);
    return field ? field.placeholder : whole;
  });
}

function fillMap(
  map: Record<string, string> | undefined,
  entry: CatalogEntry,
): Record<string, string> | undefined {
  if (!map) return undefined;
  return Object.fromEntries(Object.entries(map).map(([k, v]) => [k, fill(v, entry)]));
}

function serverConfig(entry: CatalogEntry): ServerConfig {
  if (entry.transport.kind === "http") {
    const headers = fillMap(entry.transport.headers, entry);
    return { type: "http", url: entry.transport.url, ...(headers ? { headers } : {}) };
  }
  const env = fillMap(entry.transport.env, entry);
  return {
    command: entry.transport.command,
    args: entry.transport.args.map((a) => fill(a, entry)),
    ...(env ? { env } : {}),
  };
}

function meeluServer(opts: MeeluOptions): ServerConfig {
  return {
    type: "http",
    url: opts.url ?? MEELU_AGENT_MCP_URL,
    headers: { "x-api-key": opts.apiKey },
  };
}

function q(value: string): string {
  return `'${value.replace(/'/g, `'\\''`)}'`;
}

export function serverConfigJson(entry: CatalogEntry): string {
  return JSON.stringify({ mcpServers: { [entry.id]: serverConfig(entry) } }, null, 2);
}

export function serverCommand(entry: CatalogEntry): string {
  const config = serverConfig(entry);

  if ("type" in config) {
    const headers = Object.entries(config.headers ?? {})
      .map(([k, v]) => `--header ${q(`${k}: ${v}`)}`)
      .join(" ");
    return `claude mcp add ${entry.id} --scope user --transport http ${config.url}${
      headers ? ` ${headers}` : ""
    }`;
  }

  const env = Object.entries(config.env ?? {})
    .map(([k, v]) => `-e ${k}=${q(v)}`)
    .join(" ");
  return `claude mcp add ${entry.id} --scope user${env ? ` ${env}` : ""} -- ${config.command} ${config.args.join(" ")}`;
}

export function meeluConfigJson(opts: MeeluOptions): string {
  return JSON.stringify({ mcpServers: { meelu: meeluServer(opts) } }, null, 2);
}

export function meeluCommand(opts: MeeluOptions): string {
  const config = meeluServer(opts) as {
    type: "http";
    url: string;
    headers: Record<string, string>;
  };
  const headers = Object.entries(config.headers)
    .map(([k, v]) => `--header ${q(`${k}: ${v}`)}`)
    .join(" ");
  return `claude mcp add --transport http meelu ${config.url}${headers ? ` ${headers}` : ""}`;
}
