import { apiFetch } from "../../net.js";
import { outputCap } from "./openrouter.js";

export async function serverLimits(baseUrl, apiKey) {
  try {
    const res = await apiFetch(`${baseUrl}/props`, {
      headers: apiKey ? { authorization: `Bearer ${apiKey}` } : {},
    });
    if (!res.ok) return null;
    const props = await res.json();
    const context = Number(props.default_generation_settings?.n_ctx ?? 0);
    if (context <= 0) return null;
    return { context, output: outputCap(context, 0) };
  } catch {
    return null;
  }
}
