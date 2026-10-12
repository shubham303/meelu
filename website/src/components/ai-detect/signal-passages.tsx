"use client";

import { useMemo, useState } from "react";
import { Highlighter, List } from "lucide-react";
import type { Signal, SignalSpan } from "@/lib/ai-detect/types";

/**
 * The surface signals, with the passages that made each one count.
 *
 * A count on its own ("twenty sentences start with 'the'") is not something a writer can
 * act on or argue with. The sentence is both. Two views of the same attribution: a list
 * per signal, and the whole text with one signal's passages marked in place.
 *
 * The framing matters as much as the mechanism. A highlight here means "this is what was
 * counted", never "this sentence was written by a machine" — no surface count can support
 * that claim about a single sentence, and none of these feed the score at all.
 */

/** Spans shown before the card collapses the rest behind a button. */
const PREVIEW_SPANS = 3;

type View = "list" | "text";

export function SurfaceSignals({ signals, text }: { signals: Signal[]; text: string }) {
  const [view, setView] = useState<View>("list");
  const withSpans = signals.filter((signal) => signal.spans.length > 0);
  const [active, setActive] = useState<string>(withSpans[0]?.id ?? "");

  if (signals.length === 0) return null;

  const activeSignal =
    withSpans.find((signal) => signal.id === active) ?? withSpans[0] ?? null;

  return (
    <section className="mt-6 rounded-2xl border border-edge bg-panel p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h2 className="text-base font-medium text-ink">Surface signals</h2>
        {withSpans.length > 0 && (
          <div className="flex shrink-0 items-center gap-1 rounded-lg border border-edge2 bg-bg p-1">
            <ViewButton
              active={view === "list"}
              onClick={() => setView("list")}
              icon={<List size={13} />}
              label="Per signal"
            />
            <ViewButton
              active={view === "text"}
              onClick={() => setView("text")}
              icon={<Highlighter size={13} />}
              label="In the text"
            />
          </div>
        )}
      </div>

      <p className="mt-1.5 text-sm leading-relaxed text-sub">
        Plain counts you can verify against the text yourself, with the passages that made
        each one count.{" "}
        <strong className="font-medium text-ink">None of these feed the score</strong> —
        they are here so a percentage is not the only thing you leave with. Every one of
        them also describes plenty of human writing.
      </p>
      <p className="mt-2 text-xs leading-relaxed text-faint">
        A highlighted sentence is a sentence that was counted, and nothing more than that.
        It is not the classifier&rsquo;s opinion of that sentence, and no surface count can
        tell you who wrote one sentence. Read them to see what the tool reacted to, then
        make your own call.
      </p>

      {view === "list" || !activeSignal ? (
        <div className="mt-5 space-y-4">
          {signals.map((signal) => (
            <SignalCard key={signal.id} signal={signal} />
          ))}
        </div>
      ) : (
        <div className="mt-5">
          <div className="flex flex-wrap gap-1.5">
            {withSpans.map((signal) => (
              <button
                key={signal.id}
                type="button"
                onClick={() => setActive(signal.id)}
                aria-pressed={signal.id === activeSignal.id}
                className={`rounded-lg border px-2.5 py-1.5 text-xs transition-colors ${
                  signal.id === activeSignal.id
                    ? "border-accent/40 bg-accent/10 text-ink"
                    : "border-edge2 text-sub hover:text-ink"
                }`}
              >
                {signal.label}
                <span className="ml-1.5 font-mono text-[10px] tabular-nums text-faint">
                  {signal.totalSpans}
                </span>
              </button>
            ))}
          </div>

          <p className="mt-3 text-xs leading-relaxed text-sub">{activeSignal.trigger}</p>

          <div className="mt-3 max-h-[28rem] select-text overflow-y-auto rounded-xl border border-edge bg-bg p-4 text-sm leading-relaxed whitespace-pre-wrap text-ink/90">
            <HighlightedText text={text} spans={activeSignal.spans} signal={activeSignal} />
          </div>

          {activeSignal.totalSpans > activeSignal.spans.length && (
            <p className="mt-2 text-xs text-faint">
              {activeSignal.totalSpans.toLocaleString()} passages counted in total; the
              first {activeSignal.spans.length} are marked.
            </p>
          )}
        </div>
      )}
    </section>
  );
}

function SignalCard({ signal }: { signal: Signal }) {
  const [expanded, setExpanded] = useState(false);
  const shown = expanded ? signal.spans : signal.spans.slice(0, PREVIEW_SPANS);
  const hidden = signal.spans.length - shown.length;

  return (
    <div className="rounded-xl border border-edge bg-bg p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <p className="text-sm font-medium text-ink">{signal.label}</p>
        <span
          className={`font-mono text-[11px] ${
            signal.leaning === "ai" ? "text-warn" : "text-faint"
          }`}
        >
          {signal.value}
        </span>
      </div>
      <p className="mt-1.5 text-xs leading-relaxed text-sub">{signal.note}</p>
      <p className="mt-1.5 text-xs leading-relaxed text-faint">{signal.trigger}</p>

      {shown.length > 0 && (
        <ol className="mt-3 space-y-2">
          {shown.map((span) => (
            <li
              key={`${span.index}-${span.start}`}
              className={`rounded-lg border-l-2 bg-panel px-3 py-2 ${
                signal.leaning === "ai" ? "border-warn/50" : "border-good/50"
              }`}
            >
              <p className="flex flex-wrap items-baseline gap-x-2 font-mono text-[10px] uppercase tracking-widest text-faint">
                <span>Sentence {span.index}</span>
                <span className="normal-case tracking-normal text-sub">{span.detail}</span>
              </p>
              <p className="mt-1 select-text text-sm leading-relaxed text-ink/90">
                {span.text}
              </p>
            </li>
          ))}
        </ol>
      )}

      {hidden > 0 && (
        <button
          type="button"
          onClick={() => setExpanded(true)}
          className="mt-2 text-xs text-accent transition-colors hover:text-accent-hi"
        >
          Show {hidden} more passage{hidden === 1 ? "" : "s"}
        </button>
      )}
      {expanded && signal.spans.length > PREVIEW_SPANS && (
        <button
          type="button"
          onClick={() => setExpanded(false)}
          className="mt-2 text-xs text-accent transition-colors hover:text-accent-hi"
        >
          Show fewer
        </button>
      )}
      {signal.totalSpans > signal.spans.length && (
        <p className="mt-2 text-xs text-faint">
          {signal.totalSpans.toLocaleString()} passages counted in total; the first{" "}
          {signal.spans.length} are shown.
        </p>
      )}
    </div>
  );
}

/** Renders the whole text with one signal's spans marked, offsets straight from the analysis. */
function HighlightedText({
  text,
  spans,
  signal,
}: {
  text: string;
  spans: SignalSpan[];
  signal: Signal;
}) {
  const parts = useMemo(() => {
    const ordered = [...spans].sort((a, b) => a.start - b.start);
    const out: Array<{ key: string; text: string; span: SignalSpan | null }> = [];
    let cursor = 0;
    for (const span of ordered) {
      if (span.start < cursor) continue;
      if (span.start > cursor) {
        out.push({ key: `plain-${cursor}`, text: text.slice(cursor, span.start), span: null });
      }
      out.push({ key: `mark-${span.start}`, text: text.slice(span.start, span.end), span });
      cursor = span.end;
    }
    if (cursor < text.length) {
      out.push({ key: `plain-${cursor}`, text: text.slice(cursor), span: null });
    }
    return out;
  }, [text, spans]);

  const marked =
    signal.leaning === "ai"
      ? "bg-warn/20 text-ink"
      : "bg-good/15 text-ink";

  return (
    <>
      {parts.map((part) =>
        part.span ? (
          <mark
            key={part.key}
            title={`Sentence ${part.span.index} — counted: ${part.span.detail}`}
            className={`rounded px-0.5 ${marked}`}
          >
            {part.text}
          </mark>
        ) : (
          <span key={part.key}>{part.text}</span>
        ),
      )}
    </>
  );
}

function ViewButton({
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
