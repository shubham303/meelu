import { jsonCall } from "./llm.js";

export const BATCH_SIZE = 10;
const SNIPPET_CHARS = 600;
const INTENTS = new Set([
  "seeking_tool",
  "seeking_help",
  "complaining",
  "recommending",
  "praising",
  "discussion",
  "other",
]);
const SENTIMENTS = new Set(["positive", "neutral", "negative"]);

function system({ mode, topic, siteContext }) {
  return `You classify social posts for a marketer doing social listening.
The search is in ${mode === "brand" ? `brand mode: the marketer is watching for mentions of "${topic}"` : `topic mode: the marketer wants conversations about "${topic}" they could usefully join`}.
${siteContext ? `Their product, for judging relevance:\n${siteContext}\n` : ""}
For every numbered post, judge it on its own text. Reply with ONLY a JSON object — no prose, no code fences — of this exact shape:
{"results":[{"i":0,"isQuestion":false,"isMention":false,"intent":"seeking_tool","sentiment":"neutral","relevance":0.0,"keepReason":"..."}]}

- i: the post's number, one result per post, every post covered.
- isQuestion: the author is asking something.
- isMention: the post mentions the searched topic or brand by name.
- intent: one of seeking_tool, seeking_help, complaining, recommending, praising, discussion, other.
- sentiment: positive, neutral or negative toward the subject.
- relevance: 0 to 1 — how much a reply from this marketer would belong under this post. A post merely sharing an article scores low; a person asking for exactly what the product does scores high. Posts about an unrelated meaning of the same words score near 0.
- keepReason: one plain sentence telling the marketer why this post is worth their attention. For posts below 0.4 relevance, one sentence on why it is noise.

Be strict: most posts pulled by keyword search are noise, and the marketer's time is spent on every post you let through.`;
}

function batchPrompt(posts) {
  return posts
    .map((p, i) => {
      const bits = [
        `[${i}] ${p.platform}${p.context?.subreddit ? ` r/${p.context.subreddit}` : ""} by @${p.author.handle}`,
        p.title ? `Title: ${p.title}` : "",
        `Text: ${p.text.slice(0, SNIPPET_CHARS)}`,
      ];
      return bits.filter(Boolean).join("\n");
    })
    .join("\n\n");
}

export async function classifyBatch(posts, ctx, llm) {
  const parsed = await jsonCall(system(ctx), batchPrompt(posts), llm);
  const byIndex = new Map();
  for (const r of Array.isArray(parsed.results) ? parsed.results : []) {
    const i = Number(r?.i);
    if (!Number.isInteger(i) || i < 0 || i >= posts.length) continue;
    const relevance = Number(r.relevance);
    byIndex.set(i, {
      classification: {
        isQuestion: Boolean(r.isQuestion),
        isMention: Boolean(r.isMention),
        intent: INTENTS.has(r.intent) ? r.intent : "other",
        sentiment: SENTIMENTS.has(r.sentiment) ? r.sentiment : "neutral",
      },
      relevanceScore: Number.isFinite(relevance) ? Math.min(Math.max(relevance, 0), 1) : 0,
      keepReason: String(r.keepReason ?? "").trim() || null,
    });
  }
  return posts.map((p, i) => {
    const judged = byIndex.get(i);
    if (!judged) return { ...p, relevanceScore: 0, keepReason: null };
    return { ...p, ...judged };
  });
}
