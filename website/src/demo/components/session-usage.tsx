"use client";

import { useSyncExternalStore } from "react";
import {
  subscribeToUsage,
  usageServerSnapshot,
  usageSnapshot,
} from "@demo/lib/session-usage";

function short(n: number): string {
  if (n < 1000) return String(n);
  if (n < 1_000_000) return `${(n / 1000).toFixed(n < 10_000 ? 1 : 0)}k`;
  return `${(n / 1_000_000).toFixed(2)}M`;
}

export function SessionUsage({ compact = false }: { compact?: boolean }) {
  const usage = useSyncExternalStore(
    subscribeToUsage,
    usageSnapshot,
    usageServerSnapshot,
  );

  if (!usage || usage.tokens === 0) return null;

  const since = new Date(usage.startedAt).toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit",
  });

  const title =
          `${usage.tokens.toLocaleString()} tokens across ${usage.turns} agent turn` +
          `${usage.turns === 1 ? "" : "s"} — ${usage.inputTokens.toLocaleString()} in ` +
          `(incl. cache), ${usage.outputTokens.toLocaleString()} out. ` +
          `$${usage.costUsd.toFixed(2)} so far. ` +
    `Counting since ${since}; resets when you quit Meelu.`;

  if (compact) {
    return (
      <p
        aria-live="polite"
        title={title}
        className={[
          "select-none py-2 text-center text-[10px] tabular-nums",
          usage.busy ? "text-accent" : "text-faint",
        ].join(" ")}
      >
        {short(usage.tokens)}
      </p>
    );
  }

  return (
    <p
      aria-live="polite"
      title={title}
      className={[
        "select-none px-3 pt-2 text-[11px] tabular-nums",
        usage.busy ? "text-accent" : "text-faint",
      ].join(" ")}
    >
      {usage.busy && (
        <span className="mr-1.5 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-current align-middle" />
      )}
      {short(usage.tokens)} tokens
      <span className="ml-1.5 opacity-60">${usage.costUsd.toFixed(2)}</span>
    </p>
  );
}
