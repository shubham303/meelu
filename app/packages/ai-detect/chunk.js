import { MAX_CHUNK_WORDS, MIN_CHUNK_WORDS, SOFT_BREAK_WORDS, TARGET_CHUNK_WORDS } from "./constants.js";

export function normalise(input) {
  return String(input ?? "")
    .replace(/\r\n?/g, "\n")
    .replace(/[ \t]+/g, " ")
    .replace(/ ?\n ?/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function countWords(text) {
  const matched = text.match(/[\p{L}\p{N}][\p{L}\p{N}'’-]*/gu);
  return matched ? matched.length : 0;
}

function sentences(normalised) {
  const out = [];
  const paraRe = /[^\n]+/g;
  let para;
  while ((para = paraRe.exec(normalised)) !== null) {
    const base = para.index;
    const body = para[0];
    const found = [];
    const sentRe = /[^.!?…]+(?:[.!?…]+["'”’)\]]*|$)/g;
    let match;
    while ((match = sentRe.exec(body)) !== null) {
      if (!match[0].trim()) continue;
      found.push({ start: base + match.index, end: base + match.index + match[0].length });
    }
    if (found.length === 0) found.push({ start: base, end: base + body.length });
    found.forEach((span, i) => {
      out.push({
        start: span.start,
        end: span.end,
        words: countWords(normalised.slice(span.start, span.end)),
        endsParagraph: i === found.length - 1,
      });
    });
  }
  return out;
}

export function chunkText(normalised) {
  const chunks = [];
  const all = sentences(normalised);

  let start = null;
  let end = 0;
  let words = 0;

  const flush = () => {
    if (start === null) return;
    const text = normalised.slice(start, end).trim();
    if (text) chunks.push({ index: chunks.length, text, words, start, end });
    start = null;
    end = 0;
    words = 0;
  };

  for (const sentence of all) {
    if (sentence.words > MAX_CHUNK_WORDS) {
      flush();
      const slice = normalised.slice(sentence.start, sentence.end);
      const wordRe = /\S+/g;
      let pieceStart = sentence.start;
      let seen = 0;
      let match;
      while ((match = wordRe.exec(slice)) !== null) {
        seen += 1;
        if (seen >= TARGET_CHUNK_WORDS) {
          const wordEnd = sentence.start + match.index + match[0].length;
          const text = normalised.slice(pieceStart, wordEnd).trim();
          if (text) chunks.push({ index: chunks.length, text, words: seen, start: pieceStart, end: wordEnd });
          pieceStart = wordEnd;
          seen = 0;
        }
      }
      if (seen > 0) {
        start = pieceStart;
        end = sentence.end;
        words = seen;
      }
      continue;
    }

    if (start === null) start = sentence.start;
    end = sentence.end;
    words += sentence.words;

    if (words >= TARGET_CHUNK_WORDS) flush();
    else if (sentence.endsParagraph && words >= SOFT_BREAK_WORDS) flush();
  }
  flush();

  for (let i = chunks.length - 1; i >= 0 && chunks.length > 1; i--) {
    const chunk = chunks[i];
    if (chunk.words >= MIN_CHUNK_WORDS) continue;
    const prev = i > 0 ? chunks[i - 1] : null;
    const next = i < chunks.length - 1 ? chunks[i + 1] : null;
    let into = null;
    if (prev && next) into = prev.words <= next.words ? prev : next;
    else into = prev ?? next;
    if (!into) continue;
    if (into.words + chunk.words > MAX_CHUNK_WORDS) continue;
    into.start = Math.min(into.start, chunk.start);
    into.end = Math.max(into.end, chunk.end);
    into.words += chunk.words;
    into.text = normalised.slice(into.start, into.end).trim();
    chunks.splice(i, 1);
  }

  chunks.sort((a, b) => a.start - b.start);
  chunks.forEach((chunk, i) => {
    chunk.index = i;
  });
  return chunks;
}

export function sentenceSpans(normalised) {
  const out = [];
  for (const sentence of sentences(normalised)) {
    const raw = normalised.slice(sentence.start, sentence.end);
    const lead = raw.length - raw.trimStart().length;
    const trail = raw.length - raw.trimEnd().length;
    const start = sentence.start + lead;
    const end = sentence.end - trail;
    if (end <= start) continue;
    out.push({ index: out.length + 1, start, end, text: normalised.slice(start, end), words: sentence.words });
  }
  return out;
}
