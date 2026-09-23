import { jsonCall } from "../social-signals/llm.js";

export const BATCH_SIZE = 8;

const SYSTEM = `You judge whether prospects fit a lead campaign.
Reply with ONLY a JSON object — no prose, no code fences — of this exact shape:
{"leads":[{"index":0,"fitScore":0.0,"fitReason":"...","evidence":[{"quote":"...","url":"..."}]}]}

- One entry per prospect, using the prospect's given index.
- fitScore: 0 to 1 — how well this prospect matches the campaign's audience. Below 0.3 for clearly off-target people; above 0.7 only when the prospect's own words show the fit.
- fitReason: one short sentence grounded in the prospect's text.
- evidence: up to 2 short verbatim quotes from the prospect's text, each with the source url it came from. Never invent quotes.`;

function clamp01(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return 0;
  return Math.min(1, Math.max(0, n));
}

function cleanEvidence(list, fallbackUrl) {
  return (Array.isArray(list) ? list : [])
    .map((e) => ({
      quote: String(e?.quote ?? "").trim().slice(0, 400),
      url: String(e?.url ?? fallbackUrl ?? "").trim(),
    }))
    .filter((e) => e.quote)
    .slice(0, 2);
}

export async function qualifyBatch(prospects, campaign, siteContext, llm) {
  const brief = [
    `Audience: ${campaign.audience ?? ""}`,
    siteContext ? `About the site:\n${siteContext}` : "",
  ]
    .filter(Boolean)
    .join("\n");
  const listing = prospects
    .map((p, i) =>
      [
        `[${i}] ${p.name}`,
        p.role ? `role: ${p.role}` : "",
        p.company ? `company: ${p.company}` : "",
        `source: ${p.source} ${p.sourceUrl ?? ""}`,
        p.rawText ? `text: ${p.rawText.slice(0, 1200)}` : "",
      ]
        .filter(Boolean)
        .join("\n"),
    )
    .join("\n\n");
  const parsed = await jsonCall(SYSTEM, `Campaign:\n${brief}\n\nProspects:\n${listing}`, llm);
  const byIndex = new Map();
  for (const row of Array.isArray(parsed.leads) ? parsed.leads : []) {
    const i = Math.floor(Number(row?.index));
    if (Number.isInteger(i) && i >= 0 && i < prospects.length) byIndex.set(i, row);
  }
  return prospects.map((p, i) => {
    const row = byIndex.get(i);
    return {
      ...p,
      fitScore: row ? clamp01(row.fitScore) : 0,
      fitReason: row ? String(row.fitReason ?? "").trim().slice(0, 500) || null : null,
      evidence: cleanEvidence(row?.evidence, p.sourceUrl),
    };
  });
}
