import type { Band, MatchKind } from "@/lib/similarity/types";

export const BAND_TEXT: Record<Band, string> = {
  original: "text-good",
  partial: "text-warn",
  high: "text-bad",
};

export const BAND_RING: Record<Band, string> = {
  original: "border-good/25 bg-good/5",
  partial: "border-warn/25 bg-warn/5",
  high: "border-bad/25 bg-bad/5",
};

export const BAND_LABEL: Record<Band, string> = {
  original: "Under 30% — original",
  partial: "30–60% — partly duplicated",
  high: "Over 60% — heavily duplicated",
};

export const KIND_LABEL: Record<MatchKind, string> = {
  exact: "Exact",
  near: "Near-exact",
  close: "Close",
};

export const KIND_CLASS: Record<MatchKind, string> = {
  exact: "border-bad/25 bg-bad/10 text-bad",
  near: "border-warn/25 bg-warn/10 text-warn",
  close: "border-accent/25 bg-accent/10 text-accent",
};

/** How a matched sentence is tinted inside the side-by-side view. */
export const KIND_MARK: Record<MatchKind, string> = {
  exact: "bg-bad/12 decoration-bad/40",
  near: "bg-warn/15 decoration-warn/40",
  close: "bg-accent/10 decoration-accent/40",
};

export function KindPill({ kind, score }: { kind: MatchKind; score: number }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 font-mono text-[11px] font-medium whitespace-nowrap ${KIND_CLASS[kind]}`}
    >
      {KIND_LABEL[kind]}
      <span className="tabular-nums opacity-70">{score}%</span>
    </span>
  );
}

export function download(name: string, body: string) {
  // The byte-order mark is what makes Excel read the file as UTF-8.
  const blob = new Blob([`﻿${body}`], { type: "text/csv;charset=utf-8;" });
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(href);
}
