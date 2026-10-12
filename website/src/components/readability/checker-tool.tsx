"use client";

import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ClipboardType,
  ExternalLink,
  Link2,
  Loader2,
  Lock,
  RotateCcw,
  Wand2,
} from "lucide-react";
import { MAX_WORDS, analyse, type ReadabilityReport } from "@/lib/readability/analyse";
import { countWords } from "@/lib/limits";
import { detect } from "@/lib/similarity/input";
import type { PageBlock } from "@/lib/page-text/types";
import { SAMPLE_TEXT } from "@/lib/readability/sample";
import { PageBlockResults, scoreBlocks, type ScoredBlock } from "./page-blocks";
import { ReadabilityResults } from "./results";

type Mode = "paste" | "url";

type Failure = { error: string; hint?: string; code: string };

type Page = {
  url: string;
  finalUrl: string;
  title: string | null;
  blocks: PageBlock[];
  text: string;
  words: number;
  truncated: boolean;
  usedFallback?: boolean;
};

type UrlPhase =
  | { kind: "idle" }
  | { kind: "fetching" }
  | { kind: "done"; page: Page; report: ReadabilityReport; scored: ScoredBlock[] }
  | { kind: "failed"; failure: Failure };

export function ReadabilityChecker() {
  const [mode, setMode] = useState<Mode>("paste");
  /** A URL pasted into the text box, handed to the URL mode to fetch straight away. */
  const [handoff, setHandoff] = useState("");
  /** Set when the visitor overrides the detection and wants the URL scored as text. */
  const [forceText, setForceText] = useState(false);

  return (
    <div>
      <div className="mb-3 inline-flex items-center gap-1 rounded-lg border border-edge2 bg-panel p-1">
        <ModeButton
          active={mode === "paste"}
          onClick={() => {
            setMode("paste");
            setHandoff("");
          }}
          icon={<ClipboardType size={13} />}
          label="Paste text"
        />
        <ModeButton
          active={mode === "url"}
          onClick={() => {
            setMode("url");
            setHandoff("");
          }}
          icon={<Link2 size={13} />}
          label="Web page URL"
        />
      </div>

      {mode === "paste" ? (
        <PasteMode
          forceText={forceText}
          onUrlPasted={(url) => {
            setHandoff(url);
            setMode("url");
          }}
        />
      ) : (
        <UrlMode
          initialUrl={handoff}
          onScoreAsText={
            handoff
              ? () => {
                  setForceText(true);
                  setHandoff("");
                  setMode("paste");
                }
              : undefined
          }
        />
      )}
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

function PasteMode({
  forceText,
  onUrlPasted,
}: {
  forceText: boolean;
  onUrlPasted: (url: string) => void;
}) {
  const [text, setText] = useState("");
  const [settled, setSettled] = useState("");

  // Debounced so a fast typist is not re-scoring on every keystroke.
  useEffect(() => {
    const timer = window.setTimeout(() => setSettled(text), 250);
    return () => window.clearTimeout(timer);
  }, [text]);

  // A pasted address is almost never something you want scored as prose: it
  // would be one "sentence" of four words. Hand it to the fetcher instead,
  // unless the visitor has said they meant it as text.
  useEffect(() => {
    if (forceText || settled.trim().length === 0) return;
    const input = detect(settled);
    if (input.kind === "url") onUrlPasted(input.url);
  }, [settled, forceText, onUrlPasted]);

  const report: ReadabilityReport | null = useMemo(() => {
    if (settled.trim().length === 0) return null;
    const next = analyse(settled);
    return next.empty ? null : next;
  }, [settled]);

  const shown = text.trim().length === 0 ? null : report;

  const used = countWords(text);
  const nearLimit = used > MAX_WORDS * 0.9;

  return (
    <div>
      <div className="rounded-2xl border border-edge bg-panel p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <label
            htmlFor="readability-text"
            className="font-mono text-[11px] uppercase tracking-widest text-faint"
          >
            Paste your text
          </label>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setText(SAMPLE_TEXT)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-edge2 bg-panel px-2.5 py-1.5 text-xs text-ink transition-colors hover:bg-panel2"
            >
              <Wand2 size={13} />
              Paste a sample
            </button>
            {used > 0 && (
              <button
                type="button"
                onClick={() => setText("")}
                className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs text-sub transition-colors hover:bg-panel2 hover:text-ink"
              >
                <RotateCcw size={13} />
                Clear
              </button>
            )}
          </div>
        </div>

        <textarea
          id="readability-text"
          name="text"
          value={text}
          onChange={(event) => setText(event.target.value)}
          spellCheck={false}
          rows={12}
          placeholder="Paste your article, landing page, email or product description here. Scores appear as you type."
          className="mt-3 w-full resize-y rounded-lg border border-edge2 bg-bg p-3.5 text-sm leading-relaxed text-ink placeholder:text-faint focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
        />

        <div className="mt-2 flex flex-wrap items-center justify-between gap-3">
          <p className="inline-flex items-center gap-1.5 text-xs text-faint">
            <Lock size={12} className="text-good" />
            Analysed in this browser tab. Your text is never uploaded.
          </p>
          <p
            className={`font-mono text-xs tabular-nums ${nearLimit ? "text-warn" : "text-faint"}`}
          >
            {used.toLocaleString()} / {MAX_WORDS.toLocaleString()} words
          </p>
        </div>
      </div>

      {shown ? (
        <ReadabilityResults report={shown} />
      ) : (
        <p className="mt-6 rounded-2xl border border-dashed border-edge2 bg-panel/40 p-10 text-center text-sm text-sub">
          Six readability formulas, the sentence-by-sentence breakdown and the
          arithmetic behind every number appear here as soon as there is text to
          score.
        </p>
      )}
    </div>
  );
}

function UrlMode({
  initialUrl = "",
  onScoreAsText,
}: {
  initialUrl?: string;
  onScoreAsText?: () => void;
}) {
  const [url, setUrl] = useState(initialUrl);
  const [phase, setPhase] = useState<UrlPhase>({ kind: "idle" });

  const busy = phase.kind === "fetching";

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (busy || url.trim().length === 0) return;

    setPhase({ kind: "fetching" });

    let response: Response;
    try {
      response = await fetch("/api/tools/readability", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url.trim() }),
      });
    } catch {
      setPhase({
        kind: "failed",
        failure: {
          error: "Could not reach the page fetcher.",
          hint: "Paste the text instead — that path never touches our server.",
          code: "unreachable",
        },
      });
      return;
    }

    const payload = (await response.json().catch(() => null)) as {
      page?: Page;
      error?: string;
      hint?: string;
      code?: string;
    } | null;

    if (!response.ok || !payload?.page) {
      setPhase({
        kind: "failed",
        failure: {
          error: payload?.error ?? "The page could not be read.",
          hint: payload?.hint,
          code: payload?.code ?? "unreachable",
        },
      });
      return;
    }

    const page = payload.page;
    // The same word limit the paste box uses, so the two paths agree.
    const report = analyse(page.text);
    if (report.empty) {
      setPhase({
        kind: "failed",
        failure: {
          error: "No readable sentences came back from that page.",
          hint: "The page may build its content with JavaScript. Paste the text instead.",
          code: "empty",
        },
      });
      return;
    }

    setPhase({ kind: "done", page, report, scored: scoreBlocks(page.blocks) });
  }

  return (
    <div>
      <form onSubmit={submit} className="rounded-2xl border border-edge bg-panel p-5 sm:p-6">
        <label
          htmlFor="readability-url"
          className="font-mono text-[11px] uppercase tracking-widest text-faint"
        >
          Page address
        </label>
        <div className="mt-2 flex flex-wrap gap-3">
          <input
            id="readability-url"
            name="url"
            type="text"
            inputMode="url"
            autoComplete="url"
            spellCheck={false}
            value={url}
            onChange={(event) => setUrl(event.target.value.slice(0, 2000))}
            placeholder="example.com/blog/post"
            className="h-11 min-w-0 flex-1 rounded-lg border border-edge2 bg-bg px-3.5 text-sm text-ink placeholder:text-faint focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
          <button
            type="submit"
            disabled={busy || url.trim().length === 0}
            className="inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-lg bg-accent px-5 text-sm font-medium text-white transition-colors hover:bg-accent-hi disabled:opacity-60"
          >
            {busy && <Loader2 size={15} className="animate-spin" />}
            {busy ? "Reading the page…" : "Score this page"}
          </button>
        </div>

        {onScoreAsText && (
          <p className="mt-3 inline-flex flex-wrap items-center gap-1.5 text-xs text-sub">
            <Link2 size={12} className="text-accent" />
            That looked like a web address, so we will fetch the page.
            <button
              type="button"
              onClick={onScoreAsText}
              className="font-medium text-accent underline underline-offset-2 hover:text-accent-hi"
            >
              Score it as text instead
            </button>
          </p>
        )}

        <p className="mt-3 text-xs text-faint">
          Free, no sign-up. We fetch the page once, strip the navigation, headers,
          footers and scripts, and score what is left — both as a whole and
          passage by passage. Nothing is stored.
        </p>
      </form>

      {phase.kind === "failed" && (
        <ErrorCard failure={phase.failure} onReset={() => setPhase({ kind: "idle" })} />
      )}

      {phase.kind === "done" && (
        <>
          <div className="mt-6 rounded-2xl border border-edge bg-panel p-5">
            <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
              Page read
            </p>
            <p className="mt-1.5 text-sm font-medium text-ink">
              {phase.page.title ?? phase.page.finalUrl}
            </p>
            <a
              href={phase.page.finalUrl}
              target="_blank"
              rel="noopener noreferrer nofollow"
              className="mt-1 inline-flex items-center gap-1.5 text-xs text-accent transition-colors hover:text-accent-hi"
            >
              {phase.page.finalUrl}
              <ExternalLink size={11} />
            </a>
            <p className="mt-2 text-xs text-faint">
              {phase.page.blocks.length.toLocaleString()} readable blocks,{" "}
              {phase.page.words.toLocaleString()} words.
              {phase.page.truncated && " The page is very long, so only the first part was read."}
              {phase.page.words > MAX_WORDS &&
                ` The whole-page score covers the first ${MAX_WORDS.toLocaleString()} words; every passage below is scored in full.`}
              {phase.page.usedFallback &&
                " This page has no paragraph markup, so the passages were split on its line breaks and may be rougher than usual."}

            </p>
          </div>

          <ReadabilityResults report={phase.report} />
          <PageBlockResults scored={phase.scored} />
        </>
      )}

      {phase.kind === "idle" && (
        <p className="mt-6 rounded-2xl border border-dashed border-edge2 bg-panel/40 p-10 text-center text-sm text-sub">
          Give it a URL and you get the six formulas for the whole page, plus
          every paragraph, heading and list item scored on its own so the hard
          passages are easy to find.
        </p>
      )}
    </div>
  );
}

function ErrorCard({ failure, onReset }: { failure: Failure; onReset: () => void }) {
  return (
    <div className="mt-6 rounded-2xl border border-warn/25 bg-warn/5 p-5" role="alert">
      <div className="flex items-start gap-3">
        <AlertTriangle size={18} className="mt-0.5 text-warn" />
        <div>
          <p className="text-sm font-medium text-ink">{failure.error}</p>
          {failure.hint && (
            <p className="mt-1.5 text-sm leading-relaxed text-sub">{failure.hint}</p>
          )}
          <p className="mt-2 font-mono text-[11px] uppercase tracking-widest text-faint">
            {failure.code}
          </p>
          <button
            type="button"
            onClick={onReset}
            className="mt-3 text-sm text-accent transition-colors hover:text-accent-hi"
          >
            Try again
          </button>
        </div>
      </div>
    </div>
  );
}
