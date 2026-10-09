"use client";

import { useEffect, useRef, useState } from "react";
import { Download } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/use-api";
import type { SocialListeningConfig, SocialListeningStrictness } from "@/lib/types";
import { AGE_PICKS, STRICTNESS } from "./lib";

const MAX_DAYS = 3650;

export function SettingsPopover({
  config,
  onClose,
  onSaved,
  onDownload,
  downloading,
}: {
  config: SocialListeningConfig | null;
  onClose: () => void;
  onSaved: () => Promise<void>;
  onDownload: () => void;
  downloading: boolean;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [days, setDays] = useState(String(config?.maxAgeDays ?? 365));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const away = (e: MouseEvent) => {
      const target = e.target as HTMLElement | null;
      if (ref.current && target && !ref.current.contains(target) && !target.closest("[data-settings-toggle]")) {
        onClose();
      }
    };
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("mousedown", away);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", away);
      document.removeEventListener("keydown", esc);
    };
  }, [onClose]);

  const save = async (body: Record<string, unknown>) => {
    setError(null);
    try {
      await api("/api/v1/social-listening/config", { method: "PUT", body });
      await onSaved();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The setting did not save.");
    }
  };

  const saveDays = (raw: string) => {
    const n = Math.round(Number(raw));
    if (!Number.isFinite(n) || n < 1 || n > MAX_DAYS) {
      setError(`Enter a number of days between 1 and ${MAX_DAYS}.`);
      return;
    }
    setDays(String(n));
    if (n !== config?.maxAgeDays) void save({ maxAgeDays: n });
  };

  const strictness = config?.strictness ?? "balanced";

  return (
    <div
      ref={ref}
      role="dialog"
      aria-label="Settings"
      className="absolute right-0 top-11 z-20 w-[340px] max-w-[calc(100vw-32px)] space-y-4 rounded-2xl border border-edge2 bg-panel p-4 shadow-[0_12px_32px_#1f2d3d24]"
    >
      <div className="space-y-2">
        <label htmlFor="sl-max-age" className="block text-[13px] font-medium text-ink">
          Ignore posts older than
        </label>
        <div className="flex items-center gap-2">
          <input
            id="sl-max-age"
            type="number"
            min={1}
            max={MAX_DAYS}
            value={days}
            onChange={(e) => setDays(e.target.value)}
            onBlur={(e) => saveDays(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && saveDays((e.target as HTMLInputElement).value)}
            className="h-9 w-24 rounded-lg border border-edge2 bg-panel px-2.5 text-sm tabular-nums text-ink focus:border-accent focus:outline-none"
          />
          <span className="text-[13px] text-sub">days</span>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {AGE_PICKS.map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => saveDays(String(n))}
              className={cn(
                "cursor-pointer rounded-full border px-2.5 py-0.5 text-[12.5px] tabular-nums transition-colors",
                config?.maxAgeDays === n
                  ? "border-accent/40 bg-accent-soft text-accent"
                  : "border-edge2 text-sub hover:text-ink",
              )}
            >
              {n}
            </button>
          ))}
        </div>
        <p className="text-xs text-sub">Type any number of days, or pick a common one.</p>
      </div>

      <div className="space-y-2">
        <p className="text-[13px] font-medium text-ink">How strict</p>
        <div className="flex gap-0.5 rounded-lg border border-edge2 bg-panel2 p-[3px]">
          {STRICTNESS.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => s.id !== strictness && void save({ strictness: s.id as SocialListeningStrictness })}
              className={cn(
                "flex-1 cursor-pointer rounded-md py-1 text-[13px] transition-colors",
                s.id === strictness
                  ? "bg-panel font-medium text-ink shadow-[0_1px_2px_#1f2d3d14]"
                  : "text-sub hover:text-ink",
              )}
            >
              {s.label}
            </button>
          ))}
        </div>
        <p className="text-xs text-sub">Strict shows fewer posts, each a closer fit to what you wrote.</p>
      </div>

      {error && <p className="text-xs text-bad">{error}</p>}

      <div className="h-px bg-edge" />
      <button
        type="button"
        onClick={onDownload}
        disabled={downloading}
        className="inline-flex cursor-pointer items-center gap-1.5 text-[13px] text-accent hover:underline disabled:opacity-60"
      >
        <Download size={14} /> {downloading ? "Building the CSV…" : "Download all posts as CSV"}
      </button>
    </div>
  );
}
