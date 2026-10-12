"use client";

import { useState } from "react";
import { AlertTriangle, Link2, Loader2 } from "lucide-react";
import { MAX_WORDS, compare } from "@/lib/similarity/compare";
import { countWords } from "@/lib/limits";
import { detect } from "@/lib/similarity/input";
import type { SimilarityResult } from "@/lib/similarity/types";
import { SimilarityResults, type Sources } from "./results";

type Side = "a" | "b";

type Failure = { error: string; hint?: string; code: string };

type Phase =
  | { kind: "idle" }
  | { kind: "fetching" }
  | { kind: "comparing" }
  | { kind: "done"; result: SimilarityResult; sources: Sources }
  | { kind: "failed"; failure: Failure };

const EXAMPLE_A =
  "Search engines do not have a duplicate content penalty in the way most people imagine. What they have is a filter. When Google finds two pages that say the same thing, it picks one and drops the other out of the results for that query. Nobody gets punished; one page simply stops earning traffic.\n\nThe usual cause is not plagiarism at all. It is a store that lists the same product under four category paths, or a printer-friendly version of every article, or a staging site that got indexed by accident.";

const EXAMPLE_B =
  "Search engines do not have a duplicate content penalty in the way most people imagine. What they have is a filter. When Google finds two pages that say the same thing, it picks one and drops the other out of the results for that query.\n\nWhere duplication genuinely costs you is at scale. If half your pages are near copies of each other, crawl budget goes on pages that will never rank, and the pages that could rank get visited less often.";

export function SimilarityChecker() {
  const [text, setText] = useState<Record<Side, string>>({ a: "", b: "" });
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });

  const busy = phase.kind === "fetching" || phase.kind === "comparing";
  const inputs = { a: detect(text.a), b: detect(text.b) };
  const ready = inputs.a.kind !== "empty" && inputs.b.kind !== "empty";

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (busy || !ready) return;

    const sources: Sources = {};
    const bodies: Record<Side, string> = { a: "", b: "" };
    const wanted: Partial<Record<Side, string>> = {};

    for (const side of ["a", "b"] as const) {
      const input = inputs[side];
      if (input.kind === "url") wanted[side] = input.url;
      else if (input.kind === "text") bodies[side] = input.text;
    }

    if (wanted.a || wanted.b) {
      setPhase({ kind: "fetching" });
      let response: Response;
      try {
        response = await fetch("/api/tools/similarity", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(wanted),
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
        documents?: Partial<
          Record<Side, { url: string; finalUrl: string; title: string | null; text: string }>
        >;
        errors?: Partial<Record<Side, Failure>>;
        error?: string;
        hint?: string;
        code?: string;
      } | null;

      if (!response.ok || !payload) {
        setPhase({
          kind: "failed",
          failure: {
            error: payload?.error ?? "The page could not be fetched.",
            hint: payload?.hint,
            code: payload?.code ?? "unreachable",
          },
        });
        return;
      }

      for (const side of ["a", "b"] as const) {
        if (!wanted[side]) continue;
        const failure = payload.errors?.[side];
        if (failure) {
          setPhase({
            kind: "failed",
            failure: {
              error: `Document ${side.toUpperCase()}: ${failure.error}`,
              hint: failure.hint,
              code: failure.code,
            },
          });
          return;
        }
        const page = payload.documents?.[side];
        if (!page) {
          setPhase({
            kind: "failed",
            failure: {
              error: `Document ${side.toUpperCase()} came back empty.`,
              hint: "Paste the text instead.",
              code: "empty",
            },
          });
          return;
        }
        bodies[side] = page.text;
        sources[side] = {
          url: page.url,
          finalUrl: page.finalUrl,
          title: page.title,
        };
      }
    }

    setPhase({ kind: "comparing" });
    // Yield once so the button repaints before a synchronous comparison starts.
    await new Promise((resolve) => setTimeout(resolve, 0));
    setPhase({ kind: "done", result: compare(bodies.a, bodies.b), sources });
  }

  return (
    <div>
      <form onSubmit={submit} className="rounded-2xl border border-edge bg-panel p-5 sm:p-6">
        <div className="grid gap-4 sm:grid-cols-2">
          {(["a", "b"] as const).map((side) => (
            <Box
              key={side}
              side={side}
              value={text[side]}
              isUrl={inputs[side].kind === "url"}
              onChange={(value) =>
                setText((held) => ({ ...held, [side]: value }))
              }
            />
          ))}
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="submit"
            disabled={busy || !ready}
            className="inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-lg bg-accent px-5 text-sm font-medium text-white transition-colors hover:bg-accent-hi disabled:opacity-60"
          >
            {busy && <Loader2 size={15} className="animate-spin" />}
            {phase.kind === "fetching"
              ? "Fetching pages…"
              : phase.kind === "comparing"
                ? "Comparing…"
                : "Compare for duplicates"}
          </button>
          <button
            type="button"
            onClick={() => {
              setText({ a: EXAMPLE_A, b: EXAMPLE_B });
              setPhase({ kind: "idle" });
            }}
            className="text-sm text-accent transition-colors hover:text-accent-hi"
          >
            Load an example
          </button>
          {(text.a || text.b) && (
            <button
              type="button"
              onClick={() => {
                setText({ a: "", b: "" });
                setPhase({ kind: "idle" });
              }}
              className="text-sm text-sub transition-colors hover:text-ink"
            >
              Clear
            </button>
          )}
        </div>

        <p className="mt-3 text-xs text-faint">
          Free, no sign-up. Pasted text is compared inside your browser and is never uploaded —
          only a URL is sent to our server, and only so the page can be fetched. Up to{" "}
          {MAX_WORDS.toLocaleString()} words a side.
        </p>
      </form>

      {phase.kind === "failed" && (
        <ErrorCard failure={phase.failure} onReset={() => setPhase({ kind: "idle" })} />
      )}

      {phase.kind === "done" && (
        <SimilarityResults
          result={phase.result}
          sources={phase.sources}
          onReset={() => {
            setPhase({ kind: "idle" });
            setText({ a: "", b: "" });
          }}
        />
      )}
    </div>
  );
}

function Box({
  side,
  value,
  isUrl,
  onChange,
}: {
  side: Side;
  value: string;
  isUrl: boolean;
  onChange: (value: string) => void;
}) {
  const label = side.toUpperCase();
  const words = countWords(value);
  const over = words > MAX_WORDS;
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <label
          htmlFor={`similarity-${side}`}
          className="font-mono text-[11px] uppercase tracking-widest text-faint"
        >
          Document {label}
        </label>
        {isUrl ? (
          <span className="inline-flex items-center gap-1 font-mono text-[11px] text-accent">
            <Link2 size={11} />
            URL — we will fetch it
          </span>
        ) : (
          <span
            className={`font-mono text-[11px] tabular-nums ${over ? "text-bad" : "text-faint"}`}
          >
            {words.toLocaleString()} / {MAX_WORDS.toLocaleString()}
          </span>
        )}
      </div>
      <textarea
        id={`similarity-${side}`}
        name={`document-${side}`}
        value={value}
        spellCheck={false}
        onChange={(e) => onChange(e.target.value)}
        rows={9}
        placeholder={
          side === "a"
            ? "Paste your text here — or paste a URL such as example.com/blog/post"
            : "Paste the text you are comparing against, or its URL"
        }
        className="mt-2 w-full resize-y rounded-lg border border-edge2 bg-bg p-3.5 text-sm leading-relaxed text-ink placeholder:text-faint focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
      />
      {over && (
        <p className="mt-1 text-xs text-warn">
          Only the first {MAX_WORDS.toLocaleString()} words will be compared.
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
