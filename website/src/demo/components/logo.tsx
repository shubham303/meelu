import { cn } from "@demo/lib/utils";

// Mirrors @/components/logo — the demo app is a self-contained tree with its
// own alias, so the brand mark is duplicated rather than imported across it.
export function Logo({ size = 22, withWordmark = true, className }: { size?: number; withWordmark?: boolean; className?: string }) {
  const small = size < 32;
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <svg
        width={Math.round(size * (small ? 41.25 / 29 : 38 / 26))}
        height={size}
        viewBox={small ? "3.25 9.5 41.25 29" : "5 11 38 26"}
        fill="none"
        aria-hidden
      >
        <circle cx="30" cy="24" r={small ? 14.5 : 13} fill="var(--color-accent)" />
        <circle
          cx={small ? 17 : 18}
          cy="24"
          r="11"
          fill="none"
          stroke="var(--color-ink)"
          strokeWidth={small ? 5.5 : 4}
        />
      </svg>
      {withWordmark && <span className="font-display text-lg font-light text-ink tracking-tight">meelu</span>}
    </span>
  );
}
