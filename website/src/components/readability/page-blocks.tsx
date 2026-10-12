"use client";

import { useMemo, useState } from "react";
import { ArrowDownWideNarrow, ListOrdered } from "lucide-react";
import { analyse, type ReadabilityReport } from "@/lib/readability/analyse";
import type { BlockKind, PageBlock } from "@/lib/page-text/types";
import { TONE_TEXT, TonePill } from "./shared";

/** Under this a passage is a label or a heading, not prose a formula can read. */
const SCOREABLE_WORDS = 12;

const KIND_LABEL: Record<BlockKind, string> = {
  heading: "Heading",
  paragraph: "Paragraph",
  "list-item": "List item",
  quote: "Quote",
  cell: "Table cell",
  caption: "Caption",
};

const PREVIEW_CHARS = 260;

export interface ScoredBlock {
  block: PageBlock;
  report: ReadabilityReport | null;
}

/** Scores every block on its own, so a hard passage cannot hide inside an easy page. */
export function scoreBlocks(blocks: PageBlock[]): ScoredBlock[] {
  return blocks.map((block) => {
    if (block.words < SCOREABLE_WORDS) return { block, report: null };
    const report = analyse(block.text);
    return { block, report: report.empty ? null : report };
  });
}

type Order = "hardest" | "page";

export function PageBlockResults({ scored }: { scored: ScoredBlock[] }) {
  const [order, setOrder] = useState<Order>("hardest");
  const [open, setOpen] = useState<number | null>(null);

  const rows = useMemo(() => {
    if (order === "page") return scored;
    // Unscoreable blocks keep their place at the end: there is nothing to rank
    // them by, and burying them under the hard passages is the point.
    const scoreable = scored.filter((row) => row.report);
    const rest = scored.filter((row) => !row.report);
    return [
      ...[...scoreable].sort((a, b) => a.report!.flesch - b.report!.flesch),
      ...rest,
    ];
  }, [scored, order]);

  const hard = scored.filter((row) => row.report && row.report.gradeTone === "bad").length;
  const scoredCount = scored.filter((row) => row.report).length;

  return (
    <section className="mt-6 rounded-2xl border border-edge bg-panel p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="font-display text-lg text-ink">Passage by passage</h2>
          <p className="mt-1 text-sm leading-relaxed text-sub">
            {scoredCount === 0
              ? "Every block on the page is shorter than a formula can score."
              : `${scoredCount.toLocaleString()} of ${scored.length.toLocaleString()} blocks were long enough to score${
                  hard > 0 ? `, and ${hard.toLocaleString()} read as hard going` : ""
                }. Hardest first, so you know what to rewrite.`}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1 rounded-lg border border-edge2 bg-bg p-1">
          <OrderButton
            active={order === "hardest"}
            onClick={() => setOrder("hardest")}
            icon={<ArrowDownWideNarrow size={13} />}
            label="Hardest first"
          />
          <OrderButton
            active={order === "page"}
            onClick={() => setOrder("page")}
            icon={<ListOrdered size={13} />}
            label="Page order"
          />
        </div>
      </div>

      <ul className="mt-4 space-y-2">
        {rows.map(({ block, report }) => {
          const expanded = open === block.index;
          const long = block.text.length > PREVIEW_CHARS;
          const tone = report?.gradeTone;
          return (
            <li
              key={block.index}
              className={`rounded-xl border bg-bg p-3.5 ${
                tone === "bad"
                  ? "border-bad/30"
                  : tone === "warn"
                    ? "border-warn/25"
                    : "border-edge"
              }`}
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-[10px] uppercase tracking-widest text-faint">
                  {block.index}. {KIND_LABEL[block.kind]}
                </span>
                <code className="rounded border border-edge2 px-1.5 py-0.5 font-mono text-[10px] text-sub">
                  &lt;{block.tag}&gt;
                </code>
                <span className="font-mono text-[10px] tabular-nums text-faint">
                  {block.words.toLocaleString()} words
                </span>
                {report ? (
                  <>
                    <TonePill tone={report.gradeTone}>
                      Grade {report.grade.toFixed(1)}
                    </TonePill>
                    <span className="font-mono text-[11px] tabular-nums text-sub">
                      Flesch{" "}
                      <span className={TONE_TEXT[report.gradeTone]}>
                        {report.fleschDisplay}
                      </span>
                    </span>
                    <span className="font-mono text-[11px] tabular-nums text-faint">
                      {report.averages.wordsPerSentence.toFixed(1)} words/sentence
                    </span>
                  </>
                ) : (
                  <span className="font-mono text-[11px] text-faint">
                    Too short to score
                  </span>
                )}
              </div>

              <p className="mt-2 text-sm leading-relaxed text-ink">
                {expanded || !long ? block.text : `${block.text.slice(0, PREVIEW_CHARS)}…`}
              </p>

              {long && (
                <button
                  type="button"
                  onClick={() => setOpen(expanded ? null : block.index)}
                  className="mt-1.5 text-xs text-accent transition-colors hover:text-accent-hi"
                >
                  {expanded ? "Show less" : "Show the whole passage"}
                </button>
              )}

              {report && report.band && (
                <p className="mt-2 text-xs leading-snug text-faint">
                  {report.band.label} — {report.gradeAudience}
                </p>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function OrderButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs transition-colors ${
        active ? "bg-panel2 text-ink" : "text-sub hover:text-ink"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}
