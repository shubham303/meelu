import type { Label } from "@/lib/sentiment/types";

export const LABEL_TEXT: Record<Label, string> = {
  positive: "Positive",
  neutral: "Neutral",
  negative: "Negative",
};

export const LABEL_CLASS: Record<Label, string> = {
  positive: "border-good/25 bg-good/10 text-good",
  neutral: "border-edge2 bg-panel2 text-sub",
  negative: "border-bad/25 bg-bad/10 text-bad",
};

export const LABEL_DOT: Record<Label, string> = {
  positive: "bg-good",
  neutral: "bg-faint",
  negative: "bg-bad",
};

export const LABEL_FILL: Record<Label, string> = {
  positive: "bg-good",
  neutral: "bg-edge2",
  negative: "bg-bad",
};

export function LabelPill({ label }: { label: Label }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 font-mono text-[11px] font-medium whitespace-nowrap ${LABEL_CLASS[label]}`}
    >
      <span className={`size-1.5 rounded-full ${LABEL_DOT[label]}`} />
      {LABEL_TEXT[label]}
    </span>
  );
}

/** The three shares as one horizontal bar. */
export function SplitBar({
  positive,
  neutral,
  negative,
  height = "h-3",
}: {
  positive: number;
  neutral: number;
  negative: number;
  height?: string;
}) {
  return (
    <div className={`flex w-full overflow-hidden rounded-full bg-panel2 ${height}`}>
      <div className="bg-good" style={{ width: `${positive}%` }} />
      <div className="bg-edge2" style={{ width: `${neutral}%` }} />
      <div className="bg-bad" style={{ width: `${negative}%` }} />
    </div>
  );
}

export function StatCard({
  value,
  label,
  tone = "text-ink",
  hint,
}: {
  value: string;
  label: string;
  tone?: string;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-edge bg-panel p-4">
      <div className={`font-display text-3xl tracking-tight ${tone}`}>{value}</div>
      <div className="mt-1 text-sm text-sub">{label}</div>
      {hint ? <div className="mt-1 text-xs text-faint">{hint}</div> : null}
    </div>
  );
}

/** -1..1 rendered as a needle on a track, because the number alone means little. */
export function ScoreMeter({ compound }: { compound: number }) {
  const position = ((compound + 1) / 2) * 100;
  return (
    <div className="w-full">
      <div className="relative h-2 w-full rounded-full bg-gradient-to-r from-bad/50 via-edge2 to-good/50">
        <span
          className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-panel bg-ink"
          style={{ left: `${position}%` }}
        />
      </div>
      <div className="mt-1 flex justify-between font-mono text-[10px] text-faint">
        <span>-1.0</span>
        <span>0</span>
        <span>+1.0</span>
      </div>
    </div>
  );
}
