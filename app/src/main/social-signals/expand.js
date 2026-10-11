import { jsonCall } from "./llm.js";

const SYSTEM = `You turn one line a marketer wrote, describing conversations they want to find on social platforms, into search terms.
Reply with ONLY a JSON object, no prose and no code fences, of this exact shape:
{"keywords":["..."],"negativeKeywords":["..."]}

- keywords: 3 to 6 short search phrases people would actually write in such a post. Two or three words each, because they run against literal keyword search APIs. Cover the problem, the thing being asked for and the names involved; if the line names a brand or product, include the name itself.
- negativeKeywords: up to 6 words whose presence marks a post as a different subject that shares the same words (another meaning of an ambiguous term, an unrelated hobby, job ads).

Use the description of the marketer's own site to read ambiguous words the way their customers would. Never invent phrases the line does not support.`;

function strings(v, cap) {
  return (Array.isArray(v) ? v : []).map((s) => String(s ?? "").trim()).filter(Boolean).slice(0, cap);
}

export async function expandLine({ line, siteContext }, target) {
  const prompt = [
    `The line: ${line}`,
    siteContext ? `The marketer's site:\n${siteContext}` : "",
  ]
    .filter(Boolean)
    .join("\n\n");
  const parsed = await jsonCall(SYSTEM, prompt, target);
  return {
    keywords: strings(parsed.keywords, 6),
    negativeKeywords: strings(parsed.negativeKeywords, 6),
  };
}
