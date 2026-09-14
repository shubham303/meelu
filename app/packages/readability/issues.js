import { analyse, LONG_SENTENCE, VERY_LONG_SENTENCE } from "./analyse.js";

const DOCUMENT_RECOMMENDATIONS = new Set(["avg-length", "paragraphs", "rhythm", "adverbs", "clear"]);

function proseFromMarkdown(markdown) {
  const lines = [];
  let inFence = false;
  for (const raw of String(markdown ?? "").split("\n")) {
    const line = raw.replace(/\r$/, "");
    if (/^\s*(```|~~~)/.test(line)) {
      inFence = !inFence;
      lines.push("");
      continue;
    }
    if (inFence) {
      lines.push("");
      continue;
    }
    if (/^\s*!\[[^\]]*\]\([^)]*\)\s*$/.test(line) || /^\s*(---+|\*\*\*+|\|.*\|)\s*$/.test(line)) {
      lines.push("");
      continue;
    }
    const stripped = line.replace(/^\s{0,3}(#{1,6}\s+|>\s?|[-*+]\s+|\d+[.)]\s+)/, "");
    lines.push(stripped);
  }
  return lines.join("\n");
}

function sentenceIssue(sentence, grade) {
  const anchorText = sentence.text.trim();
  if (sentence.flags.includes("very-long")) {
    return {
      code: "very_long_sentence",
      title: `Sentence runs to ${sentence.words} words`,
      detail: `Past ${VERY_LONG_SENTENCE} words a reader loses the start before reaching the end. Find the conjunction in the middle and put a full stop there.`,
      anchorText,
    };
  }
  if (sentence.flags.includes("long")) {
    return {
      code: "long_sentence",
      title: `Long sentence, ${sentence.words} words`,
      detail: `Over ${LONG_SENTENCE} words. Splitting it costs nothing.`,
      anchorText,
    };
  }
  if (sentence.flags.includes("passive")) {
    return {
      code: "passive_voice",
      title: "Passive voice",
      detail: `"${sentence.passive[0]}" hides who did the thing. Check it — this detection is a pattern match, not a parser.`,
      anchorText,
    };
  }
  if (sentence.flags.includes("complex")) {
    return {
      code: "complex_words",
      title: `${sentence.complexWords.length} long words in one sentence`,
      detail: `${sentence.complexWords.slice(0, 4).join(", ")} — most three-syllable words have a shorter twin. This sentence reads at grade ${Math.round(grade)}.`,
      anchorText,
    };
  }
  return null;
}

export function checkReadability(markdown) {
  const report = analyse(proseFromMarkdown(markdown));
  if (report.empty) {
    return { grade: null, flesch: null, gradeLabel: null, reliable: false, issues: [] };
  }
  const issues = [];
  const seen = new Set();
  for (const sentence of report.sentences) {
    const issue = sentenceIssue(sentence, sentence.grade);
    if (!issue || seen.has(issue.anchorText)) continue;
    seen.add(issue.anchorText);
    issues.push(issue);
  }
  for (const rec of report.recommendations) {
    if (!DOCUMENT_RECOMMENDATIONS.has(rec.id) || rec.id === "clear" || rec.tone === "good") continue;
    issues.push({ code: rec.id.replace(/-/g, "_"), title: rec.title, detail: rec.body, anchorText: null });
  }
  return {
    grade: report.grade,
    gradeLabel: report.gradeLabel,
    flesch: report.flesch,
    reliable: report.reliable,
    issues,
  };
}
