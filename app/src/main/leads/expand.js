import { jsonCall } from "../social-signals/llm.js";

const SYSTEM = `You turn a lead campaign brief into search queries for finding prospects.
Reply with ONLY a JSON object — no prose, no code fences — of this exact shape:
{"queries":["..."]}

- queries: 3 to 5 short search phrases that would surface the people the brief describes — the audience, their role, the communities and topics they post about. Two to five words each; they run against literal search APIs.
- Write queries that find PEOPLE (practitioners, founders, creators), not articles about the topic.`;

function strings(v, cap) {
  return (Array.isArray(v) ? v : []).map((s) => String(s ?? "").trim()).filter(Boolean).slice(0, cap);
}

export async function expandBrief(campaign, siteContext, llm) {
  const prompt = [
    `Audience: ${campaign.audience ?? ""}`,
    siteContext ? `About the site this campaign serves:\n${siteContext}` : "",
  ]
    .filter(Boolean)
    .join("\n\n");
  const parsed = await jsonCall(SYSTEM, prompt, llm);
  const queries = strings(parsed.queries, 5);
  if (queries.length === 0 && campaign.audience) queries.push(String(campaign.audience).slice(0, 80));
  return queries;
}
