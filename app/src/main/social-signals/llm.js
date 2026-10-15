import { query } from "@anthropic-ai/claude-agent-sdk";
import { claudeExecutable, llmEnv, resolveLlm } from "../agent/runner.js";

const BILLING_ERROR = /^API Error: 402\s*/;
let billingBlocked = () => {};

export function onBillingBlocked(listener) {
  billingBlocked = listener;
}

export async function jsonCall(system, prompt, target) {
  const { gateway, model, limits } = await resolveLlm(target);
  const q = query({
    prompt,
    options: {
      model,
      systemPrompt: system,
      tools: [],
      allowedTools: [],
      permissionMode: "default",
      settingSources: [],
      strictMcpConfig: true,
      maxTurns: 1,
      ...claudeExecutable(),
      env: llmEnv(gateway, limits),
    },
  });
  let output = null;
  for await (const m of q) {
    if (m.type === "result") {
      if (m.subtype !== "success" || m.is_error) {
        const reason = m.result || m.subtype || "The model call failed.";
        if (BILLING_ERROR.test(reason)) {
          const message = reason.replace(BILLING_ERROR, "");
          billingBlocked(message);
          throw new Error(message);
        }
        throw new Error(reason);
      }
      output = m.result;
    }
  }
  const raw = String(output ?? "").trim();
  const start = raw.indexOf("{");
  const end = raw.lastIndexOf("}");
  if (start === -1 || end <= start) throw new Error("The model returned no JSON object.");
  return JSON.parse(raw.slice(start, end + 1));
}
