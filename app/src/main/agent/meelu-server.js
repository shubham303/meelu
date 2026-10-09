import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";

export const MEELU_SERVER = "meelu";

const CALL_TIMEOUT_MS = 30 * 60_000;
const RELIST_WAIT_MS = 3_000;

export function meeluMcpServer(url, headers, catalog, visible) {
  let shown = new Set(visible);
  let client = null;
  let relisted = [];

  const connect = async () => {
    if (client) return client;
    const next = new Client({ name: "meelu-app", version: "0.1.0" });
    await next.connect(new StreamableHTTPClientTransport(new URL(url), { requestInit: { headers } }));
    client = next;
    return client;
  };

  const drop = () => {
    const stale = client;
    client = null;
    stale?.close().catch(() => {});
  };

  const server = new Server({ name: MEELU_SERVER, version: "1.0.0" }, { capabilities: { tools: { listChanged: true } } });

  server.setRequestHandler(ListToolsRequestSchema, async () => {
    const waiting = relisted;
    relisted = [];
    for (const resolve of waiting) resolve();
    return {
      tools: catalog
        .filter((t) => shown.has(t.name))
        .map((t) => ({ ...t.definition, _meta: { ...t.definition._meta, "anthropic/alwaysLoad": true } })),
    };
  });

  server.setRequestHandler(CallToolRequestSchema, async (request, extra) => {
    const { name, arguments: args } = request.params;
    if (!shown.has(name)) {
      return { isError: true, content: [{ type: "text", text: `${name} is not in this task.` }] };
    }
    try {
      const upstream = await connect();
      return await upstream.callTool({ name, arguments: args ?? {} }, undefined, {
        signal: extra.signal,
        timeout: CALL_TIMEOUT_MS,
        resetTimeoutOnProgress: true,
      });
    } catch (err) {
      if (!extra.signal.aborted) drop();
      return {
        isError: true,
        content: [{ type: "text", text: `The agent server failed on ${name}: ${err?.message ?? err}` }],
      };
    }
  });

  return {
    config: { type: "sdk", name: MEELU_SERVER, instance: server },
    async show(names) {
      shown = new Set(names);
      const seen = new Promise((resolve) => relisted.push(resolve));
      await server.sendToolListChanged().catch(() => {});
      await Promise.race([seen, new Promise((resolve) => setTimeout(resolve, RELIST_WAIT_MS))]);
    },
    close() {
      drop();
    },
  };
}
