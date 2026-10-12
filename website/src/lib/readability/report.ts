import type { ReadabilityReport } from "./analyse";

function cell(value: unknown): string {
  if (value === null || value === undefined) return "";
  const text = String(value);
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function toCsv(headers: string[], rows: unknown[][]): string {
  return [headers, ...rows].map((row) => row.map(cell).join(",")).join("\r\n");
}

/** A plain-text report, the thing the copy button puts on the clipboard. */
export function textReport(report: ReadabilityReport): string {
  const lines: string[] = [];
  lines.push("READABILITY REPORT");
  lines.push("Meelu readability checker — meelu.dev/tools/readability-checker");
  lines.push("");
  lines.push(`Flesch Reading Ease   ${report.fleschDisplay}  (${report.band.label}, ${report.band.school})`);
  lines.push(`Grade level           ${report.gradeLabel}  (Flesch-Kincaid ${report.scores[1]?.display ?? ""})`);
  lines.push(`Audience              ${report.gradeAudience}`);
  lines.push("");
  lines.push("SCORES");
  for (const score of report.scores) {
    lines.push(`  ${score.name.padEnd(28)} ${score.display.padStart(6)}`);
    lines.push(`    ${score.formula}`);
    lines.push(`    = ${score.worked}`);
  }
  lines.push("");
  lines.push("COUNTS");
  const c = report.counts;
  lines.push(`  Words ${c.words} · Sentences ${c.sentences} · Paragraphs ${c.paragraphs} · Syllables ${c.syllables}`);
  lines.push(`  Characters ${c.characters} (${c.charactersNoSpaces} without spaces) · Letters and digits ${c.letters}`);
  lines.push(`  Average sentence ${report.averages.wordsPerSentence} words · Average word ${report.averages.syllablesPerWord} syllables`);
  lines.push(`  Words of 3+ syllables ${c.polysyllables} · Complex words (Fog) ${c.complexWords}`);
  lines.push(`  Long sentences (${c.longSentences}) · Passive sentences (${c.passiveSentences}) · Adverbs (${c.adverbs})`);
  lines.push(`  Reading time ${report.readingTime} at 238 words a minute`);
  lines.push("");
  lines.push("WHAT TO CHANGE");
  for (const rec of report.recommendations) {
    lines.push(`  [${rec.tone.toUpperCase()}] ${rec.title}`);
    lines.push(`    ${rec.body}`);
  }
  if (report.longList.length > 0) {
    lines.push("");
    lines.push("LONGEST SENTENCES");
    for (const index of report.longList.slice(0, 20)) {
      const sentence = report.sentences[index];
      lines.push(`  (${sentence.words} words) ${sentence.text}`);
    }
  }
  if (report.passiveList.length > 0) {
    lines.push("");
    lines.push("POSSIBLE PASSIVE VOICE (pattern match, check each one)");
    for (const hit of report.passiveList.slice(0, 20)) {
      lines.push(`  "${hit.phrase}" — sentence ${hit.sentence + 1}`);
    }
  }
  lines.push("");
  lines.push("Computed in the browser. No text was uploaded anywhere.");
  return lines.join("\n");
}

/** One row per sentence, which is the shape you edit in. */
export function sentencesCsv(report: ReadabilityReport): string {
  return toCsv(
    [
      "Sentence #",
      "Paragraph #",
      "Words",
      "Syllables",
      "Flesch-Kincaid grade",
      "Flags",
      "Complex words",
      "Adverbs",
      "Passive phrases",
      "Text",
    ],
    report.sentences.map((s) => [
      s.index + 1,
      s.paragraph + 1,
      s.words,
      s.syllables,
      s.grade.toFixed(1),
      s.flags.join(" "),
      s.complexWords.join(" "),
      s.adverbs.join(" "),
      s.passive.join(" | "),
      s.text,
    ]),
  );
}

/** The scores and counts, one metric per row. */
export function scoresCsv(report: ReadabilityReport): string {
  const rows: unknown[][] = report.scores.map((score) => [
    score.name,
    score.display,
    score.unit === "score" ? "0-100 score" : "US grade",
    score.formula,
    score.worked,
  ]);
  const c = report.counts;
  const counts: Array<[string, number | string]> = [
    ["Words", c.words],
    ["Sentences", c.sentences],
    ["Paragraphs", c.paragraphs],
    ["Syllables", c.syllables],
    ["Characters", c.characters],
    ["Characters without spaces", c.charactersNoSpaces],
    ["Letters and digits", c.letters],
    ["Average words per sentence", report.averages.wordsPerSentence],
    ["Average syllables per word", report.averages.syllablesPerWord],
    ["Average letters per word", report.averages.lettersPerWord],
    ["Words of 3+ syllables", c.polysyllables],
    ["Complex words (Gunning Fog rules)", c.complexWords],
    ["Long sentences (25+ words)", c.longSentences],
    ["Sentences with possible passive voice", c.passiveSentences],
    ["Adverbs ending in -ly", c.adverbs],
    ["Reading time", report.readingTime],
  ];
  for (const [name, value] of counts) rows.push([name, value, "count", "", ""]);
  return toCsv(["Metric", "Value", "Kind", "Formula", "Worked"], rows);
}

export function fileStem(): string {
  const now = new Date();
  const stamp = [
    now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, "0"),
    String(now.getDate()).padStart(2, "0"),
  ].join("-");
  return `readability-${stamp}`;
}
