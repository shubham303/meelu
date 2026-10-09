import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

const CATALOGS = new Map();

const CATALOG_TTL_MS = 60_000;

async function fetchCatalog(url, headers) {
  const client = new Client({ name: "meelu-app", version: "0.1.0" });
  const transport = new StreamableHTTPClientTransport(new URL(url), { requestInit: { headers } });
  await client.connect(transport);
  try {
    const tools = [];
    let cursor;
    do {
      const page = await client.listTools(cursor ? { cursor } : undefined);
      for (const t of page.tools) {
        const meta = t._meta ?? {};
        tools.push({
          name: t.name,
          desk: typeof meta["meelu/desk"] === "string" ? meta["meelu/desk"] : null,
          provider: typeof meta["meelu/provider"] === "string" ? meta["meelu/provider"] : null,
          writes: meta["meelu/writes"] === true,
          definition: {
            name: t.name,
            ...(t.title ? { title: t.title } : {}),
            description: t.description,
            inputSchema: t.inputSchema,
            ...(t.outputSchema ? { outputSchema: t.outputSchema } : {}),
            ...(t.annotations ? { annotations: t.annotations } : {}),
            _meta: meta,
          },
        });
      }
      cursor = page.nextCursor;
    } while (cursor);
    return tools;
  } finally {
    await client.close().catch(() => {});
  }
}

export async function agentToolCatalog(url, headers, { refresh = false } = {}) {
  const cached = CATALOGS.get(url);
  if (!refresh && cached && Date.now() - cached.at < CATALOG_TTL_MS) return cached.tools;
  const tools = await fetchCatalog(url, headers);
  CATALOGS.set(url, { tools, at: Date.now() });
  return tools;
}

export function forgetToolCatalog(url) {
  CATALOGS.delete(url);
}

export function allowedToolNames(catalog, desks, writes, providers = []) {
  const loaded = new Set(desks);
  const domains = new Set(providers);
  const allowed = new Set(writes);
  for (const t of catalog) {
    if (t.writes) continue;
    if (t.provider !== null) {
      if (domains.has(t.provider)) allowed.add(t.name);
      continue;
    }
    if (t.desk === null || loaded.has(t.desk)) allowed.add(t.name);
  }
  return allowed;
}
