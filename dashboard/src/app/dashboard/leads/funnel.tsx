import { Fragment } from "react";
import { cn } from "@/lib/utils";

export function Funnel({
  segments,
}: {
  segments: Array<{ label: string; value: number; tone?: "muted" | "plain" | "good" }>;
}) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {segments.map((s, i) => (
        <Fragment key={s.label}>
          {i > 0 && <span className="text-faint text-xs">→</span>}
          <div
            className={cn(
              "flex flex-col items-center rounded-xl border px-4 py-2 min-w-[72px]",
              s.tone === "good"
                ? "border-good/30 bg-good/10 text-good"
                : "border-edge bg-panel2 text-ink",
              s.tone === "muted" && "opacity-65",
            )}
          >
            <span className="font-display text-lg leading-tight">{s.value}</span>
            <span className="text-[11px] text-current/80">{s.label}</span>
          </div>
        </Fragment>
      ))}
    </div>
  );
}
