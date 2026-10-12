"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronRight,
  ClipboardType,
  Cpu,
  ExternalLink,
  Link2,
  Loader2,
  Lock,
  RotateCcw,
  TriangleAlert,
} from "lucide-react";
import { chunkText, countWords, normalise } from "@/lib/ai-detect/chunk";
import { limitWords } from "@/lib/limits";
import {
  DOWNLOAD_MB,
  MAX_WORDS,
  MIN_WORDS_TO_JUDGE,
  MIN_WORDS_TO_RUN,
} from "@/lib/ai-detect/constants";
import {
  CONFIDENCE_LABEL,
  VERDICT_BLURB,
  VERDICT_LABEL,
  analyse,
  toneFor,
} from "@/lib/ai-detect/score";
import type { Analysis, LoadProgress, ScoredChunk } from "@/lib/ai-detect/types";
import { detect } from "@/lib/similarity/input";
import { createEngine, type Engine } from "./engine";
import { SurfaceSignals } from "./signal-passages";

type Mode = "paste" | "url";

type Failure = { error: string; hint?: string; code: string };

/** Where the scored text came from, when it was not typed into the box. */
type Source = {
  finalUrl: string;
  title: string | null;
  words: number;
  blocks: number;
  truncated: boolean;
};

type Phase =
  | { kind: "idle" }
  | { kind: "fetching" }
  | { kind: "loading"; progress: LoadProgress }
  | { kind: "scoring"; total: number }
  | { kind: "done"; analysis: Analysis }
  | { kind: "failed"; message: string }
  | { kind: "fetch-failed"; failure: Failure };

const mb = (bytes: number) => (bytes / 1_048_576).toFixed(0);

export function AiContentDetector() {
  const [mode, setMode] = useState<Mode>("paste");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  /** Set when the visitor pasted something URL-shaped but meant it as text. */
  const [forceText, setForceText] = useState(false);
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const [source, setSource] = useState<Source | null>(null);
  const [modelReady, setModelReady] = useState(false);
  const engine = useRef<Engine | null>(null);

  useEffect(() => {
    return () => {
      engine.current?.dispose();
      engine.current = null;
    };
  }, []);

  const words = useMemo(() => countWords(text), [text]);

  // A pasted address is almost never something you want scored as prose: it would be
  // one "sentence" of four words, and the classifier needs two hundred. detect() is
  // deliberately strict, so an article that merely mentions example.com stays text.
  const detected = useMemo(() => detect(text), [text]);
  const pastedUrl =
    mode === "paste" && !forceText && detected.kind === "url" ? detected.url : null;

  const busy =
    phase.kind === "loading" || phase.kind === "scoring" || phase.kind === "fetching";

  const scoreText = useCallback(
    async (raw: string) => {
      const normalised = limitWords(normalise(raw), MAX_WORDS).text;
      const chunks = chunkText(normalised);
      if (chunks.length === 0) {
        setPhase({
          kind: "failed",
          message: "There was no readable text to score.",
        });
        return;
      }

      if (!engine.current) engine.current = createEngine();
      const active = engine.current;

      try {
        if (!modelReady) {
          setPhase({
            kind: "loading",
            progress: {
              percent: 0,
              loadedBytes: 0,
              totalBytes: 0,
              message: "Starting the detector",
            },
          });
          await active.load((progress) => setPhase({ kind: "loading", progress }));
          setModelReady(true);
        }

        setPhase({ kind: "scoring", total: chunks.length });
        const scores = await active.classify(chunks.map((chunk) => chunk.text));
        const scored: ScoredChunk[] = chunks.map((chunk, i) => ({
          ...chunk,
          ai: scores[i] ?? 0,
        }));
        setPhase({ kind: "done", analysis: analyse(scored, normalised) });
      } catch (error: unknown) {
        setModelReady(false);
        setPhase({
          kind: "failed",
          message:
            error instanceof Error
              ? error.message
              : "The detector could not finish. Try again.",
        });
      }
    },
    [modelReady],
  );

  /**
   * The only part of this tool that touches a server. It fetches the page and strips it
   * to readable text; the classifier still runs in this tab, on the text that comes back.
   */
  const fetchAndScore = useCallback(
    async (target: string) => {
      setSource(null);
      setPhase({ kind: "fetching" });

      let response: Response;
      try {
        response = await fetch("/api/tools/ai-detect", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: target }),
        });
      } catch {
        setPhase({
          kind: "fetch-failed",
          failure: {
            error: "Could not reach the page fetcher.",
            hint: "Paste the text instead — that path never touches our server.",
            code: "unreachable",
          },
        });
        return;
      }

      const payload = (await response.json().catch(() => null)) as {
        page?: Source & { text: string };
        error?: string;
        hint?: string;
        code?: string;
      } | null;

      if (!response.ok || !payload?.page) {
        setPhase({
          kind: "fetch-failed",
          failure: {
            error: payload?.error ?? "The page could not be read.",
            hint: payload?.hint,
            code: payload?.code ?? "unreachable",
          },
        });
        return;
      }

      const page = payload.page;
      if (countWords(page.text) < MIN_WORDS_TO_RUN) {
        setPhase({
          kind: "fetch-failed",
          failure: {
            error: "That page has too little text to check.",
            hint: `A detector of this kind needs ${MIN_WORDS_TO_JUDGE}+ words to say anything useful, and at least ${MIN_WORDS_TO_RUN} to run at all.`,
            code: "empty",
          },
        });
        return;
      }

      setSource({
        finalUrl: page.finalUrl,
        title: page.title,
        words: page.words,
        blocks: page.blocks,
        truncated: page.truncated,
      });
      await scoreText(page.text);
    },
    [scoreText],
  );

  const run = useCallback(() => {
    if (busy) return;
    if (mode === "url") {
      if (url.trim().length > 0) void fetchAndScore(url.trim());
      return;
    }
    if (pastedUrl) {
      void fetchAndScore(pastedUrl);
      return;
    }
    setSource(null);
    void scoreText(text);
  }, [busy, mode, url, pastedUrl, text, fetchAndScore, scoreText]);

  const tooShort = !pastedUrl && words < MIN_WORDS_TO_RUN;
  const disabled =
    busy ||
    (mode === "url" ? url.trim().length === 0 : pastedUrl ? false : tooShort);

  const reset = () => {
    setText("");
    setUrl("");
    setForceText(false);
    setSource(null);
    setPhase({ kind: "idle" });
  };

  const clearResult = () => {
    if (phase.kind === "done" || phase.kind === "failed" || phase.kind === "fetch-failed") {
      setPhase({ kind: "idle" });
      setSource(null);
    }
  };

  return (
    <div>
      <div className="mb-3 inline-flex items-center gap-1 rounded-lg border border-edge2 bg-panel p-1">
        <ModeButton
          active={mode === "paste"}
          onClick={() => {
            setMode("paste");
            clearResult();
          }}
          icon={<ClipboardType size={13} />}
          label="Paste text"
        />
        <ModeButton
          active={mode === "url"}
          onClick={() => {
            setMode("url");
            clearResult();
          }}
          icon={<Link2 size={13} />}
          label="Web page URL"
        />
      </div>

      <div className="rounded-2xl border border-edge bg-panel p-5 sm:p-6">
        {mode === "paste" ? (
          <>
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <label
                htmlFor="ai-detect-text"
                className="font-mono text-[11px] uppercase tracking-widest text-faint"
              >
                Paste the text to check
              </label>
              {pastedUrl ? (
                <span className="inline-flex items-center gap-1 font-mono text-[11px] text-accent">
                  <Link2 size={11} />
                  URL — we will fetch it
                </span>
              ) : (
                <p
                  className={`font-mono text-[11px] tabular-nums ${
                    countWords(text) >= MAX_WORDS ? "text-warn" : "text-faint"
                  }`}
                >
                  {words.toLocaleString()} word{words === 1 ? "" : "s"} ·{" "}
                  {countWords(text).toLocaleString()} / {MAX_WORDS.toLocaleString()}
                </p>
              )}
            </div>

            <textarea
              id="ai-detect-text"
              value={text}
              rows={10}
              spellCheck={false}
              onChange={(event) => {
                setText(event.target.value);
                setForceText(false);
                clearResult();
              }}
              placeholder="Paste an article, an essay, a product description or a batch of copy — or paste a URL such as example.com/blog/post. 200 words or more, or the result will not mean much."
              className="mt-2 w-full resize-y rounded-lg border border-edge2 bg-bg px-3.5 py-3 text-sm leading-relaxed text-ink placeholder:text-faint focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
            />

            {pastedUrl && (
              <p className="mt-2 text-xs leading-relaxed text-faint">
                That looks like a web address, so pressing the button fetches the page and
                checks what it says rather than scoring the address itself.{" "}
                <button
                  type="button"
                  onClick={() => setForceText(true)}
                  className="text-accent transition-colors hover:text-accent-hi"
                >
                  Score it as text instead
                </button>
                .
              </p>
            )}
          </>
        ) : (
          <>
            <label
              htmlFor="ai-detect-url"
              className="font-mono text-[11px] uppercase tracking-widest text-faint"
            >
              Page address
            </label>
            <input
              id="ai-detect-url"
              name="url"
              type="text"
              inputMode="url"
              autoComplete="url"
              spellCheck={false}
              value={url}
              onChange={(event) => {
                setUrl(event.target.value.slice(0, 2000));
                clearResult();
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  run();
                }
              }}
              placeholder="example.com/blog/post"
              className="mt-2 h-11 w-full rounded-lg border border-edge2 bg-bg px-3.5 text-sm text-ink placeholder:text-faint focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
            />
            <p className="mt-2 text-xs leading-relaxed text-faint">
              We fetch the page once, strip the navigation, headers, footers and scripts,
              and hand the readable text to the classifier in your browser. The page text
              is not stored, and the model never runs on our side.
            </p>
          </>
        )}

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={run}
            disabled={disabled}
            className="inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-lg bg-accent px-5 text-sm font-medium text-white transition-colors hover:bg-accent-hi disabled:opacity-60"
          >
            {busy && <Loader2 size={15} className="animate-spin" />}
            {phase.kind === "fetching"
              ? "Reading the page…"
              : busy
                ? "Working…"
                : mode === "url" || pastedUrl
                  ? "Fetch and check this page"
                  : "Check this text"}
          </button>
          {(phase.kind === "done" ||
            phase.kind === "failed" ||
            phase.kind === "fetch-failed") && (
            <button
              type="button"
              onClick={reset}
              className="inline-flex h-11 items-center gap-2 rounded-lg border border-edge2 px-4 text-sm text-sub transition-colors hover:text-ink"
            >
              <RotateCcw size={14} />
              Check something else
            </button>
          )}
          {mode === "paste" && tooShort && words > 0 && (
            <p className="text-xs text-faint">
              {MIN_WORDS_TO_RUN - words} more word
              {MIN_WORDS_TO_RUN - words === 1 ? "" : "s"} before there is anything to
              read.
            </p>
          )}
        </div>

        {!modelReady && phase.kind !== "loading" && (
          <p className="mt-3 flex items-start gap-2 text-xs leading-relaxed text-faint">
            <Cpu size={13} className="mt-0.5 shrink-0" />
            <span>
              The classifier runs inside this tab. Nothing is downloaded until you press
              the button, and then it is about {DOWNLOAD_MB} MB of model, once — your
              browser keeps it, so every check after the first is instant and works
              offline.
            </span>
          </p>
        )}
        <p className="mt-2 flex items-start gap-2 text-xs leading-relaxed text-faint">
          <Lock size={13} className="mt-0.5 shrink-0" />
          <span>
            Pasted text is never uploaded — the model comes to the text, not the other way
            round. A URL is the one exception: we fetch that page from our server because
            a browser is not allowed to, then score it here in your tab. Nothing is
            stored either way.
          </span>
        </p>
      </div>

      {phase.kind === "fetching" && (
        <div className="mt-6 rounded-2xl border border-edge bg-panel p-5">
          <p className="flex items-center gap-2 text-sm text-ink">
            <Loader2 size={14} className="animate-spin text-accent" />
            Fetching the page and stripping it to readable text
          </p>
        </div>
      )}

      {phase.kind === "fetch-failed" && (
        <div className="mt-6 rounded-2xl border border-warn/25 bg-warn/5 p-5" role="alert">
          <div className="flex items-start gap-3">
            <AlertTriangle size={18} className="mt-0.5 text-warn" />
            <div>
              <p className="text-sm font-medium text-ink">{phase.failure.error}</p>
              {phase.failure.hint && (
                <p className="mt-1.5 text-sm leading-relaxed text-sub">
                  {phase.failure.hint}
                </p>
              )}
              <p className="mt-2 font-mono text-[11px] uppercase tracking-widest text-faint">
                {phase.failure.code}
              </p>
            </div>
          </div>
        </div>
      )}

      {phase.kind === "loading" && <LoadingCard progress={phase.progress} />}

      {phase.kind === "scoring" && (
        <div className="mt-6 rounded-2xl border border-edge bg-panel p-5">
          <p className="flex items-center gap-2 text-sm text-ink">
            <Loader2 size={14} className="animate-spin text-accent" />
            Reading the text — {phase.total} window
            {phase.total === 1 ? "" : "s"} to score
          </p>
        </div>
      )}

      {phase.kind === "failed" && (
        <div className="mt-6 rounded-2xl border border-warn/25 bg-warn/5 p-5" role="alert">
          <div className="flex items-start gap-3">
            <AlertTriangle size={18} className="mt-0.5 text-warn" />
            <div>
              <p className="text-sm font-medium text-ink">
                The detector could not finish.
              </p>
              <p className="mt-1.5 text-sm leading-relaxed text-sub">{phase.message}</p>
              <p className="mt-1.5 text-sm leading-relaxed text-sub">
                The usual causes are a dropped connection partway through the model
                download, or a browser with WebAssembly turned off. Try again — anything
                already downloaded is kept.
              </p>
            </div>
          </div>
        </div>
      )}

      {phase.kind === "done" && <Result analysis={phase.analysis} source={source} />}

      {phase.kind !== "done" && <Limitations />}
    </div>
  );
}

function ModeButton({
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
      className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors ${
        active ? "bg-panel2 text-ink" : "text-sub hover:text-ink"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}

function LoadingCard({ progress }: { progress: LoadProgress }) {
  const percent = Math.round(progress.percent);
  const known = progress.totalBytes > 0;
  return (
    <div className="mt-6 rounded-2xl border border-edge bg-panel p-5">
      <div className="flex items-center justify-between gap-4">
        <p className="flex items-center gap-2 text-sm text-ink">
          <Loader2 size={14} className="animate-spin text-accent" />
          {progress.message}
        </p>
        <p className="font-mono text-xs tabular-nums text-faint">
          {known
            ? `${mb(progress.loadedBytes)} / ${mb(progress.totalBytes)} MB · ${percent}%`
            : "starting"}
        </p>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-panel2">
        <div
          className="h-full rounded-full bg-accent transition-all duration-300"
          style={{ width: `${Math.max(percent, 3)}%` }}
        />
      </div>
      <p className="mt-3 text-xs leading-relaxed text-faint">
        First run only. The model is about {DOWNLOAD_MB} MB and your browser caches it, so
        the next check starts immediately — on this tab or a visit next month. On a slow
        connection this is a minute or two; leave the tab open.
      </p>
    </div>
  );
}

function Result({ analysis, source }: { analysis: Analysis; source: Source | null }) {
  const tone = toneFor(analysis.score);
  const shortText = analysis.verdict === "too-short";

  return (
    <div className="mt-8">
      {source && (
        <section className="mb-6 rounded-2xl border border-edge bg-panel p-5">
          <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
            Page read
          </p>
          <p className="mt-1.5 text-sm font-medium text-ink">
            {source.title ?? source.finalUrl}
          </p>
          <a
            href={source.finalUrl}
            target="_blank"
            rel="noopener noreferrer nofollow"
            className="mt-1 inline-flex items-center gap-1.5 text-xs text-accent transition-colors hover:text-accent-hi"
          >
            {source.finalUrl}
            <ExternalLink size={11} />
          </a>
          <p className="mt-2 text-xs text-faint">
            {source.blocks.toLocaleString()} readable blocks, {source.words.toLocaleString()}{" "}
            words on the page.
            {source.truncated && " The page is very long, so only the first part was read."}
            {source.words > analysis.words &&
              ` The check covers the first ${analysis.words.toLocaleString()} of them — the classifier takes ${MAX_WORDS.toLocaleString()} words at a time.`}
          </p>
        </section>
      )}

      <section className="rounded-2xl border border-edge bg-panel p-6">
        <div className="flex flex-wrap items-center gap-6">
          <Dial percent={analysis.score} ring={tone.ring} muted={shortText} />
          <div className="min-w-[16rem] flex-1">
            <p className={`font-display text-2xl tracking-tight ${shortText ? "text-sub" : tone.text}`}>
              {VERDICT_LABEL[analysis.verdict]}
            </p>
            <p className="mt-2 text-sm leading-relaxed text-sub">
              {VERDICT_BLURB[analysis.verdict]}
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[11px] text-faint">
              <span>{CONFIDENCE_LABEL[analysis.confidenceBand]} · {analysis.confidence}%</span>
              <span>{analysis.words.toLocaleString()} words</span>
              <span>
                {analysis.chunks.length} window{analysis.chunks.length === 1 ? "" : "s"}
              </span>
              {analysis.spread >= 20 && <span>uneven (±{analysis.spread})</span>}
            </div>
          </div>
        </div>

        <p className="mt-5 border-t border-edge pt-4 text-xs leading-relaxed text-sub">
          <strong className="font-medium text-ink">Read this as a probability, not a
          verdict.</strong>{" "}
          {shortText
            ? "There is not enough text here for the score to carry meaning, so we are not putting a number on the dial."
            : `${analysis.score}% is how much of this text a classifier put on the AI side of a line it learned from training data.`}{" "}
          Our confidence figure is capped at 85% because that is roughly where detectors of
          this kind top out — it is deliberately not the model&rsquo;s own certainty, which
          reads 100% even when the model is wrong.
        </p>
      </section>

      <Limitations />

      {analysis.flagged.length > 0 && (
        <section className="mt-6 rounded-2xl border border-edge bg-panel p-6">
          <h2 className="text-base font-medium text-ink">
            The passages that scored highest
          </h2>
          <p className="mt-1.5 text-sm leading-relaxed text-sub">
            These windows sat furthest onto the AI side. Read them — if they are the
            formal, list-like, heavily-hedged stretches, that is the classifier reacting
            to register rather than authorship.
          </p>
          <div className="mt-4 space-y-3">
            {analysis.flagged.map((chunk) => {
              const chunkTone = toneFor(chunk.ai * 100);
              return (
                <blockquote
                  key={chunk.index}
                  className={`rounded-xl border ${chunkTone.border} ${chunkTone.bg} p-4`}
                >
                  <p className={`font-mono text-[11px] font-medium ${chunkTone.text}`}>
                    Window {chunk.index + 1} · {Math.round(chunk.ai * 100)}%
                  </p>
                  <p className="mt-2 select-text text-sm leading-relaxed text-ink/90">
                    {chunk.text}
                  </p>
                </blockquote>
              );
            })}
          </div>
        </section>
      )}

      {analysis.chunks.length > 1 && (
        <section className="mt-6 rounded-2xl border border-edge bg-panel p-6">
          <h2 className="text-base font-medium text-ink">Window by window</h2>
          <p className="mt-1.5 text-sm leading-relaxed text-sub">
            The text is cut into roughly two-hundred-word windows and each is scored on
            its own. We measured the window size rather than guessing it: at forty words
            this model called 62% of hand-written prose AI, and at two hundred it called
            none of it. A document that swings between the two ends is more interesting
            than its average. Open any row to read the whole window it scored.
          </p>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[34rem] text-left text-sm">
              <thead>
                <tr className="border-b border-edge text-[11px] uppercase tracking-widest text-faint">
                  <th className="py-2 pr-3 font-mono font-normal">#</th>
                  <th className="py-2 pr-3 font-mono font-normal">Opening words</th>
                  <th className="py-2 pr-3 font-mono font-normal">Words</th>
                  <th className="py-2 font-mono font-normal">AI score</th>
                </tr>
              </thead>
              <tbody>
                {analysis.chunks.map((chunk) => (
                  <ChunkRow key={chunk.index} chunk={chunk} />
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <SurfaceSignals signals={analysis.signals} text={analysis.text} />

      {analysis.words < MIN_WORDS_TO_JUDGE && (
        <p className="mt-4 text-xs leading-relaxed text-warn">
          This text is {analysis.words} words. Under {MIN_WORDS_TO_JUDGE} the classifier
          has too little to go on and its answers move around a lot between similar
          passages. Add more text before you read anything into the number.
        </p>
      )}
    </div>
  );
}

/**
 * A score with no way to see what was scored is not showing its working. The row opens
 * to the full window, as a disclosure button rather than a click handler on the row, so
 * it works from the keyboard and announces its state.
 */
function ChunkRow({ chunk }: { chunk: ScoredChunk }) {
  const [open, setOpen] = useState(false);
  const percent = Math.round(chunk.ai * 100);
  const tone = toneFor(percent);
  const opening = chunk.text.split(/\s+/).slice(0, 9).join(" ");
  const panelId = `ai-window-${chunk.index}`;

  return (
    <>
      <tr className={`border-b border-edge/60 ${open ? "" : "last:border-0"}`}>
        <td className="py-2.5 pr-3 font-mono text-xs text-faint tabular-nums">
          {chunk.index + 1}
        </td>
        <td className="py-2.5 pr-3 text-sm text-sub">
          <button
            type="button"
            onClick={() => setOpen(!open)}
            aria-expanded={open}
            aria-controls={open ? panelId : undefined}
            className="flex items-start gap-1.5 rounded text-left text-sub transition-colors hover:text-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent/40"
          >
            <ChevronRight
              size={13}
              aria-hidden
              className={`mt-0.5 shrink-0 transition-transform ${open ? "rotate-90" : ""}`}
            />
            <span>
              {opening}…
              <span className="sr-only">
                {open ? " Hide the whole window" : " Show the whole window"}
              </span>
            </span>
          </button>
        </td>
        <td className="py-2.5 pr-3 font-mono text-xs text-faint tabular-nums">
          {chunk.words}
        </td>
        <td className="py-2.5">
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-24 overflow-hidden rounded-full bg-panel2">
              <div
                className="h-full rounded-full"
                style={{ width: `${percent}%`, background: tone.ring }}
              />
            </div>
            <span className={`font-mono text-xs tabular-nums ${tone.text}`}>{percent}%</span>
          </div>
        </td>
      </tr>
      {open && (
        <tr id={panelId} className="border-b border-edge/60 last:border-0">
          <td colSpan={4} className="pb-3">
            <div className={`rounded-xl border ${tone.border} ${tone.bg} p-4`}>
              <p className="font-mono text-[11px] text-faint">
                Window {chunk.index + 1} · {chunk.words} words · scored {percent}%
              </p>
              <p className="mt-2 select-text text-sm leading-relaxed whitespace-pre-wrap text-ink/90">
                {chunk.text}
              </p>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function Dial({
  percent,
  ring,
  muted,
}: {
  percent: number;
  ring: string;
  muted: boolean;
}) {
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  const filled = muted ? 0 : (Math.min(100, Math.max(0, percent)) / 100) * circumference;
  return (
    <div className="relative size-32 shrink-0">
      <svg viewBox="0 0 120 120" className="size-full -rotate-90">
        <circle
          cx="60"
          cy="60"
          r={radius}
          fill="none"
          strokeWidth="9"
          stroke="var(--color-panel2)"
        />
        <circle
          cx="60"
          cy="60"
          r={radius}
          fill="none"
          strokeWidth="9"
          strokeLinecap="round"
          stroke={muted ? "var(--color-edge2)" : ring}
          strokeDasharray={`${filled} ${circumference}`}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="font-display text-3xl leading-none"
          style={{ color: muted ? "var(--color-faint)" : ring }}
        >
          {muted ? "—" : `${percent}%`}
        </span>
        <span className="mt-1 font-mono text-[9px] uppercase tracking-widest text-faint">
          AI score
        </span>
      </div>
    </div>
  );
}

/**
 * Not collapsible, not dismissible, and shown before anyone has run anything. A detector
 * that hides this is selling certainty it does not have.
 */
function Limitations() {
  return (
    <section className="mt-6 rounded-2xl border border-warn/30 bg-warn/5 p-5 sm:p-6">
      <h2 className="flex items-center gap-2 text-base font-medium text-ink">
        <TriangleAlert size={17} className="text-warn" />
        What this score is not
      </h2>
      <ul className="mt-4 space-y-2.5 text-sm leading-relaxed text-ink/90">
        <li>
          <strong className="font-medium">It is not proof, and it is not evidence
          on its own.</strong>{" "}
          AI detectors of this class are right roughly 75–85% of the time. Nobody should
          lose a grade, a job or a contract on a number in that range.
        </li>
        <li>
          <strong className="font-medium">It flags non-native English writers.</strong>{" "}
          Simpler vocabulary and steadier sentence rhythm — the things you get when
          someone is writing in their second or third language — are exactly what pushes
          this model towards &ldquo;AI&rdquo;. It is a documented bias in every detector
          of this kind, and it lands on the people least able to argue with it.
        </li>
        <li>
          <strong className="font-medium">It flags formal and academic prose.</strong>{" "}
          We tested a passage of ordinary human research writing and the model scored it
          100% AI on every window. Technical documentation, legal writing, translated
          text and anything written to a house style all trip the same wire.
        </li>
        <li>
          <strong className="font-medium">It misses edited AI text.</strong> Run a
          generated draft through a paraphraser, or rewrite a third of the sentences by
          hand, and the score collapses. A low score means the text does not look
          generated. It does not mean a person wrote it.
        </li>
        <li>
          <strong className="font-medium">It needs {MIN_WORDS_TO_JUDGE}+ words.</strong>{" "}
          We measured this: on forty-word windows the model called 62% of hand-written
          prose AI. Short text does not get you a rougher answer, it gets you a wrong one,
          so below the floor we say so instead of printing a verdict.
        </li>
        <li>
          <strong className="font-medium">The surface signals are not the score.</strong>{" "}
          The repeated openers and stock phrases we highlight for you are counts, not
          evidence. They show what the text does, so you can judge it yourself — a
          highlighted sentence has not been accused of anything.
        </li>
        <li>
          <strong className="font-medium">Never use it to accuse someone.</strong> If a
          result concerns you, talk to the writer, ask about their process, look at the
          draft history. A percentage from a browser tab is a reason to have a
          conversation and nothing more than that.
        </li>
      </ul>
      <p className="mt-4 flex items-start gap-2 text-xs leading-relaxed text-sub">
        <CheckCircle2 size={13} className="mt-0.5 shrink-0 text-good" />
        <span>
          What it is good for: spot-checking freelance or agency copy before you publish
          it, sanity-checking a batch of programmatic pages, and settling your own
          suspicion about a draft one way or the other.
        </span>
      </p>
    </section>
  );
}
