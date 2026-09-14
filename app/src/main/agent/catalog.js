import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

const CATALOGS = new Map();

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
          writes: meta["meelu/writes"] === true,
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
  if (!refresh && CATALOGS.has(url)) return CATALOGS.get(url);
  const tools = await fetchCatalog(url, headers);
  CATALOGS.set(url, tools);
  return tools;
}

export function forgetToolCatalog(url) {
  CATALOGS.delete(url);
}

export function allowedToolNames(catalog, desks, writes) {
  const loaded = new Set(desks);
  const allowed = new Set(writes);
  for (const t of catalog) {
    if (t.writes) continue;
    if (t.desk === null || loaded.has(t.desk)) allowed.add(t.name);
  }
  return allowed;
}
