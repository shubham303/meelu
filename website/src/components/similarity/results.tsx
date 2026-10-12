"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import { ArrowLeftRight, Download, ExternalLink, Quote, ScanText } from "lucide-react";
import { fileStem, matchesCsv } from "@/lib/similarity/csv";
import type { MatchKind, SideReport, SimilarityResult } from "@/lib/similarity/types";
import {
  BAND_LABEL,
  BAND_RING,
  BAND_TEXT,
  KIND_MARK,
  KindPill,
  download,
} from "./shared";

export type Sources = Partial<
  Record<"a" | "b", { url: string; finalUrl: string; title: string | null }>
>;

type Mark = { kind: MatchKind; score: number; partner: number };
type Tab = "matches" | "passages" | "uniqueA" | "uniqueB";

export function SimilarityResults({
  result,
  sources,
  onReset,
}: {
  result: SimilarityResult;
  sources: Sources;
  onReset: () => void;
}) {
  const [tab, setTab] = useState<Tab>("matches");
  const [focus, setFocus] = useState<{ a: number; b: number } | null>(null);
  const [sync, setSync] = useState(true);

  const nodes = useRef(new Map<string, HTMLElement>());
  const paneA = useRef<HTMLDivElement>(null);
  const paneB = useRef<HTMLDivElement>(null);
  const echo = useRef(0);

  const register = useCallback((key: string, el: HTMLElement | null) => {
    if (el) nodes.current.set(key, el);
    else nodes.current.delete(key);
  }, []);

  const marksA = useMemo(() => buildMarks(result, "a"), [result]);
  const marksB = useMemo(() => buildMarks(result, "b"), [result]);

  const reveal = useCallback((a: number, b: number) => {
    setFocus({ a, b });
    scrollToKey(paneA.current, nodes.current.get(`a:${a}`));
    scrollToKey(paneB.current, nodes.current.get(`b:${b}`));
  }, []);

  const onScroll = useCallback(
    (from: "a" | "b") => {
      if (!sync) return;
      const now = Date.now();
      if (now - echo.current < 120) return;
      const source = from === "a" ? paneA.current : paneB.current;
      const target = from === "a" ? paneB.current : paneA.current;
      if (!source || !target) return;
      const room = source.scrollHeight - source.clientHeight;
      if (room <= 0) return;
      echo.current = now;
      target.scrollTop = (source.scrollTop / room) * (target.scrollHeight - target.clientHeight);
    },
    [sync],
  );

  const sentencesA = useMemo(() => byIndex(result.a), [result]);
  const sentencesB = useMemo(() => byIndex(result.b), [result]);

  return (
    <div className="mt-8">
      <section className={`rounded-2xl border p-6 ${BAND_RING[result.band]}`}>
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="flex items-center gap-5">
            <div className="text-center">
              <p className={`font-display text-5xl leading-none ${BAND_TEXT[result.band]}`}>
                {result.overall}%
              </p>
              <p className="mt-1 font-mono text-[10px] uppercase tracking-widest text-faint">
                Similar
              </p>
            </div>
            <div>
              <p className={`text-base font-medium ${BAND_TEXT[result.band]}`}>
                {result.verdict}
              </p>
              <p className="mt-1 font-mono text-[11px] uppercase tracking-widest text-faint">
                {BAND_LABEL[result.band]}
              </p>
              <p className="mt-2 max-w-xl text-sm leading-relaxed text-sub">{result.advice}</p>
            </div>
          </div>
          <div className="flex flex-col items-start gap-2">
            <button
              type="button"
              onClick={() => download(`${fileStem(result)}.csv`, matchesCsv(result))}
              disabled={result.matches.length === 0}
              className="inline-flex h-9 items-center gap-2 rounded-lg border border-edge2 bg-panel px-3 text-sm text-ink transition-colors hover:border-accent hover:text-accent disabled:opacity-50"
            >
              <Download size={14} />
              Matched pairs CSV
            </button>
            <button
              type="button"
              onClick={onReset}
              className="text-sm text-accent transition-colors hover:text-accent-hi"
            >
              Compare something else
            </button>
          </div>
        </div>

        <p className="mt-5 text-xs text-faint">
          {result.a.words.toLocaleString()} words against {result.b.words.toLocaleString()}{" "}
          words · {result.a.sentenceCount + result.b.sentenceCount} sentences · compared in{" "}
          {result.durationMs} ms in your browser
          {(result.a.truncated || result.b.truncated) && " · one side was cut at 25,000 characters"}
        </p>
      </section>

      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <Containment side={result.a} other={result.b} source={sources.a} />
        <Containment side={result.b} other={result.a} source={sources.b} />
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-4">
        {[
          { label: "Word-for-word sentences", value: result.exactSentences },
          { label: "Near-exact sentences", value: result.nearSentences },
          { label: "Matched pairs", value: result.matches.length },
          {
            label: "Longest shared run",
            value: result.longestPassageWords > 0 ? `${result.longestPassageWords} words` : "None",
          },
        ].map((tile) => (
          <div key={tile.label} className="rounded-xl border border-edge bg-panel p-4">
            <p className="font-display text-2xl leading-none text-ink tabular-nums">{tile.value}</p>
            <p className="mt-1.5 text-xs text-sub">{tile.label}</p>
          </div>
        ))}
      </div>

      <section className="mt-6 rounded-2xl border border-edge bg-panel p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h3 className="flex items-center gap-2 text-sm font-medium text-ink">
            <ScanText size={15} className="text-accent" />
            Side by side
          </h3>
          <label className="flex items-center gap-2 text-xs text-sub">
            <input
              type="checkbox"
              checked={sync}
              onChange={(e) => setSync(e.target.checked)}
              className="size-3.5 accent-[var(--color-accent)]"
            />
            Scroll both together
          </label>
        </div>
        <p className="mt-2 text-xs text-faint">
          Shaded text has a match on the other side. Click any shaded sentence and both panes
          jump to it. Red is word-for-word, amber is near-exact, blue is close but reworded.
        </p>
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <Pane
            side="a"
            report={result.a}
            marks={marksA}
            focus={focus?.a ?? null}
            paneRef={paneA}
            register={register}
            onPick={(index, partner) => reveal(index, partner)}
            onScroll={() => onScroll("a")}
            source={sources.a}
          />
          <Pane
            side="b"
            report={result.b}
            marks={marksB}
            focus={focus?.b ?? null}
            paneRef={paneB}
            register={register}
            onPick={(index, partner) => reveal(partner, index)}
            onScroll={() => onScroll("b")}
            source={sources.b}
          />
        </div>
      </section>

      <section className="mt-6 rounded-2xl border border-edge bg-panel">
        <div className="flex flex-wrap gap-1 border-b border-edge p-2">
          {(
            [
              ["matches", `Matched sentences (${result.matches.length})`],
              ["passages", `Longest shared passages (${result.passages.length})`],
              ["uniqueA", `Only in A (${result.a.unique.length})`],
              ["uniqueB", `Only in B (${result.b.unique.length})`],
            ] as Array<[Tab, string]>
          ).map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() => setTab(key)}
              className={`rounded-lg px-3 py-1.5 text-sm transition-colors ${
                tab === key ? "bg-panel2 font-medium text-ink" : "text-sub hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="p-5">
          {tab === "matches" && (
            <MatchList result={result} a={sentencesA} b={sentencesB} onPick={reveal} />
          )}
          {tab === "passages" && <PassageList result={result} onPick={reveal} />}
          {tab === "uniqueA" && (
            <UniqueList
              label="A"
              indexes={result.a.unique}
              lookup={sentencesA}
              empty="Every judged sentence in A has a match in B."
            />
          )}
          {tab === "uniqueB" && (
            <UniqueList
              label="B"
              indexes={result.b.unique}
              lookup={sentencesB}
              empty="Every judged sentence in B has a match in A."
            />
          )}
        </div>
      </section>
    </div>
  );
}

function buildMarks(result: SimilarityResult, side: "a" | "b"): Map<number, Mark> {
  const marks = new Map<number, Mark>();
  const add = (index: number, partner: number, kind: MatchKind, score: number) => {
    const held = marks.get(index);
    if (!held || score > held.score) marks.set(index, { kind, score, partner });
  };
  for (const match of [...result.matches, ...result.reverse]) {
    if (side === "a") add(match.a, match.b, match.kind, match.score);
    else add(match.b, match.a, match.kind, match.score);
  }
  return marks;
}

function byIndex(report: SideReport) {
  return new Map(report.sentences.map((s) => [s.index, s]));
}

function scrollToKey(container: HTMLDivElement | null, el: HTMLElement | undefined) {
  if (!container || !el) return;
  const top = el.offsetTop - container.clientHeight / 2 + el.offsetHeight / 2;
  container.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
}

function Containment({
  side,
  other,
  source,
}: {
  side: SideReport;
  other: SideReport;
  source?: { url: string; finalUrl: string; title: string | null };
}) {
  return (
    <div className="rounded-2xl border border-edge bg-panel p-5">
      <p className="font-display text-3xl leading-none text-ink tabular-nums">
        {side.containment}%
      </p>
      <p className="mt-2 text-sm leading-relaxed text-ink">
        of document {side.label} appears in document {other.label}.
      </p>
      <p className="mt-2 text-sm leading-relaxed text-sub">
        {side.verbatim}% of {side.label}&rsquo;s five-word windows turn up in {other.label}{" "}
        word for word, and {side.coverage}% of its words sit in a sentence with a match. The
        figure above is the higher of the two.
      </p>
      {source && (
        <p className="mt-3 truncate font-mono text-[11px] text-faint">
          <a
            href={source.finalUrl}
            target="_blank"
            rel="noopener noreferrer nofollow"
            className="inline-flex max-w-full items-center gap-1 hover:text-accent"
          >
            <ExternalLink size={11} className="shrink-0" />
            <span className="truncate">{source.finalUrl.replace(/^https?:\/\//, "")}</span>
          </a>
        </p>
      )}
    </div>
  );
}

function Pane({
  side,
  report,
  marks,
  focus,
  paneRef,
  register,
  onPick,
  onScroll,
  source,
}: {
  side: "a" | "b";
  report: SideReport;
  marks: Map<number, Mark>;
  focus: number | null;
  paneRef: React.RefObject<HTMLDivElement | null>;
  register: (key: string, el: HTMLElement | null) => void;
  onPick: (index: number, partner: number) => void;
  onScroll: () => void;
  source?: { url: string; finalUrl: string; title: string | null };
}) {
  const pieces: React.ReactNode[] = [];
  let cursor = 0;
  for (const sentence of report.sentences) {
    if (sentence.start > cursor) {
      pieces.push(
        <span key={`gap-${sentence.index}`}>{report.text.slice(cursor, sentence.start)}</span>,
      );
    }
    const mark = marks.get(sentence.index);
    if (mark) {
      pieces.push(
        <button
          key={`s-${sentence.index}`}
          type="button"
          ref={(el) => register(`${side}:${sentence.index}`, el)}
          onClick={() => onPick(sentence.index, mark.partner)}
          title={`${mark.score}% match`}
          className={`inline cursor-pointer rounded-sm px-0.5 text-left underline decoration-dotted underline-offset-2 transition-colors ${
            KIND_MARK[mark.kind]
          } ${focus === sentence.index ? "ring-2 ring-accent/60" : ""}`}
        >
          {sentence.text}
        </button>,
      );
    } else {
      pieces.push(
        <span key={`s-${sentence.index}`} ref={(el) => register(`${side}:${sentence.index}`, el)}>
          {sentence.text}
        </span>,
      );
    }
    cursor = sentence.end;
  }
  if (cursor < report.text.length) {
    pieces.push(<span key="tail">{report.text.slice(cursor)}</span>);
  }

  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
          Document {report.label}
        </p>
        <p className="truncate text-xs text-faint">
          {source?.title ?? `${report.words.toLocaleString()} words`}
        </p>
      </div>
      <div
        ref={paneRef}
        onScroll={onScroll}
        className="relative mt-2 h-80 overflow-y-auto rounded-xl border border-edge2 bg-bg p-4 text-sm leading-relaxed whitespace-pre-wrap text-ink"
      >
        {pieces}
      </div>
    </div>
  );
}

function MatchList({
  result,
  a,
  b,
  onPick,
}: {
  result: SimilarityResult;
  a: Map<number, SideReport["sentences"][number]>;
  b: Map<number, SideReport["sentences"][number]>;
  onPick: (a: number, b: number) => void;
}) {
  if (result.matches.length === 0) {
    return (
      <p className="text-sm leading-relaxed text-sub">
        No sentence in A is close enough to a sentence in B to count as a match. Anything the
        two texts share is shorter than a sentence or too reworded for a lexical comparison to
        call it.
      </p>
    );
  }
  return (
    <ul className="flex flex-col gap-3">
      {result.matches.map((match) => (
        <li
          key={`${match.a}-${match.b}`}
          className="rounded-xl border border-edge bg-bg p-4"
        >
          <div className="flex flex-wrap items-center gap-3">
            <KindPill kind={match.kind} score={match.score} />
            <span className="font-mono text-[11px] text-faint">
              cosine {match.cosine}% · shared words {match.overlap}%
            </span>
            <button
              type="button"
              onClick={() => onPick(match.a, match.b)}
              className="ml-auto inline-flex items-center gap-1.5 text-xs text-accent transition-colors hover:text-accent-hi"
            >
              <ArrowLeftRight size={12} />
              Show both
            </button>
          </div>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <p className="text-sm leading-relaxed text-ink">
              <span className="font-mono text-[10px] uppercase tracking-widest text-faint">
                A ·{" "}
              </span>
              {a.get(match.a)?.text}
            </p>
            <p className="text-sm leading-relaxed text-ink">
              <span className="font-mono text-[10px] uppercase tracking-widest text-faint">
                B ·{" "}
              </span>
              {b.get(match.b)?.text}
            </p>
          </div>
        </li>
      ))}
    </ul>
  );
}

function PassageList({
  result,
  onPick,
}: {
  result: SimilarityResult;
  onPick: (a: number, b: number) => void;
}) {
  if (result.passages.length === 0) {
    return (
      <p className="text-sm leading-relaxed text-sub">
        The two texts share no run of eight or more identical words in a row. Whatever overlap
        the score reports is reworded rather than copied.
      </p>
    );
  }
  return (
    <ul className="flex flex-col gap-3">
      {result.passages.map((passage) => (
        <li key={`${passage.aStart}-${passage.bStart}`} className="rounded-xl border border-edge bg-bg p-4">
          <div className="flex flex-wrap items-center gap-3">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-bad/25 bg-bad/10 px-2 py-0.5 font-mono text-[11px] font-medium text-bad">
              <Quote size={11} />
              {passage.words} words identical
            </span>
            <button
              type="button"
              onClick={() => onPick(passage.aSentence, passage.bSentence)}
              className="ml-auto inline-flex items-center gap-1.5 text-xs text-accent transition-colors hover:text-accent-hi"
            >
              <ArrowLeftRight size={12} />
              Show both
            </button>
          </div>
          <p className="mt-3 text-sm leading-relaxed text-ink">
            &ldquo;{passage.text.length > 700 ? `${passage.text.slice(0, 700)}…` : passage.text}
            &rdquo;
          </p>
        </li>
      ))}
    </ul>
  );
}

function UniqueList({
  label,
  indexes,
  lookup,
  empty,
}: {
  label: string;
  indexes: number[];
  lookup: Map<number, SideReport["sentences"][number]>;
  empty: string;
}) {
  if (indexes.length === 0) {
    return <p className="text-sm leading-relaxed text-sub">{empty}</p>;
  }
  return (
    <div>
      <p className="text-sm leading-relaxed text-sub">
        Sentences in document {label} with nothing close to them on the other side. This is the
        part that is genuinely yours — or, if you were expecting a full copy, the part that got
        changed.
      </p>
      <ul className="mt-4 flex flex-col gap-2">
        {indexes.map((index) => (
          <li
            key={index}
            className="rounded-xl border border-edge bg-bg p-3 text-sm leading-relaxed text-ink"
          >
            {lookup.get(index)?.text}
          </li>
        ))}
      </ul>
    </div>
  );
}
