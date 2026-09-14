import { OPENROUTER_BASE_URL } from "../../config.js";
import { apiFetch } from "../../net.js";

const OUTPUT_CEILING = 8192;
const OUTPUT_SHARE = 0.2;

const cache = new Map();

export function outputCap(context, completion) {
  const room = Math.floor(context * OUTPUT_SHARE);
  const bounds = [completion, room, OUTPUT_CEILING].filter((n) => n > 0);
  return bounds.length === 0 ? 0 : Math.max(1024, Math.min(...bounds));
}

export async function modelLimits(model, apiKey) {
  if (!model) return null;
  if (cache.has(model)) return cache.get(model);

  let limits = null;
  try {
    const res = await apiFetch(`${OPENROUTER_BASE_URL}/v1/models`, {
      headers: apiKey ? { authorization: `Bearer ${apiKey}` } : {},
    });
    if (res.ok) {
      const { data } = await res.json();
      const entry = (data ?? []).find((m) => m.id === model);
      if (entry) {
        const context = Number(entry.top_provider?.context_length ?? entry.context_length ?? 0);
        const completion = Number(entry.top_provider?.max_completion_tokens ?? 0);
        if (context > 0) limits = { context, output: outputCap(context, completion) };
      }
    }
  } catch {
    limits = null;
  }

  cache.set(model, limits);
  return limits;
}
