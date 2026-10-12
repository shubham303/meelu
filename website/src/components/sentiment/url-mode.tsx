"use client";

/**
 * Scoring a review page rather than a CSV.
 *
 * A review page is not one piece of writing — it is dozens of separate
 * opinions stacked on one URL. Scoring the page as a single text would let a
 * furious review cancel a delighted one out and report "neutral", which is the
 * one answer that is always wrong. So the page is split into blocks and every
 * block is scored as its own review, exactly as a row of a CSV would be. The
 * passages are then shown back with their scores, so it is always visible which
 * text was read.
 *
 * The fetch goes through /api/tools/readability. That route already does the
 * whole job — it fetches a URL, refuses private addresses, strips the markup
 * and returns the readable blocks — and it returns exactly the shape this tool
 * needs, so a second near-identical endpoint would only be another copy of the
 * same error handling to keep in step. The scoring still happens here, in the
 * browser; the server only fetches and strips.
 *
 * Both entry points share the code below: the explicit "Review page URL" tab,
 * and the paste box when what was pasted turns out to be nothing but a URL.
 */

import { useState } from "react";
import { AlertTriangle, ExternalLink, Loader2 } from "lucide-react";
import type { PageBlock } from "@/lib/page-text/types";
import type { AnalysisResult } from "@/lib/sentiment/types";
import { SentimentResults } from "./results";

type Failure = { error: string; hint?: string; code: string };

type Page = {
  url: string;
  finalUrl: string;
  title: string | null;
  blocks: PageBlock[];
  text: string;
  words: number;
  truncated: boolean;
};

export type PageScore = {
  page: Page;
  result: AnalysisResult;
  stem: string;
  kept: number;
};

type Phase =
  | { kind: "idle" }
  | { kind: "fetching" }
  | { kind: "done"; score: PageScore }
  | { kind: "failed"; failure: Failure };

/** Headings and one-line furniture are labels, not opinions. */
function reviewBlocks(blocks: PageBlock[]): PageBlock[] {
  return blocks.filter(
    (block) => block.kind !== "heading" && block.kind !== "cell" && block.words >= 5,
  );
}

function stemFor(finalUrl: string): string {
  try {
    return `${new URL(finalUrl).hostname.replace(/^www\./, "").replace(/[^a-z0-9]+/gi, "-")}-sentiment`;
  } catch {
    return "page-sentiment";
  }
}

/**
 * Fetch a page and score every passage on it. Shared by the URL tab and by the
 * paste box, which lands here when the pasted content is only a URL.
 */
export async function fetchPageScore(
  raw: string,
): Promise<{ ok: true; score: PageScore } | { ok: false; failure: Failure }> {
  let response: Response;
  try {
    response = await fetch("/api/tools/readability", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: raw.trim() }),
    });
  } catch {
    return {
      ok: false,
      failure: {
        error: "Could not reach the page fetcher.",
        hint: "Paste the review itself instead — that path never touches our server.",
        code: "unreachable",
      },
    };
  }

  const payload = (await response.json().catch(() => null)) as {
    page?: Page;
    error?: string;
    hint?: string;
    code?: string;
  } | null;

  if (!response.ok || !payload?.page) {
    return {
      ok: false,
      failure: {
        error: payload?.error ?? "The page could not be read.",
        hint: payload?.hint,
        code: payload?.code ?? "unreachable",
      },
    };
  }

  const page = payload.page;
  const passages = reviewBlocks(page.blocks);

  if (passages.length === 0) {
    return {
      ok: false,
      failure: {
        error: "No passages long enough to score came back from that page.",
        hint: "The reviews may be built with JavaScript, which this fetch does not run. Copy them into the paste box or a CSV instead.",
        code: "empty",
      },
    };
  }

  const started = performance.now();
  const { analyzeParsed } = await import("@/lib/sentiment/analyze");
  const parsed = {
    headers: ["Review text"],
    rows: passages.map((block) => [block.text]),
    delimiter: ",",
    truncated: page.truncated,
    totalRows: passages.length,
  };
  const analysis = analyzeParsed(parsed, { textColumn: 0, ratingColumn: null });

  // analyzeParsed numbers rows as they sit in a spreadsheet, header included.
  // On a page there is no header row, so passage one should read as one.
  for (const row of analysis.rows) row.line -= 1;

  return {
    ok: true,
    score: {
      page,
      kept: passages.length,
      stem: stemFor(page.finalUrl),
      result: {
        ...analysis,
        textColumn: "passages read off the page",
        parsed,
        elapsedMs: Math.round(performance.now() - started),
      },
    },
  };
}

/** The page that was read, then every passage on it scored. */
export function PageReport({ score }: { score: PageScore }) {
  return (
    <>
      <div className="mt-4 rounded-2xl border border-edge bg-panel p-5">
        <p className="font-mono text-[11px] uppercase tracking-widest text-faint">Page read</p>
        <p className="mt-1.5 text-sm font-medium text-ink">
          {score.page.title ?? score.page.finalUrl}
        </p>
        <a
          href={score.page.finalUrl}
          target="_blank"
          rel="noopener noreferrer nofollow"
          className="mt-1 inline-flex items-center gap-1.5 text-xs text-accent transition-colors hover:text-accent-hi"
        >
          {score.page.finalUrl}
          <ExternalLink size={11} />
        </a>
        <p className="mt-2 text-xs text-faint">
          {score.kept.toLocaleString()} passages scored, one at a time, out of{" "}
          {score.page.blocks.length.toLocaleString()} readable blocks — headings and very
          short lines were left out. Every passage is listed below with the words that
          moved its score, so you can see exactly what was read.
          {score.page.truncated && " The page is very long, so only the first part was read."}
        </p>
      </div>

      <SentimentResults result={score.result} fileStem={score.stem} />
    </>
  );
}

export function PageFailure({
  failure,
  onReset,
}: {
  failure: Failure;
  onReset: () => void;
}) {
  return (
    <div className="mt-3 rounded-2xl border border-warn/25 bg-warn/5 p-5" role="alert">
      <div className="flex items-start gap-3">
        <AlertTriangle size={18} className="mt-0.5 shrink-0 text-warn" />
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

export function UrlMode() {
  const [url, setUrl] = useState("");
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });

  const busy = phase.kind === "fetching";

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (busy || url.trim().length === 0) return;

    setPhase({ kind: "fetching" });
    const outcome = await fetchPageScore(url);
    setPhase(
      outcome.ok
        ? { kind: "done", score: outcome.score }
        : { kind: "failed", failure: outcome.failure },
    );
  }

  return (
    <div>
      <form onSubmit={submit} className="mt-3 rounded-2xl border border-edge bg-panel p-5 sm:p-6">
        <label
          htmlFor="sentiment-url"
          className="font-mono text-[11px] uppercase tracking-widest text-faint"
        >
          Page address
        </label>
        <div className="mt-2 flex flex-wrap gap-3">
          <input
            id="sentiment-url"
            name="url"
            type="text"
            inputMode="url"
            autoComplete="url"
            spellCheck={false}
            value={url}
            onChange={(event) => setUrl(event.target.value.slice(0, 2000))}
            placeholder="example.com/product/reviews"
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

        <p className="mt-3 text-xs text-faint">
          We fetch the page once, strip the navigation, headers, footers and scripts, and
          score each passage that is left as its own review. The scoring runs in this tab
          and nothing is stored.
        </p>
      </form>

      {phase.kind === "failed" && (
        <PageFailure failure={phase.failure} onReset={() => setPhase({ kind: "idle" })} />
      )}

      {phase.kind === "done" && <PageReport score={phase.score} />}

      {phase.kind === "idle" && (
        <p className="mt-3 rounded-2xl border border-dashed border-edge2 bg-panel/40 p-10 text-center text-sm text-sub">
          Give it the address of a reviews page and every review on it comes back
          labelled, with the complaints ranked and the same CSV export you get from a
          file.
        </p>
      )}
    </div>
  );
}
