import type { ReactNode } from "react";
import type { SentenceFlag } from "@/lib/readability/analyse";
import type { Tone } from "@/lib/readability/scores";

export const TONE_TEXT: Record<Tone, string> = {
  good: "text-good",
  warn: "text-warn",
  bad: "text-bad",
};

export const TONE_PILL: Record<Tone, string> = {
  good: "border-good/25 bg-good/10 text-good",
  warn: "border-warn/25 bg-warn/10 text-warn",
  bad: "border-bad/25 bg-bad/10 text-bad",
};

export const TONE_DOT: Record<Tone, string> = {
  good: "bg-good",
  warn: "bg-warn",
  bad: "bg-bad",
};

export const FLAG_LABEL: Record<SentenceFlag, string> = {
  "very-long": "Very long",
  long: "Long",
  complex: "Complex words",
  passive: "Passive",
};

export const FLAG_TONE: Record<SentenceFlag, Tone> = {
  "very-long": "bad",
  long: "warn",
  complex: "warn",
  passive: "warn",
};

export function TonePill({ tone, children }: { tone: Tone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 font-mono text-[11px] font-medium whitespace-nowrap ${TONE_PILL[tone]}`}
    >
      <span className={`size-1.5 rounded-full ${TONE_DOT[tone]}`} />
      {children}
    </span>
  );
}

/** The eight Flesch bands drawn to scale across 0 to 100. */
export const GAUGE_SEGMENTS: Array<{ width: number; className: string; label: string }> = [
  { width: 10, className: "bg-bad/70", label: "0-10 extremely difficult" },
  { width: 20, className: "bg-bad/45", label: "10-30 very difficult" },
  { width: 20, className: "bg-warn/55", label: "30-50 difficult" },
  { width: 10, className: "bg-warn/35", label: "50-60 fairly difficult" },
  { width: 10, className: "bg-good/40", label: "60-70 plain English" },
  { width: 10, className: "bg-good/55", label: "70-80 fairly easy" },
  { width: 10, className: "bg-good/70", label: "80-90 easy" },
  { width: 10, className: "bg-good/85", label: "90-100 very easy" },
];

export function Stat({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string | number;
  hint?: string;
  tone?: Tone;
}) {
  return (
    <div className="rounded-xl border border-edge bg-bg p-3">
      <span className="font-mono text-[10px] uppercase tracking-widest text-faint">{label}</span>
      <span
        className={`mt-1 block font-display text-2xl tabular-nums ${tone ? TONE_TEXT[tone] : "text-ink"}`}
      >
        {value}
      </span>
      {hint && <span className="mt-0.5 block text-[11px] leading-snug text-faint">{hint}</span>}
    </div>
  );
}
