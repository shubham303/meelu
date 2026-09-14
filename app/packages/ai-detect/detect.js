import { chunkText, countWords, normalise } from "./chunk.js";
import { MAX_WORDS, MIN_WORDS_TO_RUN } from "./constants.js";
import { analyse } from "./score.js";

const WORD = /\S+/g;

function limitWords(text, max) {
  WORD.lastIndex = 0;
  let seen = 0;
  let match;
  while ((match = WORD.exec(text)) !== null) {
    seen += 1;
    if (seen === max) return text.slice(0, match.index + match[0].length);
  }
  return text;
}

export async function detect(input, scoreChunks, { maxWords = MAX_WORDS } = {}) {
  const text = normalise(limitWords(normalise(input), maxWords));
  const words = countWords(text);
  if (words < MIN_WORDS_TO_RUN) return { ok: false, reason: "too-short", words, text };
  const chunks = chunkText(text);
  const scores = await scoreChunks(chunks.map((c) => c.text));
  const scored = chunks.map((chunk, i) => ({ ...chunk, ai: Math.min(1, Math.max(0, Number(scores[i]) || 0)) }));
  return { ok: true, ...analyse(scored, text) };
}
