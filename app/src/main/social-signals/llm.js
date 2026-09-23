import { query } from "@anthropic-ai/claude-agent-sdk";
import { llmEnv, resolveLlm } from "../agent/runner.js";

export async function jsonCall(system, prompt, llm) {
  const { gateway, model, anthropicKey, limits } = await resolveLlm(llm);
  const q = query({
    prompt,
    options: {
      model,
      systemPrompt: system,
      tools: [],
      allowedTools: [],
      permissionMode: "default",
      settingSources: [],
      maxTurns: 1,
      env: llmEnv(gateway, anthropicKey, limits),
    },
  });
  let output = null;
  for await (const m of q) {
    if (m.type === "result") {
      if (m.subtype !== "success" || m.is_error) {
        throw new Error(m.result || m.subtype || "The model call failed.");
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
