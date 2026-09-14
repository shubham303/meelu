const SHINGLE_WORDS = 4;

function shingles(text) {
  const words = String(text ?? "")
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .split(/\s+/)
    .filter(Boolean);
  const out = new Set();
  for (let i = 0; i + SHINGLE_WORDS <= words.length; i++) {
    out.add(words.slice(i, i + SHINGLE_WORDS).join(" "));
  }
  if (out.size === 0 && words.length > 0) out.add(words.join(" "));
  return out;
}

export function textSimilarity(a, b) {
  const sa = shingles(a);
  const sb = shingles(b);
  if (sa.size === 0 && sb.size === 0) return 1;
  if (sa.size === 0 || sb.size === 0) return 0;
  let shared = 0;
  for (const s of sa) if (sb.has(s)) shared++;
  return shared / (sa.size + sb.size - shared);
}
