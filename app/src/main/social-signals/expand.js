import { jsonCall } from "./llm.js";

const SYSTEM = `You expand a social-listening query into search terms.
Reply with ONLY a JSON object — no prose, no code fences — of this exact shape:
{"keywords":["..."],"questionPatterns":["..."],"subredditHints":["..."],"negativeKeywords":["..."]}

- keywords: 3 to 6 short search phrases people would actually type or write in posts. Always include the given topic itself first. Keep them short — two or three words each — because they run against literal keyword search APIs.
- questionPatterns: 2 to 4 phrasings of the questions people ask around this topic ("how do I audit my site", "best tool for X").
- subredditHints: up to 4 subreddit names (without r/) where this is discussed.
- negativeKeywords: words whose presence marks a post as a different subject entirely.

In topic mode, expand toward the problems and tools people ask about. In brand mode, expand toward the brand name, close misspellings, "vs" comparison phrases and "alternative to" phrases. Never invent expansions the topic does not support.`;

function strings(v, cap) {
  return (Array.isArray(v) ? v : []).map((s) => String(s ?? "").trim()).filter(Boolean).slice(0, cap);
}

export async function expandQuery({ mode, topic, siteContext }, llm) {
  const prompt = [
    `Mode: ${mode === "brand" ? "brand (find mentions of this brand)" : "topic (find people discussing this topic)"}`,
    `Topic: ${topic}`,
    siteContext ? `About the product this search serves:\n${siteContext}` : "",
  ]
    .filter(Boolean)
    .join("\n\n");
  const parsed = await jsonCall(SYSTEM, prompt, llm);
  const keywords = strings(parsed.keywords, 6);
  const clean = topic.trim();
  if (clean && !keywords.some((k) => k.toLowerCase() === clean.toLowerCase())) keywords.unshift(clean);
  return {
    keywords: keywords.slice(0, 6),
    questionPatterns: strings(parsed.questionPatterns, 4),
    subredditHints: strings(parsed.subredditHints, 4),
    negativeKeywords: strings(parsed.negativeKeywords, 6),
  };
}
