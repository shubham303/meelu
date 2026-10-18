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

export async function jsonCall(system, prompt, target, options = {}) {
  const { gateway, model, limits } = await resolveLlm(target);
  const chosen = options.model ? options.model({ gateway, model }) : model;
  const res = await apiFetch(`${gateway.baseUrl}/v1/messages`, {
    method: "POST",
    headers: headersFor(gateway),
    body: JSON.stringify({
      model: chosen,
      max_tokens: Math.min(MAX_OUTPUT_TOKENS, limits?.output ?? MAX_OUTPUT_TOKENS),
      system,
      messages: [{ role: "user", content: prompt }],
      ...(options.tools ? { tools: options.tools } : {}),
    }),
    signal: AbortSignal.timeout(options.timeoutMs ?? CALL_TIMEOUT_MS),
  });
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) {
    const message = payload?.error?.message || `The model call failed (${res.status}).`;
    if (res.status === 402) billingBlocked(message);
    throw new Error(message);
  }
  return jsonOf(payload);
}

export function jsonOf(payload) {
  const raw = (payload?.content ?? [])
    .filter((block) => block?.type === "text")
    .map((block) => block.text)
    .join("")
    .trim();
  const start = raw.indexOf("{");
  const end = raw.lastIndexOf("}");
  if (start === -1 || end <= start) throw new Error("The model returned no JSON object.");
  return JSON.parse(raw.slice(start, end + 1));
}
