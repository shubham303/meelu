import { cn } from "@/lib/utils";

export function Logo({ size = 22, withWordmark = true, className }: { size?: number; withWordmark?: boolean; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden>
        <path
          d="M12 2c1.2 3.2 2 4.6 4.4 5.4C19 8.2 21 8.6 22 12c-1 3.4-3 3.8-5.6 4.6C14 17.4 13.2 18.8 12 22c-1.2-3.2-2-4.6-4.4-5.4C5 15.8 3 15.4 2 12c1-3.4 3-3.8 5.6-4.6C10 6.6 10.8 5.2 12 2Z"
          fill="var(--color-accent)"
        />
        <circle cx="12" cy="12" r="2.6" fill="var(--color-panel)" />
      </svg>
      {withWordmark && <span className="font-display text-lg text-ink tracking-tight">Meelu</span>}
    </span>
  );
}
