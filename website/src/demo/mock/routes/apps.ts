import { MockHttpError, newId, ok, type Route } from "../core";

interface Connection {
  connectionId: string;
  status: string;
  label?: string | null;
}

interface AppConnections {
  desk: string;
  app: string;
  name: string;
  connections: Connection[];
}

const CATALOG: Array<[string, string, string, string | null]> = [
  ["email", "gmail", "Gmail", "maya@ledgerly.app"],
  ["email", "outlook", "Outlook", null],
  ["email", "mailchimp", "Mailchimp", "Ledgerly newsletter"],
  ["email", "kit", "Kit", null],
  ["cms", "webflow", "Webflow", "ledgerly.app"],
  ["cms", "contentful", "Contentful", null],
  ["crm", "hubspot", "HubSpot", "Ledgerly · portal 4419027"],
  ["crm", "attio", "Attio", null],
  ["crm", "pipedrive", "Pipedrive", null],
  ["docs", "notion", "Notion", "Ledgerly Marketing"],
  ["docs", "googledocs", "Google Docs", null],
  ["social", "reddit", "Reddit", "u/ledgerly_maya"],
  ["social", "linkedin", "LinkedIn", null],
  ["social", "github", "GitHub", null],
];

const LABELS: Record<string, string> = {
  gmail: "maya@ledgerly.app",
  outlook: "maya@ledgerly.app",
  mailchimp: "Ledgerly newsletter",
  kit: "Ledgerly newsletter",
  webflow: "ledgerly.app",
  contentful: "Ledgerly · master",
  hubspot: "Ledgerly · portal 4419027",
  attio: "Ledgerly workspace",
  pipedrive: "Ledgerly sales",
  notion: "Ledgerly Marketing",
  googledocs: "maya@ledgerly.app",
  reddit: "u/ledgerly_maya",
  linkedin: "Maya Chen",
  github: "ledgerly-app",
};

const state: AppConnections[] = CATALOG.map(([desk, app, name, label]) => ({
  desk,
  app,
  name,
  connections: label ? [{ connectionId: `ca_${app}`, status: "ACTIVE", label }] : [],
}));

export function connectedApps(): Array<{ desk: string; name: string; label: string }> {
  return state.flatMap((a) =>
    a.connections.filter((c) => c.status === "ACTIVE").map((c) => ({ desk: a.desk, name: a.name, label: c.label ?? "" })),
  );
}

export const ROUTES: Route[] = [
  ["GET", /^\/api\/v1\/connected-apps$/, () => ok(state)],
  ["POST", /^\/api\/v1\/connected-apps$/, (_m, _q, body) => {
    const entry = state.find((a) => a.desk === body.desk && a.app === body.app);
    if (!entry) throw new MockHttpError(400, `Unknown app ${String(body.app)} for the ${String(body.desk)} desk.`);
    entry.connections.push({ connectionId: newId("ca"), status: "ACTIVE", label: LABELS[entry.app] ?? null });
    return ok({ url: `/demo-signin?app=${encodeURIComponent(entry.name)}` });
  }],
  ["DELETE", /^\/api\/v1\/connected-apps\/([^/]+)$/, (m) => {
    const entry = state.find((a) => a.connections.some((c) => c.connectionId === m[1]));
    if (!entry) throw new MockHttpError(404, "Not found");
    entry.connections = entry.connections.filter((c) => c.connectionId !== m[1]);
    return ok({ id: m[1], deleted: true });
  }],
];
