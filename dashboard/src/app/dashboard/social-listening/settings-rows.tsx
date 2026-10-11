"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import type { SocialListeningConfig, SocialListeningStrictness } from "@/lib/types";
import { AGE_PICKS, STRICTNESS } from "./lib";

const MAX_DAYS = 3650;

export function SettingsRows({
  config,
  onSave,
}: {
  config: SocialListeningConfig | null;
  onSave: (body: Record<string, unknown>) => void;
}) {
  const [days, setDays] = useState(String(config?.maxAgeDays ?? 365));
  const [error, setError] = useState<string | null>(null);

  const saveDays = (raw: string) => {
    const n = Math.round(Number(raw));
    if (!Number.isFinite(n) || n < 1 || n > MAX_DAYS) {
      setError(`Enter a number of days between 1 and ${MAX_DAYS}.`);
      return;
    }
    setError(null);
    setDays(String(n));
    if (n !== config?.maxAgeDays) onSave({ maxAgeDays: n });
  };

  const strictness = config?.strictness ?? "balanced";

  return (
    <>
      <div className="flex items-start gap-3">
        <label htmlFor="sl-max-age" className="w-24 shrink-0 pt-1.5 text-[13px] text-sub">
          Posts from
        </label>
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
          {AGE_PICKS.map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => saveDays(String(n))}
              className={cn(
                "cursor-pointer rounded-full border px-3 py-1 text-[13px] tabular-nums transition-colors",
                config?.maxAgeDays === n
                  ? "border-accent/30 bg-accent-soft text-accent"
                  : "border-edge2 text-sub hover:text-ink",
              )}
            >
              Last {n} days
            </button>
          ))}
          <span className="inline-flex items-center gap-1.5 text-[13px] text-sub">
            or last
            <input
              id="sl-max-age"
              type="number"
              min={1}
              max={MAX_DAYS}
              value={days}
              onChange={(e) => setDays(e.target.value)}
              onBlur={(e) => saveDays(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && saveDays((e.target as HTMLInputElement).value)}
              className="h-8 w-20 rounded-lg border border-edge2 bg-panel px-2.5 text-[13px] tabular-nums text-ink focus:border-accent focus:outline-none"
            />
            days
          </span>
          {error && <span className="text-xs text-bad">{error}</span>}
        </div>
      </div>

      <div className="flex items-start gap-3">
        <span className="w-24 shrink-0 pt-1.5 text-[13px] text-sub">How strict</span>
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-3">
          <div className="inline-flex gap-0.5 rounded-lg border border-edge2 bg-panel2 p-[3px]">
            {STRICTNESS.map((s) => (
              <button
                key={s.id}
                type="button"
                aria-pressed={s.id === strictness}
                onClick={() => s.id !== strictness && onSave({ strictness: s.id as SocialListeningStrictness })}
                className={cn(
                  "cursor-pointer rounded-md px-3.5 py-1 text-[13px] transition-colors",
                  s.id === strictness
                    ? "bg-panel font-medium text-ink shadow-[0_1px_2px_#1f2d3d14]"
                    : "text-sub hover:text-ink",
                )}
              >
                {s.label}
              </button>
            ))}
          </div>
          <span className="text-xs text-sub">Strict shows fewer posts, each a closer fit to what you wrote.</span>
        </div>
      </div>
    </>
  );
}
