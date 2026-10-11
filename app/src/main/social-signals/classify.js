import { jsonCall } from "./llm.js";

export const BATCH_SIZE = 10;
const SNIPPET_CHARS = 600;
const EXAMPLE_CHARS = 240;

function system({ line, siteContext, rejected }) {
  const examples = rejected.length
    ? `\nThe marketer already marked these posts found by the same line as NOT relevant. Treat posts like them as noise:\n${rejected
        .map((r, i) => `(${i + 1}) ${r.slice(0, EXAMPLE_CHARS)}`)
        .join("\n")}\n`
    : "";
  return `You check social posts for a marketer who will decide which ones to reply to.
They described the conversations they want, in their own words:
"${line}"
${siteContext ? `\nTheir site, for judging fit:\n${siteContext}\n` : ""}${examples}
For every numbered post, ask one question: does this post match what the marketer wrote, including who is posting and what that person wants? A post on the same topic by the wrong kind of person, or wanting something else, does not match. Sharing an article, a job ad, a promotion, or another meaning of the same words does not match.

Reply with ONLY a JSON object, no prose and no code fences, of this exact shape:
{"results":[{"i":0,"fits":true,"relevance":0.0,"why":"...","angle":"..."}]}

- i: the post's number; one result per post, every post covered.
- fits: true only when a reply from this site would belong under the post.
- relevance: 0 to 1, how well it matches the line. Posts that do not fit score below 0.4.
- why: one plain sentence telling the marketer why this post is worth their time, or for a post that does not fit, why it is noise.
- angle: only when fits is true, two sentences on how a reply from this site would belong in that thread: what to answer first, and what not to pitch. Never write the reply itself. Empty string otherwise.

Be strict: most posts pulled by keyword search are noise, and the marketer's time is spent on every post you let through.`;
}

function batchPrompt(posts) {
  return posts
    .map((p, i) => {
      const bits = [
        `[${i}] ${p.platform}${p.context?.subreddit ? ` r/${p.context.subreddit}` : ""} by @${p.authorHandle ?? "unknown"}`,
        p.title ? `Title: ${p.title}` : "",
        `Text: ${(p.text ?? "").slice(0, SNIPPET_CHARS)}`,
      ];
      return bits.filter(Boolean).join("\n");
    })
    .join("\n\n");
}

function unit(n) {
  const v = Number(n);
  return Number.isFinite(v) ? Math.min(Math.max(v, 0), 1) : 0;
}

export async function judgeBatch(posts, ctx, target) {
  const parsed = await jsonCall(system(ctx), batchPrompt(posts), target);
  const byIndex = new Map();
  for (const r of Array.isArray(parsed.results) ? parsed.results : []) {
    const i = Number(r?.i);
    if (!Number.isInteger(i) || i < 0 || i >= posts.length) continue;
    const fits = r.fits === true;
    byIndex.set(i, {
      fits,
      relevance: unit(r.relevance),
      why: String(r.why ?? "").trim() || null,
      angle: fits ? String(r.angle ?? "").trim() || null : null,
    });
  }
  return posts.map((p, i) => ({
    ...p,
    ...(byIndex.get(i) ?? { fits: false, relevance: 0, why: null, angle: null }),
  }));
}
