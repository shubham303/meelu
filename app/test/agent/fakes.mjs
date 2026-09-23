import http from "node:http";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { z } from "zod";

export const CATALOG = [
  { name: "run_sql", desk: null, writes: false },
  { name: "find_plans", desk: null, writes: false },
  { name: "get_plan", desk: null, writes: false },
  { name: "save_note", desk: null, writes: true },
  { name: "update_note", desk: null, writes: true },
  { name: "delete_note", desk: null, writes: true },
  { name: "search_page", desk: "pages", writes: false },
  { name: "content_create_piece", desk: "content", writes: true },
  { name: "content_update_piece", desk: "content", writes: true },
  { name: "cluster", desk: "analytics", writes: false },
  { name: "forecast", desk: "analytics", writes: false },
  { name: "save_profile", desk: "profile", writes: true },
  { name: "start_seo_job", desk: "seo", writes: true },
  { name: "screen_page_suggestions", desk: "seo", writes: true },
  { name: "rank_page_suggestions", desk: "seo", writes: true },
];

const NOTE_WRITES = ["save_note", "update_note", "delete_note"];

export const SCOPES = {
  "ask-pages": {
    desk: "pages",
    writes: NOTE_WRITES,
    systemPrompt: "PAGES DESK PROMPT. Answer about the site's pages.\n\n## The database\n\n- site_pages: url text",
  },
  "ask-seo": {
    desk: "seo",
    writes: [...NOTE_WRITES, "start_seo_job", "screen_page_suggestions", "rank_page_suggestions"],
    silentWrites: ["screen_page_suggestions", "rank_page_suggestions"],
    systemPrompt: "SEO DESK PROMPT.\n\n## The database\n\n- seo_keywords: keyword text",
  },
  "ask-pages+content": {
    desk: "pages",
    writes: [...NOTE_WRITES, "content_create_piece", "content_update_piece"],
    systemPrompt: "PAGES DESK PROMPT. Answer about the site's pages.\n\n## The database\n\n- site_pages: url text\n- content_pieces: title text",
  },
};

function scopeBody(action, desks) {
  const key = desks ? `${action}+${desks}` : action;
  const base = SCOPES[key] ?? SCOPES[action];
  const loaded = new Set([base.desk, ...(desks ? desks.split(",") : [])]);
  const offers = ["analytics", "content", "profile"]
    .filter((d) => !loaded.has(d))
    .map((d) => ({ name: d, blurb: `${d} desk`, brief: `The ${d} desk is loaded. BRIEF FOR ${d.toUpperCase()}.` }));
  return {
    action,
    writes: base.writes,
    desk: base.desk,
    createToolName: null,
    global: false,
    mcpServers: {},
    limits: {},
    saveAttachments: false,
    providers: [],
    silentWrites: base.silentWrites ?? [],
    desks: offers,
    systemPrompt: base.systemPrompt,
  };
}

export async function startScopeApi() {
  const calls = [];
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, "http://x");
    if (url.pathname === "/api/v1/agent/scope") {
      const action = url.searchParams.get("action");
      const desks = url.searchParams.get("desks");
      calls.push({ action, desks });
      res.writeHead(200, { "content-type": "application/json" });
      res.end(JSON.stringify({ data: scopeBody(action, desks) }));
      return;
    }
    res.writeHead(404, { "content-type": "application/json" });
    res.end(JSON.stringify({ error: { message: `no route ${url.pathname}` } }));
  });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  return { url: `http://127.0.0.1:${server.address().port}`, calls, close: () => server.close() };
}

export async function startMcp() {
  const counts = { initialize: 0, "tools/list": 0, "tools/call": 0 };
  const build = () => {
    const mcp = new McpServer({ name: "fake-meelu", version: "0.0.0" });
    for (const t of CATALOG) {
      mcp.registerTool(
        t.name,
        {
          description: `${t.name} tool`,
          inputSchema: { q: z.string().optional(), job_id: z.string().optional() },
          _meta: { "meelu/writes": t.writes, ...(t.desk ? { "meelu/desk": t.desk } : {}) },
        },
        async () => ({ content: [{ type: "text", text: `${t.name} ok` }] }),
      );
    }
    return mcp;
  };
  const server = http.createServer(async (req, res) => {
    if (req.url === "/health") {
      res.writeHead(200, { "content-type": "application/json" });
      res.end(JSON.stringify({ ok: true }));
      return;
    }
    let body = "";
    for await (const c of req) body += c;
    let parsed;
    try {
      parsed = body ? JSON.parse(body) : undefined;
    } catch {
      parsed = undefined;
    }
    for (const m of [parsed].flat()) {
      if (m && typeof m.method === "string" && m.method in counts) counts[m.method] += 1;
    }
    const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });
    const mcp = build();
    res.on("close", () => {
      transport.close().catch(() => {});
      mcp.close().catch(() => {});
    });
    await mcp.connect(transport);
    await transport.handleRequest(req, res, parsed);
  });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  return { url: `http://127.0.0.1:${server.address().port}/mcp/`, counts, close: () => server.close() };
}

const sse = (events) => events.map(([ev, data]) => `event: ${ev}\ndata: ${JSON.stringify(data)}\n\n`).join("");

function toolUseResponse(name, input) {
  const id = "toolu_" + Math.random().toString(36).slice(2, 10);
  return sse([
    ["message_start", { type: "message_start", message: { id: "msg_t", type: "message", role: "assistant", model: "m", content: [], stop_reason: null, stop_sequence: null, usage: { input_tokens: 10, output_tokens: 1 } } }],
    ["content_block_start", { type: "content_block_start", index: 0, content_block: { type: "tool_use", id, name, input: {} } }],
    ["content_block_delta", { type: "content_block_delta", index: 0, delta: { type: "input_json_delta", partial_json: JSON.stringify(input) } }],
    ["content_block_stop", { type: "content_block_stop", index: 0 }],
    ["message_delta", { type: "message_delta", delta: { stop_reason: "tool_use", stop_sequence: null }, usage: { output_tokens: 5 } }],
    ["message_stop", { type: "message_stop" }],
  ]);
}

function textResponse(text) {
  return sse([
    ["message_start", { type: "message_start", message: { id: "msg_x", type: "message", role: "assistant", model: "m", content: [], stop_reason: null, stop_sequence: null, usage: { input_tokens: 10, output_tokens: 1 } } }],
    ["content_block_start", { type: "content_block_start", index: 0, content_block: { type: "text", text: "" } }],
    ["content_block_delta", { type: "content_block_delta", index: 0, delta: { type: "text_delta", text } }],
    ["content_block_stop", { type: "content_block_stop", index: 0 }],
    ["message_delta", { type: "message_delta", delta: { stop_reason: "end_turn", stop_sequence: null }, usage: { output_tokens: 3 } }],
    ["message_stop", { type: "message_stop" }],
  ]);
}

export async function startLlm() {
  const requests = [];
  const script = [];
  const server = http.createServer(async (req, res) => {
    let body = "";
    for await (const c of req) body += c;
    let parsed = null;
    try {
      parsed = JSON.parse(body);
    } catch {}
    if (!parsed || !(parsed.tools ?? []).length) {
      res.writeHead(400, { "content-type": "application/json" });
      res.end(JSON.stringify({ type: "error", error: { type: "invalid_request_error", message: "not a model turn" } }));
      return;
    }
    requests.push(parsed);
    const next = script.shift() ?? { text: "ok" };
    res.writeHead(200, { "content-type": "text/event-stream" });
    res.end(next.tool ? toolUseResponse(next.tool, next.input ?? {}) : textResponse(next.text));
  });
  await new Promise((r) => server.listen(0, "127.0.0.1", r));
  return { url: `http://127.0.0.1:${server.address().port}`, requests, script, close: () => server.close() };
}

export function meeluTools(request) {
  return request.tools
    .map((t) => t.name)
    .filter((n) => n.startsWith("mcp__meelu__"))
    .map((n) => n.replace("mcp__meelu__", ""))
    .sort();
}

export function systemText(request) {
  const s = request.system;
  return (Array.isArray(s) ? s : [s]).map((b) => (typeof b === "string" ? b : b.text)).join("\n");
}
