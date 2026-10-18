import { jsonCall } from "../social-signals/llm.js";

export const SCREEN_BATCH = 15;
const SNIPPET_CHARS = 500;
const QUOTE_CHARS = 240;

function system({ brief, siteContext }) {
  return `You screen people a founder might contact personally about their product.
The founder described who they are looking for, in their own words:
"${brief}"
${siteContext ? `\nTheir site, for judging fit:\n${siteContext}\n` : ""}
For every numbered person, answer one question: does this person plausibly match the brief AND plausibly want what the site offers? Drop vendors, agencies or freelancers selling the same thing as the founder, bots, job ads, news and brand accounts (unless the brief asks for businesses), and anyone the text does not support.

Reply with ONLY a JSON object, no prose and no code fences, of this exact shape:
{"results":[{"i":0,"keep":true}]}

- i: the person's number; one result per person, every person covered.
- keep: true only when a personal message from this founder would plausibly be welcome.

Be strict: most people found by search are noise, and every one you keep costs the founder time.`;
}

export function personBlock(lead, i) {
  const quotes = (lead.evidence ?? [])
    .map((e) => `  - "${String(e.quote ?? "").slice(0, QUOTE_CHARS)}"`)
    .join("\n");
  return [
    `[${i}] ${lead.platform}${lead.name ? ` · ${lead.name}` : ""}${lead.handle ? ` (@${lead.handle})` : ""}`,
    lead.headline ? `Headline: ${lead.headline}` : "",
    lead.snippet ? `Found by: ${String(lead.snippet).slice(0, SNIPPET_CHARS)}` : "",
    quotes ? `They wrote:\n${quotes}` : "",
  ]
    .filter(Boolean)
    .join("\n");
}

export function screenVerdicts(parsed, leads) {
  const byIndex = new Map();
  for (const r of Array.isArray(parsed?.results) ? parsed.results : []) {
    const i = Number(r?.i);
    if (!Number.isInteger(i) || i < 0 || i >= leads.length || typeof r.keep !== "boolean") continue;
    byIndex.set(i, r.keep);
  }
  return leads
    .map((lead, i) => (byIndex.has(i) ? { id: lead.id, keep: byIndex.get(i) } : null))
    .filter(Boolean);
}

export async function screenBatch(leads, ctx, target) {
  const prompt = leads.map((lead, i) => personBlock(lead, i)).join("\n\n");
  return screenVerdicts(await jsonCall(system(ctx), prompt, target), leads);
}
