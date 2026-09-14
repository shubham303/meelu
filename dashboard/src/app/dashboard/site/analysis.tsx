"use client";

import { Info, ScanText, Square } from "lucide-react";
import { Button } from "@/components/ui";
import type { Analysis } from "./tracked-analysis";

export function AnalyseButton({ analysis }: { analysis: Analysis }) {
  const { status, running, stopping, canAnalyse, start, stop } = analysis;
  if (!canAnalyse) return null;
  return (
    <Button
      onClick={() => void (running ? stop() : start())}
      disabled={running && stopping}
    >
      {running ? (
        <>
          <Square className="mr-2 h-4 w-4" />
          {stopping ? "Stopping…" : "Stop analysis"}
        </>
      ) : (
        <>
          <ScanText className="mr-2 h-4 w-4" />
          {(status?.analyzedPages ?? 0) > 0 ? "Analyse again" : "Analyse pages"}
        </>
      )}
    </Button>
  );
}

export function AnalysisSummary({ analysis }: { analysis: Analysis }) {
  const { status, note, running, stopping } = analysis;

  const counted = (status?.analyzedPages ?? 0) > 0 || (status?.eligiblePages ?? 0) > 0;
  if (!running && !counted && !note) return null;
  const done =
    (status?.processed ?? 0) + (status?.skippedUnchanged ?? 0) + (status?.skippedSimilar ?? 0) + (status?.failed ?? 0);
  const total = status?.total ?? 0;
  const share = total > 0 ? Math.min(99, Math.round((done / total) * 100)) : null;

  return (
    <div className="space-y-1.5">
      {!running && counted && (
        <span className="inline-flex items-center gap-1.5 text-xs text-sub">
          {status?.analyzedPages ?? 0} of {status?.eligiblePages ?? 0} pages analysed by Meelu
          <span
            className="inline-flex cursor-help text-faint"
            title="Meelu reads each crawled page once and notes its topics, keywords and the questions it answers, so related pages can be found without rereading them."
          >
            <Info size={13} aria-label="What analysis means" />
          </span>
        </span>
      )}

      {!running && note && <div className="text-xs text-sub">{note}</div>}

      {running && (
        <>
          <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 text-xs">
            <span className="text-ink">
              {stopping ? "Stopping — the pages already analysed are kept" : "Analysing pages"} ·{" "}
              {done} of {total}
              {share !== null && <span className="ml-1 tabular-nums text-sub">{share}%</span>}
            </span>
            <span className="text-sub">
              {[
                (status?.processed ?? 0) > 0 && `${status?.processed} analysed`,
                (status?.skippedUnchanged ?? 0) + (status?.skippedSimilar ?? 0) > 0 &&
                  `${(status?.skippedUnchanged ?? 0) + (status?.skippedSimilar ?? 0)} unchanged, left alone`,
                (status?.failed ?? 0) > 0 && `${status?.failed} failed`,
              ]
                .filter(Boolean)
                .join(" · ")}
            </span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-panel2">
            {share === null ? (
              <div className="h-full w-1/5 rounded-full bg-accent animate-crawl-sweep" />
            ) : (
              <div
                className="h-full rounded-full bg-accent transition-[width] duration-500 ease-out"
                style={{ width: `${Math.max(share, 2)}%` }}
              />
            )}
          </div>
        </>
      )}
    </div>
  );
}
