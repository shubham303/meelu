import { jsonCall } from "./llm.js";

const KEYWORDS_PER_LINE = 2;

const SYSTEM = `You turn lines a marketer wrote, each describing conversations they want to find on social platforms, into search terms.
Reply with ONLY a JSON object, no prose and no code fences, of this exact shape:
{"lines":[{"id":"...","keywords":["...","..."]}]}

- One entry per line, with the line's id exactly as given.
- keywords: exactly ${KEYWORDS_PER_LINE} short search phrases people would actually write in such a post. Two or three words each, because they run against literal keyword search APIs. Pick the two phrases most likely to find the conversation the line describes; if the line names a brand or product, one of them is the name itself.
- The two phrases of a line must differ.

Use the description of the marketer's own site to read ambiguous words the way their customers would. Never invent phrases the line does not support.`;

function clean(keywords) {
  const seen = new Set();
  for (const k of Array.isArray(keywords) ? keywords : []) {
    const phrase = String(k ?? "").toLowerCase().split(/\s+/).filter(Boolean).join(" ");
    if (phrase) seen.add(phrase);
  }
  return [...seen].slice(0, KEYWORDS_PER_LINE);
}

export async function expandLines({ lines, siteContext }, target) {
  if (lines.length === 0) return new Map();
  const prompt = [
    `The lines:\n${lines.map((l) => JSON.stringify({ id: l.id, line: l.text })).join("\n")}`,
    siteContext ? `The marketer's site:\n${siteContext}` : "",
  ]
    .filter(Boolean)
    .join("\n\n");
  return keywordsByLine(await jsonCall(SYSTEM, prompt, target), lines);
}

export function keywordsByLine(parsed, lines) {
  const ids = new Set(lines.map((l) => l.id));
  const out = new Map();
  for (const entry of Array.isArray(parsed?.lines) ? parsed.lines : []) {
    const keywords = clean(entry?.keywords);
    if (keywords.length === KEYWORDS_PER_LINE && ids.has(entry?.id)) out.set(entry.id, keywords);
  }
  return out;
}
