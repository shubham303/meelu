import { tool as sdkTool } from "@anthropic-ai/claude-agent-sdk";
import { ProviderError, errorPayload } from "./errors.js";

export function defineTools(FacadeClass, specs) {
  for (const spec of specs) {
    if (typeof FacadeClass.prototype[spec.method] !== "function") {
      throw new Error(`${FacadeClass.name} has no method ${spec.method} for tool ${spec.name}`);
    }
  }
  FacadeClass.TOOLS = specs;
  return specs;
}

export function toolNames(FacadeClass) {
  return (FacadeClass.TOOLS ?? []).map((t) => t.name);
}

export function toolHandlers(instance) {
  const map = new Map();
  for (const spec of instance.constructor.TOOLS ?? []) {
    map.set(spec.name, (input) => instance[spec.method](input ?? {}));
  }
  return map;
}

function textResult(value, isError = false) {
  const text = typeof value === "string" ? value : JSON.stringify(value ?? null);
  return { content: [{ type: "text", text }], ...(isError ? { isError: true } : {}) };
}

export function mcpTools(instance, { allowed = null, siteId = null } = {}) {
  const out = [];
  for (const spec of instance.constructor.TOOLS ?? []) {
    if (allowed && !allowed.has(spec.name)) continue;
    const shape = spec.input?.shape ?? {};
    out.push(
      sdkTool(spec.name, spec.description, shape, async (input) => {
        try {
          const result = await instance[spec.method]({ ...(siteId ? { siteId } : {}), ...input });
          return textResult(result);
        } catch (err) {
          if (err instanceof ProviderError) return textResult(errorPayload(err), true);
          return textResult({ message: err instanceof Error ? err.message : String(err) }, true);
        }
      }),
    );
  }
  return out;
}
