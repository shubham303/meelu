"use client";

import { useMemo, useState } from "react";
import { AlertTriangle, Download, Search } from "lucide-react";
import { rowsCsv, summaryCsv } from "@/lib/sentiment/csv";
import type { AnalysisResult, Label } from "@/lib/sentiment/types";
import { LABEL_TEXT, LabelPill, ScoreMeter, SplitBar, StatCard } from "./shared";

const PAGE = 50;

function download(name: string, body: string) {
  const blob = new Blob([body], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}

function verdict(net: number): { text: string; tone: string } {
  if (net >= 50) return { text: "Strongly positive", tone: "text-good" };
  if (net >= 20) return { text: "Positive overall", tone: "text-good" };
  if (net > -20) return { text: "Mixed", tone: "text-warn" };
  if (net > -50) return { text: "Negative overall", tone: "text-bad" };
  return { text: "Strongly negative", tone: "text-bad" };
}

export function SentimentResults({
  result,
  fileStem,
}: {
  result: AnalysisResult;
  fileStem: string;
}) {
  const [filter, setFilter] = useState<Label | "all" | "mismatch">("all");
  const [query, setQuery] = useState("");
  const [shown, setShown] = useState(PAGE);

  const { summary } = result;
  const overall = verdict(summary.netSentiment);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return result.rows.filter((row) => {
      if (filter === "mismatch" && !row.mismatch) return false;
      if (filter !== "all" && filter !== "mismatch" && row.scored.label !== filter) return false;
      if (needle && !row.text.toLowerCase().includes(needle)) return false;
      return true;
    });
  }, [result.rows, filter, query]);

  const visible = filtered.slice(0, shown);

  return (
    <div className="mt-8 flex flex-col gap-8">
      <section>
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h2 className="font-display text-xl tracking-tight text-ink">
            {summary.total.toLocaleString()} reviews, {overall.text.toLowerCase()}
          </h2>
          <p className="font-mono text-xs text-faint">
            scored in {result.elapsedMs}ms · column &ldquo;{result.textColumn}&rdquo;
            {result.ratingColumn ? ` · rating from “${result.ratingColumn}”` : ""}
          </p>
        </div>

        <div className="mt-4">
          <SplitBar
            positive={summary.share.positive}
            neutral={summary.share.neutral}
            negative={summary.share.negative}
          />
          <div className="mt-2 flex flex-wrap gap-x-5 gap-y-1 font-mono text-xs text-sub">
            <span className="text-good">
              {summary.share.positive}% positive ({summary.counts.positive.toLocaleString()})
            </span>
            <span>
              {summary.share.neutral}% neutral ({summary.counts.neutral.toLocaleString()})
            </span>
            <span className="text-bad">
              {summary.share.negative}% negative ({summary.counts.negative.toLocaleString()})
            </span>
          </div>
        </div>

        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard
            value={`${summary.netSentiment > 0 ? "+" : ""}${summary.netSentiment}`}
            label="Net sentiment"
            tone={overall.tone}
            hint="Positive share minus negative share"
          />
          <StatCard
            value={summary.avgCompound.toFixed(2)}
            label="Average score"
            hint="-1 to +1 across every review"
          />
          <StatCard
            value={summary.counts.negative.toLocaleString()}
            label="To follow up"
            tone={summary.counts.negative > 0 ? "text-bad" : "text-ink"}
            hint="Negative reviews in this file"
          />
          <StatCard
            value={summary.skipped.toLocaleString()}
            label="Rows skipped"
            hint="Empty cells in the review column"
          />
        </div>

        <div className="mt-4 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => download(`${fileStem}-rows.csv`, rowsCsv(result))}
            className="inline-flex items-center gap-2 rounded-lg border border-edge bg-panel px-3 py-2 text-sm text-ink transition-colors hover:border-edge2"
          >
            <Download size={14} className="text-accent" />
            Every row + label
          </button>
          <button
            type="button"
            onClick={() => download(`${fileStem}-summary.csv`, summaryCsv(result))}
            className="inline-flex items-center gap-2 rounded-lg border border-edge bg-panel px-3 py-2 text-sm text-ink transition-colors hover:border-edge2"
          >
            <Download size={14} className="text-accent" />
            Summary
          </button>
        </div>
      </section>

      {(summary.positiveTerms.length > 0 || summary.negativeTerms.length > 0) && (
        <section>
          <h3 className="font-display text-lg tracking-tight text-ink">What drove the scores</h3>
          <p className="mt-1 text-sm text-sub">
            The words doing the work, by how often they appear. This is the part you
            act on — a label tells you the mood, these tell you the cause.
          </p>
          <div className="mt-4 grid gap-5 sm:grid-cols-2">
            <TermList title="Praised" terms={summary.positiveTerms} tone="good" />
            <TermList title="Complained about" terms={summary.negativeTerms} tone="bad" />
          </div>
        </section>
      )}

      {summary.hasRatings && (
        <section>
          <h3 className="font-display text-lg tracking-tight text-ink">
            Sentiment against the star rating
          </h3>
          <p className="mt-1 text-sm text-sub">
            Where the words and the stars disagree, the words are usually closer to
            the truth.
          </p>
          <div className="mt-4 overflow-x-auto rounded-xl border border-edge bg-panel">
            <table className="w-full min-w-[34rem] text-sm">
              <thead>
                <tr className="border-b border-edge text-left font-mono text-xs text-faint">
                  <th className="px-4 py-2 font-normal">Rating</th>
                  <th className="px-4 py-2 font-normal">Reviews</th>
                  <th className="px-4 py-2 font-normal">Split</th>
                  <th className="px-4 py-2 text-right font-normal">Avg score</th>
                </tr>
              </thead>
              <tbody>
                {summary.ratings.map((bucket) => (
                  <tr key={bucket.rating} className="border-b border-edge/60 last:border-0">
                    <td className="px-4 py-2.5 whitespace-nowrap text-ink">
                      {"★".repeat(bucket.rating)}
                      <span className="text-faint">{"★".repeat(5 - bucket.rating)}</span>
                    </td>
                    <td className="px-4 py-2.5 font-mono text-xs text-sub">
                      {bucket.total.toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5">
                      <SplitBar
                        height="h-2"
                        positive={(bucket.positive / bucket.total) * 100}
                        neutral={(bucket.neutral / bucket.total) * 100}
                        negative={(bucket.negative / bucket.total) * 100}
                      />
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono text-xs text-sub">
                      {bucket.avgCompound.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {summary.mismatches.length > 0 && (
        <section>
          <h3 className="flex items-center gap-2 font-display text-lg tracking-tight text-ink">
            <AlertTriangle size={16} className="text-warn" />
            {summary.mismatches.length} reviews where the stars and the words disagree
          </h3>
          <p className="mt-1 text-sm text-sub">
            A five-star review that reads like a complaint is usually a mis-click, a
            sarcastic customer, or a support case someone closed too early. These are
            the most interesting rows in the file.
          </p>
          <ul className="mt-4 flex flex-col gap-2">
            {summary.mismatches.slice(0, 10).map((row) => (
              <li key={row.line} className="rounded-xl border border-warn/25 bg-warn/5 p-4">
                <div className="flex items-center gap-3 font-mono text-xs text-faint">
                  <span>row {row.line}</span>
                  <span className="text-warn">
                    {row.rating} star, reads {LABEL_TEXT[row.scored.label].toLowerCase()}
                  </span>
                </div>
                <p className="mt-2 text-sm leading-relaxed text-ink/90">
                  {row.text.slice(0, 320)}
                  {row.text.length > 320 ? "…" : ""}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="font-display text-lg tracking-tight text-ink">Every review</h3>
          <div className="flex flex-wrap items-center gap-2">
            <div className="relative">
              <Search
                size={13}
                className="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-faint"
              />
              <input
                value={query}
                onChange={(event) => {
                  setQuery(event.target.value);
                  setShown(PAGE);
                }}
                placeholder="Search reviews"
                className="w-44 rounded-lg border border-edge bg-panel py-1.5 pr-2 pl-7 text-sm text-ink placeholder:text-faint focus:border-accent focus:outline-none"
              />
            </div>
            {(["all", "positive", "neutral", "negative"] as const).map((option) => (
              <FilterButton
                key={option}
                active={filter === option}
                onClick={() => {
                  setFilter(option);
                  setShown(PAGE);
                }}
              >
                {option === "all" ? "All" : LABEL_TEXT[option]}
              </FilterButton>
            ))}
            {summary.mismatches.length > 0 && (
              <FilterButton
                active={filter === "mismatch"}
                onClick={() => {
                  setFilter("mismatch");
                  setShown(PAGE);
                }}
              >
                Mismatched
              </FilterButton>
            )}
          </div>
        </div>

        <p className="mt-2 font-mono text-xs text-faint">
          {filtered.length.toLocaleString()} of {result.rows.length.toLocaleString()} shown
        </p>

        <ul className="mt-3 flex flex-col gap-2">
          {visible.map((row) => (
            <li key={row.line} className="rounded-xl border border-edge bg-panel p-4">
              <div className="flex flex-wrap items-center gap-3">
                <LabelPill label={row.scored.label} />
                <span className="font-mono text-xs text-faint">row {row.line}</span>
                <span className="font-mono text-xs text-sub">
                  {row.scored.compound > 0 ? "+" : ""}
                  {row.scored.compound.toFixed(2)}
                </span>
                {row.rating !== null && (
                  <span className="font-mono text-xs text-faint">{row.rating}★</span>
                )}
              </div>
              <p className="mt-2 text-sm leading-relaxed text-ink/90">
                {row.text.slice(0, 400)}
                {row.text.length > 400 ? "…" : ""}
              </p>
              {row.scored.hits.length > 0 && (
                <p className="mt-2 flex flex-wrap gap-1.5">
                  {row.scored.hits.slice(0, 6).map((hit, index) => (
                    <span
                      key={`${hit.term}-${index}`}
                      className={`rounded border px-1.5 py-0.5 font-mono text-[10px] ${
                        hit.weight > 0
                          ? "border-good/25 bg-good/5 text-good"
                          : "border-bad/25 bg-bad/5 text-bad"
                      }`}
                    >
                      {hit.term} {hit.weight > 0 ? "+" : ""}
                      {hit.weight.toFixed(1)}
                    </span>
                  ))}
                </p>
              )}
            </li>
          ))}
        </ul>

        {shown < filtered.length && (
          <button
            type="button"
            onClick={() => setShown((current) => current + PAGE * 4)}
            className="mt-4 w-full rounded-lg border border-edge bg-panel py-2.5 text-sm text-sub transition-colors hover:border-edge2 hover:text-ink"
          >
            Show more ({(filtered.length - shown).toLocaleString()} left)
          </button>
        )}
      </section>
    </div>
  );
}

function FilterButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-lg border px-2.5 py-1.5 text-xs transition-colors ${
        active
          ? "border-accent/30 bg-accent/10 text-accent"
          : "border-edge bg-panel text-sub hover:border-edge2 hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}

function TermList({
  title,
  terms,
  tone,
}: {
  title: string;
  terms: { term: string; count: number }[];
  tone: "good" | "bad";
}) {
  if (terms.length === 0) return null;
  const max = terms[0]?.count ?? 1;

  return (
    <div className="rounded-xl border border-edge bg-panel p-4">
      <h4 className={`text-sm font-medium ${tone === "good" ? "text-good" : "text-bad"}`}>
        {title}
      </h4>
      <ul className="mt-3 flex flex-col gap-1.5">
        {terms.slice(0, 10).map((term) => (
          <li key={term.term} className="flex items-center gap-2">
            <span className="w-32 shrink-0 truncate text-sm text-ink/90">{term.term}</span>
            <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-panel2">
              <span
                className={`block h-full ${tone === "good" ? "bg-good" : "bg-bad"}`}
                style={{ width: `${(term.count / max) * 100}%` }}
              />
            </span>
            <span className="w-10 shrink-0 text-right font-mono text-xs text-faint">
              {term.count}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** The single-review panel, for people who want to try it without a file. */
export function SingleResult({
  compound,
  label,
  hits,
}: {
  compound: number;
  label: Label;
  hits: { term: string; weight: number }[];
}) {
  return (
    <div className="mt-4 rounded-xl border border-edge bg-panel p-5">
      <div className="flex flex-wrap items-center gap-3">
        <LabelPill label={label} />
        <span className="font-mono text-sm text-sub">
          {compound > 0 ? "+" : ""}
          {compound.toFixed(3)}
        </span>
      </div>
      <div className="mt-4">
        <ScoreMeter compound={compound} />
      </div>
      {hits.length > 0 ? (
        <p className="mt-4 flex flex-wrap gap-1.5">
          {hits.slice(0, 12).map((hit, index) => (
            <span
              key={`${hit.term}-${index}`}
              className={`rounded border px-1.5 py-0.5 font-mono text-[11px] ${
                hit.weight > 0
                  ? "border-good/25 bg-good/5 text-good"
                  : "border-bad/25 bg-bad/5 text-bad"
              }`}
            >
              {hit.term} {hit.weight > 0 ? "+" : ""}
              {hit.weight.toFixed(1)}
            </span>
          ))}
        </p>
      ) : (
        <p className="mt-4 text-sm text-sub">
          No sentiment-bearing words found. Statements of fact score neutral, which
          is the correct answer rather than a failure.
        </p>
      )}
    </div>
  );
}
