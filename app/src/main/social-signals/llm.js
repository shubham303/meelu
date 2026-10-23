import { resolveLlm } from "../agent/runner.js";
import { ANTHROPIC_VERSION } from "../integrations/llm/own-key.js";
import { apiFetch } from "../net.js";

const MAX_OUTPUT_TOKENS = 4096;
const CALL_TIMEOUT_MS = 120_000;

let billingBlocked = () => {};

export function onBillingBlocked(listener) {
  billingBlocked = listener;
}

export function headersFor(gateway) {
  const shared = { "content-type": "application/json", "anthropic-version": ANTHROPIC_VERSION };
  if (gateway.ownKey) return { ...shared, "x-api-key": gateway.apiKey };
  return { ...shared, authorization: `Bearer ${gateway.apiKey}`, ...gateway.headers };
}

function callSignal(target, timeoutMs) {
  const timeout = AbortSignal.timeout(timeoutMs);
  return target?.signal ? AbortSignal.any([timeout, target.signal]) : timeout;
}

export async function jsonCall(system, prompt, target, options = {}) {
  const resolved = await resolveLlm(target);
  const { gateway, model, limits } = resolved;
  const tools = typeof options.tools === "function" ? options.tools(resolved) : options.tools;
  const res = await apiFetch(`${gateway.baseUrl}/v1/messages`, {
    method: "POST",
    headers: headersFor(gateway),
    body: JSON.stringify({
      model: options.model ? options.model(resolved) : model,
      max_tokens: Math.min(MAX_OUTPUT_TOKENS, limits?.output ?? MAX_OUTPUT_TOKENS),
      system,
      messages: [{ role: "user", content: prompt }],
      stream: true,
      ...(tools ? { tools } : {}),
      ...(options.extra ? options.extra(resolved) : {}),
    }),
    signal: callSignal(target, options.timeoutMs ?? CALL_TIMEOUT_MS),
  });
  if (!res.ok) {
    const payload = await res.json().catch(() => ({}));
    const message = payload?.error?.message || `The model call failed (${res.status}).`;
    if (res.status === 402) billingBlocked(message);
    throw new Error(message);
  }
  return jsonOfText(await streamedText(res));
}

export function sseEvents(buffer) {
  const frames = buffer.split(/\r?\n\r?\n/);
  const rest = frames.pop() ?? "";
  const events = [];
  for (const frame of frames) {
    const data = frame
      .split(/\r?\n/)
      .filter((line) => line.startsWith("data:"))
      .map((line) => line.slice(5).trimStart())
      .join("\n");
    if (!data) continue;
    try {
      events.push(JSON.parse(data));
    } catch {}
  }
  return { events, rest };
}

async function streamedText(res) {
  const decoder = new TextDecoder();
  let buffer = "";
  let text = "";
  for await (const chunk of res.body) {
    buffer += decoder.decode(chunk, { stream: true });
    const { events, rest } = sseEvents(buffer);
    buffer = rest;
    for (const event of events) {
      if (event?.type === "error") {
        throw new Error(event.error?.message || "The model call failed.");
      }
      if (event?.type === "content_block_delta" && event.delta?.type === "text_delta") {
        text += event.delta.text ?? "";
      }
    }
  }
  return text;
}

export function jsonOf(payload) {
  return jsonOfText(
    (payload?.content ?? [])
      .filter((block) => block?.type === "text")
      .map((block) => block.text)
      .join(""),
  );
}

export function jsonOfText(text) {
  const raw = String(text ?? "").trim();
  const start = raw.indexOf("{");
  const end = raw.lastIndexOf("}");
  if (start === -1 || end <= start) throw new Error("The model returned no JSON object.");
  return JSON.parse(raw.slice(start, end + 1));
}

export const WEB_SEARCH_MODEL = "deepseek/deepseek-v4.1-flash";

export function webSearch({ searches, results }) {
  return {
    model: ({ gateway, model }) => (gateway.ownKey ? model : WEB_SEARCH_MODEL),
    tools: ({ gateway }) =>
      gateway.ownKey
        ? [{ type: "web_search_20250305", name: "web_search", max_uses: searches }]
        : [{ type: "openrouter:web_search", parameters: { engine: "exa", max_results: results } }],
    extra: ({ gateway }) => (gateway.ownKey ? {} : { max_tool_calls: searches }),
  };
}
