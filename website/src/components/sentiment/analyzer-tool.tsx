"use client";

import { useCallback, useRef, useState } from "react";
import { FileSpreadsheet, Link2, Loader2, Lock, Upload } from "lucide-react";
import { MAX_ROWS, fileStem } from "@/lib/sentiment/csv";
import { detect } from "@/lib/similarity/input";
import type { AnalysisResult, Scored } from "@/lib/sentiment/types";
import { SentimentResults, SingleResult } from "./results";
import { PageFailure, PageReport, UrlMode, fetchPageScore, type PageScore } from "./url-mode";

const MAX_BYTES = 25 * 1024 * 1024;

const SAMPLE = `Absolutely brilliant. Arrived a day early and works perfectly.
Ordered on the 3rd, delivered on the 7th. Two units in one box.
Arrived damaged and the refund took forever. No response from support.
The room was lovely but the service was appalling.
Not worth the money — flimsy, and it fell apart after a week.`;

type PagePhase =
  | { kind: "idle" }
  | { kind: "fetching" }
  | { kind: "done"; score: PageScore }
  | { kind: "failed"; failure: { error: string; hint?: string; code: string } };

type Phase =
  | { kind: "idle" }
  | { kind: "reading" }
  | { kind: "scoring" }
  | { kind: "done"; result: AnalysisResult; stem: string }
  | { kind: "failed"; message: string; hint?: string };

export function ReviewSentimentAnalyzer() {
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const [mode, setMode] = useState<"file" | "paste" | "url">("file");
  const [dragging, setDragging] = useState(false);
  const [text, setText] = useState("");
  const [single, setSingle] = useState<Scored | null>(null);
  /** Set when the visitor overrides the detection and wants the URL read as words. */
  const [forceText, setForceText] = useState(false);
  const [pagePhase, setPagePhase] = useState<PagePhase>({ kind: "idle" });
  const [columns, setColumns] = useState<{ headers: string[]; textIndex: number } | null>(null);
  const input = useRef<HTMLInputElement>(null);

  const run = useCallback(async (raw: string, name: string, textColumn?: number) => {
    setPhase({ kind: "scoring" });
    // Yield once so the spinner paints before the main thread is taken.
    await new Promise((resolve) => setTimeout(resolve, 0));

    try {
      const { analyzeCsv } = await import("@/lib/sentiment/analyze");
      const result = analyzeCsv(raw, textColumn === undefined ? {} : { textColumn });

      if (result.rows.length === 0) {
        setPhase({
          kind: "failed",
          message: "No reviews found in that file.",
          hint: "Every row in the column we picked was empty. Check the file has a header row and at least one row of review text.",
        });
        return;
      }

      const headerIndex = result.parsed.headers.indexOf(result.textColumn);
      setColumns({ headers: result.parsed.headers, textIndex: headerIndex });
      setPhase({ kind: "done", result, stem: fileStem(name) });
    } catch (error) {
      setPhase({
        kind: "failed",
        message: "That file could not be read as a CSV.",
        hint: error instanceof Error ? error.message : undefined,
      });
    }
  }, []);

  const rawFile = useRef<{ text: string; name: string } | null>(null);

  const handleFile = useCallback(
    async (file: File) => {
      if (file.size > MAX_BYTES) {
        setPhase({
          kind: "failed",
          message: "That file is larger than 25 MB.",
          hint: "Split it, or cut the columns you do not need. The scoring is fast; it is the browser holding the whole file in memory that sets the limit.",
        });
        return;
      }

      setPhase({ kind: "reading" });
      try {
        const contents = await file.text();
        rawFile.current = { text: contents, name: file.name };
        await run(contents, file.name);
      } catch {
        setPhase({ kind: "failed", message: "The file could not be opened." });
      }
    },
    [run],
  );

  function scoreSingle(value: string) {
    setText(value);
    setForceText(false);
    setPagePhase({ kind: "idle" });
    if (value.trim().length === 0) {
      setSingle(null);
      return;
    }
    void import("@/lib/sentiment/analyze").then(({ analyzeText }) => {
      setSingle(analyzeText(value));
    });
  }

  // A review that happens to mention a website is still a review: detect() only
  // calls it a URL when the box holds nothing else, whitespace included.
  const detected = detect(text);
  const pastedUrl = !forceText && detected.kind === "url" ? detected.url : null;

  async function fetchPasted(target: string) {
    setPagePhase({ kind: "fetching" });
    const outcome = await fetchPageScore(target);
    setPagePhase(
      outcome.ok
        ? { kind: "done", score: outcome.score }
        : { kind: "failed", failure: outcome.failure },
    );
  }

  const busy = phase.kind === "reading" || phase.kind === "scoring";

  return (
    <div>
      <div className="flex gap-2">
        {(["file", "paste", "url"] as const).map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => setMode(option)}
            className={`rounded-lg border px-3 py-1.5 text-sm transition-colors ${
              mode === option
                ? "border-accent/30 bg-accent/10 text-accent"
                : "border-edge bg-panel text-sub hover:border-edge2 hover:text-ink"
            }`}
          >
            {option === "file"
              ? "Upload a CSV"
              : option === "paste"
                ? "Paste one review"
                : "Review page URL"}
          </button>
        ))}
      </div>

      {mode === "file" ? (
        <>
          <div
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDragging(false);
              const file = event.dataTransfer.files?.[0];
              if (file) void handleFile(file);
            }}
            className={`mt-3 rounded-2xl border-2 border-dashed p-8 text-center transition-colors ${
              dragging ? "border-accent bg-accent/5" : "border-edge2 bg-panel"
            }`}
          >
            <input
              ref={input}
              type="file"
              accept=".csv,text/csv,text/plain"
              className="hidden"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) void handleFile(file);
                event.target.value = "";
              }}
            />

            {busy ? (
              <div className="flex flex-col items-center gap-3 text-sub">
                <Loader2 size={22} className="animate-spin text-accent" />
                <p className="text-sm">
                  {phase.kind === "reading" ? "Reading the file" : "Scoring every review"}
                </p>
              </div>
            ) : (
              <>
                <Upload size={22} className="mx-auto text-accent" />
                <p className="mt-3 text-sm text-ink">
                  Drop a CSV of reviews here, or{" "}
                  <button
                    type="button"
                    onClick={() => input.current?.click()}
                    className="font-medium text-accent underline-offset-2 hover:underline"
                  >
                    choose a file
                  </button>
                </p>
                <p className="mt-1.5 text-xs text-faint">
                  Up to {MAX_ROWS.toLocaleString()} rows. The review column is found for
                  you. Nothing is uploaded.
                </p>
              </>
            )}
          </div>

          <p className="mt-3 flex items-center justify-center gap-1.5 text-xs text-faint">
            <Lock size={11} />
            The file is read and scored in this browser tab. It never reaches our
            server, so there is nothing for us to keep.
          </p>

          {phase.kind === "done" && columns && columns.headers.length > 1 && (
            <div className="mt-4 flex flex-wrap items-center gap-2 rounded-xl border border-edge bg-panel p-3">
              <FileSpreadsheet size={14} className="text-accent" />
              <label htmlFor="review-column" className="text-sm text-sub">
                Reading reviews from
              </label>
              <select
                id="review-column"
                value={columns.textIndex}
                onChange={(event) => {
                  const next = Number(event.target.value);
                  if (rawFile.current) {
                    void run(rawFile.current.text, rawFile.current.name, next);
                  }
                }}
                className="rounded-lg border border-edge bg-panel px-2 py-1 text-sm text-ink focus:border-accent focus:outline-none"
              >
                {columns.headers.map((header, index) => (
                  <option key={`${header}-${index}`} value={index}>
                    {header || `Column ${index + 1}`}
                  </option>
                ))}
              </select>
              <span className="text-xs text-faint">
                Wrong column? Pick the right one and it re-scores instantly.
              </span>
            </div>
          )}

          {phase.kind === "done" && phase.result.parsed.truncated && (
            <p className="mt-3 rounded-xl border border-warn/25 bg-warn/5 p-3 text-sm text-warn">
              That file has {phase.result.parsed.totalRows.toLocaleString()} rows. The
              first {MAX_ROWS.toLocaleString()} were scored — the rest were left out,
              so treat the shares as a sample rather than the whole file.
            </p>
          )}

          {phase.kind === "failed" && (
            <div className="mt-3 rounded-xl border border-bad/25 bg-bad/5 p-4">
              <p className="text-sm font-medium text-bad">{phase.message}</p>
              {phase.hint ? <p className="mt-1 text-sm text-sub">{phase.hint}</p> : null}
            </div>
          )}

          {phase.kind === "done" && (
            <SentimentResults result={phase.result} fileStem={phase.stem} />
          )}
        </>
      ) : mode === "paste" ? (
        <>
          <div className="mt-3 flex items-baseline justify-end">
            {pastedUrl && (
              <span className="inline-flex items-center gap-1 font-mono text-[11px] text-accent">
                <Link2 size={11} />
                URL — we will fetch it
              </span>
            )}
          </div>
          <textarea
            value={text}
            onChange={(event) => scoreSingle(event.target.value)}
            rows={5}
            placeholder="Paste a review and see how it scores — or paste the address of a reviews page and we will fetch it"
            className="mt-1 w-full resize-y rounded-2xl border border-edge bg-panel p-4 text-sm leading-relaxed text-ink placeholder:text-faint focus:border-accent focus:outline-none"
          />

          {pastedUrl ? (
            <div className="mt-2 flex flex-wrap items-center gap-3">
              <button
                type="button"
                onClick={() => void fetchPasted(pastedUrl)}
                disabled={pagePhase.kind === "fetching"}
                className="inline-flex h-9 items-center justify-center gap-2 rounded-lg bg-accent px-4 text-sm font-medium text-white transition-colors hover:bg-accent-hi disabled:opacity-60"
              >
                {pagePhase.kind === "fetching" && <Loader2 size={14} className="animate-spin" />}
                {pagePhase.kind === "fetching" ? "Reading the page…" : "Fetch and score that page"}
              </button>
              <button
                type="button"
                onClick={() => setForceText(true)}
                className="text-xs text-sub transition-colors hover:text-ink"
              >
                No — score those words as a review
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => scoreSingle(SAMPLE.split("\n")[3])}
              className="mt-2 text-xs text-accent hover:text-accent-hi"
            >
              Try one that trips most tools
            </button>
          )}

          {pagePhase.kind === "failed" && (
            <PageFailure
              failure={pagePhase.failure}
              onReset={() => setPagePhase({ kind: "idle" })}
            />
          )}
          {pagePhase.kind === "done" && <PageReport score={pagePhase.score} />}

          {!pastedUrl && single ? (
            <SingleResult compound={single.compound} label={single.label} hits={single.hits} />
          ) : null}
        </>
      ) : (
        <UrlMode />
      )}
    </div>
  );
}
