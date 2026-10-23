import { jsonCall } from "./llm.js";

export const BATCH_SIZE = 10;
const SNIPPET_CHARS = 600;

function system({ line, siteContext }) {
  return `You check social posts for a marketer who will decide which ones to reply to.
They described the conversations they want, in their own words:
"${line}"
${siteContext ? `\nTheir site, only for writing the angle:\n${siteContext}\n` : ""}
For every numbered post, ask one question: does this post match what the marketer wrote? Judge only by what they wrote and add no rule of your own.

Reply with ONLY a JSON object, no prose and no code fences, of this exact shape:
{"results":[{"i":0,"fits":true,"why":"...","angle":"..."}]}

- i: the post's number; one result per post, every post covered.
- fits: true when the post matches what the marketer wrote, false otherwise.
- why: one plain sentence telling the marketer how the post matches what they wrote, or for a post that does not, why not.
- angle: only when fits is true, two sentences on how a reply from this site would belong in that thread: what to answer first, and what not to pitch. Never write the reply itself. Empty string otherwise.`;
}

function batchPrompt(posts) {
  return posts
    .map((p, i) => {
      const bits = [
        `[${i}] ${p.platform}${p.context?.subreddit ? ` r/${p.context.subreddit}` : ""} by ${p.authorHandle ? `@${p.authorHandle}` : (p.authorName ?? "unknown")}`,
        p.title ? `Title: ${p.title}` : "",
        `Text: ${(p.text ?? "").slice(0, SNIPPET_CHARS)}`,
      ];
      return bits.filter(Boolean).join("\n");
    })
    .join("\n\n");
}

export async function judgeBatch(posts, ctx, target) {
  return verdictsFor(await jsonCall(system(ctx), batchPrompt(posts), target), posts);
}

export function verdictsFor(parsed, posts) {
  const byIndex = new Map();
  for (const r of Array.isArray(parsed?.results) ? parsed.results : []) {
    const i = Number(r?.i);
    if (!Number.isInteger(i) || i < 0 || i >= posts.length || typeof r.fits !== "boolean") continue;
    byIndex.set(i, {
      fits: r.fits,
      why: String(r.why ?? "").trim() || null,
      angle: r.fits ? String(r.angle ?? "").trim() || null : null,
    });
  }
  return posts.map((p, i) => ({ post: p, verdict: byIndex.get(i) ?? null }));
}
