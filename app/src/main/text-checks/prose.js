const BLOCK_PREFIX = /^\s{0,3}(#{1,6}\s+|>\s?|[-*+]\s+|\d+[.)]\s+|\|\s*)/;
const SKIP_LINE = /^\s*(!\[[^\]]*\]\([^)]*\)|---+|\*\*\*+|\|.*\|)\s*$/;

export function markdownParagraphs(markdown) {
  const source = String(markdown ?? "");
  const out = [];
  let inFence = false;
  let offset = 0;
  let block = null;

  const close = () => {
    if (block && block.lines.length) {
      const raw = source.slice(block.start, block.end);
      out.push({ raw, text: block.lines.join(" "), start: block.start, end: block.end });
    }
    block = null;
  };

  for (const rawLine of source.split("\n")) {
    const lineStart = offset;
    offset += rawLine.length + 1;
    const line = rawLine.replace(/\r$/, "");
    if (/^\s*(```|~~~)/.test(line)) {
      inFence = !inFence;
      close();
      continue;
    }
    if (inFence || SKIP_LINE.test(line)) {
      close();
      continue;
    }
    if (!line.trim()) {
      close();
      continue;
    }
    const stripped = line.replace(BLOCK_PREFIX, "").trim();
    if (!stripped) {
      close();
      continue;
    }
    if (!block) block = { start: lineStart, end: lineStart + line.length, lines: [] };
    block.end = lineStart + line.length;
    block.lines.push(stripped);
  }
  close();
  return out;
}

export function pageParagraphs(bodyText) {
  const out = [];
  for (const line of String(bodyText ?? "").split("\n")) {
    const text = line.replace(BLOCK_PREFIX, "").trim();
    if (text) out.push(text);
  }
  return out;
}
