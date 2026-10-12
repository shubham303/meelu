"use client";

import { useMemo, useState } from "react";
import {
  Check,
  ChevronDown,
  Clipboard,
  Download,
  FileSpreadsheet,
  Sigma,
} from "lucide-react";
import type { ReadabilityReport, SentenceInfo } from "@/lib/readability/analyse";
import { LONG_SENTENCE, RELIABLE_WORD_COUNT } from "@/lib/readability/analyse";
import { fileStem, scoresCsv, sentencesCsv, textReport } from "@/lib/readability/report";
import { FLAG_LABEL, FLAG_TONE, GAUGE_SEGMENTS, Stat, TONE_TEXT, TonePill } from "./shared";

function download(name: string, body: string, mime: string) {
  // The byte-order mark is what makes Excel read the file as UTF-8.
  const blob = new Blob([`﻿${body}`], { type: `${mime};charset=utf-8;` });
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(href);
}

type Filter = "all" | "long" | "complex" | "passive" | "adverbs";

const FILTER_LABEL: Record<Filter, string> = {
  all: "All flagged",
  long: "Long",
  complex: "Complex words",
  passive: "Passive",
  adverbs: "Adverbs",
};

export function ReadabilityResults({ report }: { report: ReadabilityReport }) {
  const [filter, setFilter] = useState<Filter>("all");
  const [open, setOpen] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);
  const [showFormulas, setShowFormulas] = useState(true);

  const { counts, averages, sentences } = report;

  const buckets = useMemo(() => {
    const long = sentences.filter((s) => s.words >= LONG_SENTENCE);
    const complex = sentences.filter((s) => s.complexWords.length >= 3);
    const passive = sentences.filter((s) => s.passive.length > 0);
    const adverbs = sentences.filter((s) => s.adverbs.length > 0);
    const all = sentences.filter(
      (s) => s.flags.length > 0 || s.adverbs.length > 0,
    );
    return { all, long, complex, passive, adverbs };
  }, [sentences]);

  const rows = buckets[filter];
  const gaugePercent = Math.max(0, Math.min(100, report.flesch));

  async function copyReport() {
    try {
      await navigator.clipboard.writeText(textReport(report));
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="mt-6">
      <section className="rounded-2xl border border-edge bg-panel p-6">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="flex items-baseline gap-4">
            <p className={`font-display text-5xl leading-none ${TONE_TEXT[report.band.tone]}`}>
              {report.fleschDisplay}
            </p>
            <div>
              <p className="text-sm font-medium text-ink">{report.band.label}</p>
              <p className="mt-0.5 font-mono text-[11px] uppercase tracking-widest text-faint">
                Flesch Reading Ease
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={copyReport}
              className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-hi"
            >
              {copied ? <Check size={14} /> : <Clipboard size={14} />}
              {copied ? "Copied" : "Copy report"}
            </button>
            <button
              type="button"
              onClick={() =>
                download(`${fileStem()}.txt`, textReport(report), "text/plain")
              }
              className="inline-flex items-center gap-1.5 rounded-lg border border-edge2 bg-panel px-3 py-2 text-sm text-ink transition-colors hover:bg-panel2"
            >
              <Download size={14} />
              Text
            </button>
            <button
              type="button"
              onClick={() =>
                download(`${fileStem()}-sentences.csv`, sentencesCsv(report), "text/csv")
              }
              className="inline-flex items-center gap-1.5 rounded-lg border border-edge2 bg-panel px-3 py-2 text-sm text-ink transition-colors hover:bg-panel2"
            >
              <FileSpreadsheet size={14} />
              Sentences CSV
            </button>
            <button
              type="button"
              onClick={() =>
                download(`${fileStem()}-scores.csv`, scoresCsv(report), "text/csv")
              }
              className="inline-flex items-center gap-1.5 rounded-lg border border-edge2 bg-panel px-3 py-2 text-sm text-ink transition-colors hover:bg-panel2"
            >
              <FileSpreadsheet size={14} />
              Scores CSV
            </button>
          </div>
        </div>

        <div className="mt-5">
          <div className="relative h-3 w-full overflow-hidden rounded-full">
            <div className="flex h-full w-full">
              {GAUGE_SEGMENTS.map((segment) => (
                <span
                  key={segment.label}
                  title={segment.label}
                  className={segment.className}
                  style={{ width: `${segment.width}%` }}
                />
              ))}
            </div>
          </div>
          <div className="relative h-4">
            <span
              className="absolute top-0 -translate-x-1/2"
              style={{ left: `${gaugePercent}%` }}
              aria-hidden
            >
              <span className="block h-3 w-0.5 bg-ink" />
            </span>
          </div>
          <div className="flex justify-between font-mono text-[10px] text-faint">
            <span>0 hardest</span>
            <span>60 plain English</span>
            <span>100 easiest</span>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat
            label="Grade level"
            value={report.gradeLabel}
            hint={`Flesch-Kincaid ${report.scores[1]?.display}`}
            tone={report.gradeTone}
          />
          <Stat
            label="Five-formula mean"
            value={report.consensusGrade}
            hint="FK, ARI, Fog, SMOG, Coleman-Liau"
          />
          <Stat label="Words" value={counts.words.toLocaleString()} hint={`${counts.sentences} sentences`} />
          <Stat label="Reading time" value={report.readingTime} hint="238 words a minute" />
        </div>

        <p className="mt-4 rounded-xl border border-edge bg-bg p-4 text-xs leading-relaxed text-sub">
          <strong className="font-medium text-ink">Who reads at this level.</strong>{" "}
          {report.gradeAudience} {report.band.audience}
        </p>

        {!report.reliable && (
          <p className="mt-3 rounded-xl border border-warn/25 bg-warn/5 p-4 text-xs leading-relaxed text-sub">
            <strong className="font-medium text-ink">Short sample.</strong> Every
            formula here is a ratio, and ratios over {counts.words} word
            {counts.words === 1 ? "" : "s"} swing hard on a single long sentence.
            Paste at least {RELIABLE_WORD_COUNT} words before you trust the number
            to a decimal place.
          </p>
        )}
      </section>

      {report.recommendations.length > 0 && (
        <section className="mt-6">
          <h3 className="font-mono text-[11px] uppercase tracking-widest text-faint">
            What to change
          </h3>
          <div className="mt-3 flex flex-col gap-2">
            {report.recommendations.map((rec) => (
              <article key={rec.id} className="rounded-xl border border-edge bg-panel p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <TonePill tone={rec.tone}>{rec.tone === "good" ? "Note" : "Fix"}</TonePill>
                  <h4 className="text-sm font-medium text-ink">{rec.title}</h4>
                </div>
                <p className="mt-2 text-sm leading-relaxed text-sub">{rec.body}</p>
                {rec.sentences.length > 0 && (
                  <button
                    type="button"
                    onClick={() => {
                      setFilter(
                        rec.id === "passive"
                          ? "passive"
                          : rec.id === "adverbs"
                            ? "adverbs"
                            : rec.id === "complex"
                              ? "complex"
                              : "long",
                      );
                      setOpen(rec.sentences[0]);
                    }}
                    className="mt-2 text-sm text-accent transition-colors hover:text-accent-hi"
                  >
                    Show the {rec.sentences.length} sentence
                    {rec.sentences.length === 1 ? "" : "s"} this is about
                  </button>
                )}
              </article>
            ))}
          </div>
        </section>
      )}

      <section className="mt-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="font-mono text-[11px] uppercase tracking-widest text-faint">
            Sentences worth a second look
          </h3>
          <div className="inline-flex flex-wrap rounded-lg border border-edge bg-panel p-0.5">
            {(Object.keys(FILTER_LABEL) as Filter[]).map((id) => (
              <button
                key={id}
                type="button"
                onClick={() => setFilter(id)}
                className={`rounded-md px-2.5 py-1.5 text-sm transition-colors ${
                  filter === id ? "bg-panel2 font-medium text-ink" : "text-sub hover:text-ink"
                }`}
              >
                {FILTER_LABEL[id]} ({buckets[id].length})
              </button>
            ))}
          </div>
        </div>

        {rows.length === 0 ? (
          <p className="mt-4 rounded-2xl border border-edge bg-panel p-10 text-center text-sm text-sub">
            Nothing flagged in this category.
          </p>
        ) : (
          <div className="mt-4 flex flex-col gap-2">
            {rows.slice(0, 60).map((sentence) => (
              <SentenceRow
                key={sentence.index}
                sentence={sentence}
                report={report}
                isOpen={open === sentence.index}
                onToggle={() => setOpen(open === sentence.index ? null : sentence.index)}
              />
            ))}
            {rows.length > 60 && (
              <p className="p-3 text-center text-xs text-faint">
                Showing the first 60. The sentences CSV has all {rows.length}.
              </p>
            )}
          </div>
        )}
      </section>

      <section className="mt-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="font-mono text-[11px] uppercase tracking-widest text-faint">
            Every score, and the arithmetic behind it
          </h3>
          <button
            type="button"
            onClick={() => setShowFormulas(!showFormulas)}
            className="inline-flex items-center gap-1.5 text-sm text-accent transition-colors hover:text-accent-hi"
          >
            <Sigma size={14} />
            {showFormulas ? "Hide the working" : "Show the working"}
          </button>
        </div>
        <div className="mt-4 overflow-x-auto rounded-2xl border border-edge bg-panel">
          <table className="w-full min-w-[36rem] text-left text-sm">
            <thead>
              <tr className="border-b border-edge text-xs uppercase tracking-wider text-faint">
                <th className="px-5 py-3 font-medium">Index</th>
                <th className="px-5 py-3 font-medium">Value</th>
                <th className="px-5 py-3 font-medium">Means</th>
              </tr>
            </thead>
            <tbody>
              {report.scores.map((score) => (
                <tr key={score.id} className="border-b border-edge/60 align-top">
                  <td className="px-5 py-3">
                    <span className="text-ink">{score.name}</span>
                    {showFormulas && (
                      <span className="mt-1.5 block font-mono text-[11px] leading-relaxed text-faint">
                        {score.formula}
                        <br />
                        <span className="text-sub">= {score.worked}</span>
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-3 font-mono text-sm text-ink tabular-nums">
                    {score.display}
                    <span className="mt-0.5 block text-[10px] uppercase tracking-widest text-faint">
                      {score.unit === "score" ? "0-100" : "US grade"}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-xs leading-relaxed text-sub">{score.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-8">
        <h3 className="font-mono text-[11px] uppercase tracking-widest text-faint">
          The counts the formulas ran on
        </h3>
        <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          <Stat label="Words" value={counts.words.toLocaleString()} />
          <Stat label="Sentences" value={counts.sentences} />
          <Stat label="Paragraphs" value={counts.paragraphs} />
          <Stat label="Syllables" value={counts.syllables.toLocaleString()} />
          <Stat
            label="Avg sentence"
            value={averages.wordsPerSentence}
            hint="words · aim for 15-20"
            tone={averages.wordsPerSentence > 25 ? "bad" : averages.wordsPerSentence > 20 ? "warn" : "good"}
          />
          <Stat label="Avg word" value={averages.syllablesPerWord} hint="syllables" />
          <Stat
            label="3+ syllable words"
            value={counts.polysyllables}
            hint={`${Math.round((counts.polysyllables / Math.max(1, counts.words)) * 100)}% of words`}
          />
          <Stat label="Complex (Fog rules)" value={counts.complexWords} hint="proper nouns excluded" />
          <Stat
            label="Long sentences"
            value={counts.longSentences}
            hint={`${LONG_SENTENCE}+ words`}
            tone={counts.longSentences > 0 ? "warn" : "good"}
          />
          <Stat
            label="Passive sentences"
            value={counts.passiveSentences}
            hint="pattern match, verify"
            tone={counts.passiveSentences > counts.sentences / 10 ? "warn" : "good"}
          />
          <Stat label="Adverbs" value={counts.adverbs} hint="ending in -ly" />
          <Stat
            label="Characters"
            value={counts.characters.toLocaleString()}
            hint={`${counts.charactersNoSpaces.toLocaleString()} without spaces`}
          />
        </div>
        {report.complexList.length > 0 && (
          <div className="mt-4 rounded-xl border border-edge bg-panel p-4">
            <p className="font-mono text-[10px] uppercase tracking-widest text-faint">
              Longest words, most used first
            </p>
            <p className="mt-2 text-sm leading-relaxed text-sub">
              {report.complexList.slice(0, 24).map((entry, i) => (
                <span key={entry.word}>
                  {i > 0 && <span className="text-faint"> · </span>}
                  <span className="text-ink">{entry.word}</span>
                  <span className="font-mono text-[11px] text-faint">
                    {" "}
                    {entry.syllables}
                    {entry.count > 1 ? `×${entry.count}` : ""}
                  </span>
                </span>
              ))}
            </p>
          </div>
        )}
      </section>
    </div>
  );
}

function SentenceRow({
  sentence,
  report,
  isOpen,
  onToggle,
}: {
  sentence: SentenceInfo;
  report: ReadabilityReport;
  isOpen: boolean;
  onToggle: () => void;
}) {
  const context = report.sentences.filter((s) => s.paragraph === sentence.paragraph);

  return (
    <article className="rounded-xl border border-edge bg-panel">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={isOpen}
        className="flex w-full items-start justify-between gap-4 p-4 text-left"
      >
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-[11px] text-faint">
              Sentence {sentence.index + 1}
            </span>
            {sentence.flags.map((flag) => (
              <TonePill key={flag} tone={FLAG_TONE[flag]}>
                {FLAG_LABEL[flag]}
              </TonePill>
            ))}
            {sentence.adverbs.length > 0 && sentence.flags.length === 0 && (
              <TonePill tone="warn">Adverbs</TonePill>
            )}
          </div>
          <p className="mt-2 text-sm leading-relaxed text-ink">{sentence.text}</p>
          <p className="mt-1.5 font-mono text-[11px] text-faint">
            {sentence.words} words · {sentence.syllables} syllables · grade{" "}
            {sentence.grade.toFixed(1)}
          </p>
        </div>
        <ChevronDown
          size={15}
          className={`mt-1 shrink-0 text-faint transition-transform ${isOpen ? "rotate-180" : ""}`}
        />
      </button>

      {isOpen && (
        <div className="border-t border-edge px-4 py-3">
          <p className="font-mono text-[10px] uppercase tracking-widest text-faint">
            In context — paragraph {sentence.paragraph + 1}
          </p>
          <p className="mt-2 text-sm leading-relaxed text-faint">
            {context.map((s) => (
              <span
                key={s.index}
                className={
                  s.index === sentence.index
                    ? "rounded bg-accent/10 px-0.5 font-medium text-ink"
                    : undefined
                }
              >
                {s.text}{" "}
              </span>
            ))}
          </p>

          <dl className="mt-3 grid gap-2 sm:grid-cols-3">
            {sentence.complexWords.length > 0 && (
              <div>
                <dt className="font-mono text-[10px] uppercase tracking-widest text-faint">
                  Three syllables or more
                </dt>
                <dd className="mt-1 text-sm text-sub">{sentence.complexWords.join(", ")}</dd>
              </div>
            )}
            {sentence.adverbs.length > 0 && (
              <div>
                <dt className="font-mono text-[10px] uppercase tracking-widest text-faint">
                  Adverbs
                </dt>
                <dd className="mt-1 text-sm text-sub">{sentence.adverbs.join(", ")}</dd>
              </div>
            )}
            {sentence.passive.length > 0 && (
              <div>
                <dt className="font-mono text-[10px] uppercase tracking-widest text-faint">
                  Possible passive
                </dt>
                <dd className="mt-1 text-sm text-sub">{sentence.passive.join(" · ")}</dd>
              </div>
            )}
          </dl>
        </div>
      )}
    </article>
  );
}
