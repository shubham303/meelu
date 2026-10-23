import { jsonCall } from "../social-signals/llm.js";

export const JUDGE_BATCH = 5;
const SNIPPET_CHARS = 600;
const ITEM_CHARS = 400;
const MAX_ITEMS = 12;
const MAX_EVIDENCE = 3;

function system({ brief, siteContext }) {
  return `You explain to a founder why each person they found is worth contacting personally. The founder writes and sends every message themselves.
The founder described who they are looking for:
"${brief}"
${siteContext ? `\nTheir site, only for writing the angle:\n${siteContext}\n` : ""}
Every numbered person below already passed a check that they fit the brief. Each comes with what surfaced them and numbered items of their own recent activity.

Reply with ONLY a JSON object, no prose and no code fences, of this exact shape:
{"results":[{"i":0,"why":"...","angle":"...","evidence":[0,2]}]}

- i: the person's number; one result per person, every person covered.
- why: one plain sentence telling the founder why this person fits the brief, citing what shows it.
- angle: one sentence on what to open with. Never write the message itself.
- evidence: the numbers (up to ${MAX_EVIDENCE}) of the items that back up why, or an empty list when the fit comes from their profile alone. Only numbers shown for that person.`;
}

export function itemsOf(lead) {
  const items = [];
  for (const e of lead.evidence ?? []) {
    if (e?.url && e?.quote) items.push({ url: e.url, quote: String(e.quote), at: e.at ?? null });
  }
  for (const a of lead.activity ?? []) {
    if (a?.url && a?.text && !items.some((i) => i.url === a.url)) {
      items.push({ url: a.url, quote: String(a.text), at: a.at ?? null, kind: a.kind ?? null });
    }
  }
  return items.slice(0, MAX_ITEMS);
}

export function judgeBlock(lead, i) {
  const items = itemsOf(lead)
    .map(
      (item, n) =>
        `  (${n})${item.kind ? ` ${item.kind}` : ""}${item.at ? ` ${String(item.at).slice(0, 10)}` : ""}: ${item.quote.slice(0, ITEM_CHARS)}`,
    )
    .join("\n");
  return [
    `[${i}] ${lead.platform}${lead.name ? ` · ${lead.name}` : ""}${lead.handle ? ` (@${lead.handle})` : ""}`,
    lead.headline ? `Headline: ${lead.headline}` : "",
    lead.snippet ? `Found by: ${String(lead.snippet).slice(0, SNIPPET_CHARS)}` : "",
    items ? `Their items:\n${items}` : "No activity found.",
  ]
    .filter(Boolean)
    .join("\n");
}

export function judgeVerdicts(parsed, leads) {
  const byIndex = new Map();
  for (const r of Array.isArray(parsed?.results) ? parsed.results : []) {
    const i = Number(r?.i);
    if (!Number.isInteger(i) || i < 0 || i >= leads.length) continue;
    byIndex.set(i, r);
  }
  const out = [];
  leads.forEach((lead, i) => {
    const r = byIndex.get(i);
    if (!r) return;
    const items = itemsOf(lead);
    const picked = [];
    for (const n of Array.isArray(r.evidence) ? r.evidence : []) {
      const item = items[Number(n)];
      if (Number.isInteger(Number(n)) && item && !picked.some((p) => p.url === item.url)) {
        picked.push({ url: item.url, quote: item.quote, at: item.at });
      }
    }
    out.push({
      id: lead.id,
      keep: true,
      reason: String(r.why ?? "").trim() || null,
      angle: String(r.angle ?? "").trim() || null,
      evidence: picked.slice(0, MAX_EVIDENCE),
    });
  });
  return out;
}

export async function judgeBatch(leads, ctx, target) {
  const prompt = leads.map((lead, i) => judgeBlock(lead, i)).join("\n\n");
  return judgeVerdicts(await jsonCall(system(ctx), prompt, target), leads);
}
