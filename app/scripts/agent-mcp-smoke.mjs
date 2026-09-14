import { ENV_DEFAULTS } from "../src/main/config.js";

const URL_BASE = ENV_DEFAULTS.agentMcpUrl;
const API_KEY = process.env.MEELU_API_KEY;
const SITE = process.env.MEELU_SMOKE_SITE ?? "";

if (!API_KEY) {
  console.error("Set MEELU_API_KEY to a workspace key (Dashboard → Settings → API keys).");
  process.exit(1);
}

async function rpc(body) {
  const res = await fetch(URL_BASE, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json, text/event-stream",
      "x-api-key": API_KEY,
      ...(SITE ? { "x-meelu-site": SITE } : {}),
    },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`${res.status}: ${text.slice(0, 200)}`);
  if (body.id === undefined) return null;
  const data = text.startsWith("event:") || text.startsWith("data:")
    ? text.split("\n").find((l) => l.startsWith("data:"))?.slice(5)
    : text;
  const parsed = JSON.parse(data);
  if (parsed.error) throw new Error(JSON.stringify(parsed.error));
  return parsed.result;
}

const init = await rpc({
  jsonrpc: "2.0",
  id: 1,
  method: "initialize",
  params: {
    protocolVersion: "2025-03-26",
    capabilities: {},
    clientInfo: { name: "meelu-app-smoke", version: "0.1.0" },
  },
});
if (init.serverInfo?.name !== "meelu-agent") {
  console.error(`FAIL initialize — server is ${init.serverInfo?.name}`);
  process.exit(1);
}
console.log(`PASS initialize — ${init.serverInfo.name}`);

await rpc({ jsonrpc: "2.0", method: "notifications/initialized" });

const tools = await rpc({ jsonrpc: "2.0", id: 2, method: "tools/list", params: {} });
const names = tools.tools.map((t) => t.name);
const ok = names.includes("run_sql") && names.includes("schema_map") && names.includes("guide");
console.log(`${ok ? "PASS" : "FAIL"} tools/list — ${names.length} tools`);
if (!ok) process.exit(1);

const map = await rpc({
  jsonrpc: "2.0",
  id: 3,
  method: "tools/call",
  params: { name: "schema_map", arguments: {} },
});
const payload = JSON.parse(map.content?.find((c) => c.type === "text")?.text ?? "{}");
const hasSchema = Boolean(payload.workspace_schema) && "canonical" in payload;
console.log(
  `${hasSchema ? "PASS" : "FAIL"} schema_map — workspace=${payload.workspace_schema} site=${payload.site?.id ?? "none"}`,
);
process.exit(hasSchema ? 0 : 1);
