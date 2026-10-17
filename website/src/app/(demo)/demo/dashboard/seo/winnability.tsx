import { cn } from "@demo/lib/utils";

export function winnabilityTone(score: number | undefined): string {
  if (score === undefined) return "bg-edge2";
  if (score >= 60) return "bg-good";
  if (score >= 30) return "bg-warn";
  return "bg-faint";
}

export function WinnabilityBar({
  score,
  poisoned = false,
}: {
  score: number | undefined;
  poisoned?: boolean;
}) {
  if (poisoned)
    return <span className="text-xs text-warn">fake results</span>;
  if (score === undefined)
    return <span className="text-xs text-faint">not scored</span>;
  return (
    <div className="flex items-center gap-2.5">
      <div className="h-2 w-24 overflow-hidden rounded-full bg-panel2">
        <div
          className={cn("h-2 rounded-full", winnabilityTone(score))}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="min-w-7 text-sm font-semibold tabular-nums text-ink">
        {Math.round(score)}
      </span>
    </div>
  );
}

export function percent(value: number | undefined): string {
  return value === undefined ? "—" : `${Math.round(value * 100)}%`;
}

export function position(value: number | undefined): string {
  return value === undefined ? "—" : `#${value}`;
}
