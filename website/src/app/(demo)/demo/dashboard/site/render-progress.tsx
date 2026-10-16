"use client";

import type { Render } from "./tracked-render";

export function RenderProgress({ render }: { render: Render }) {
  const { status, running, stopping } = render;
  if (!running) return null;

  const total = status?.total ?? 0;
  const rendered = status?.rendered ?? 0;
  const skipped = status?.skipped ?? 0;
  const failed = status?.failed ?? 0;
  const done = rendered + skipped + failed;
  const share = total > 0 ? Math.min(99, Math.round((done / total) * 100)) : null;
  const device = status?.device === "mobile" ? "phone" : "desktop";

  const stage = stopping
    ? "Stopping — the pages already rendered are kept"
    : status?.current
      ? `Rendering ${status.current}`
      : `Starting the ${device} browser`;

  const aside = [
    skipped > 0 && `${skipped} unchanged since last time, left alone`,
    failed > 0 && `${failed} failed`,
  ].filter(Boolean) as string[];

  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 text-xs">
        <span className="min-w-0 truncate text-ink">
          {stage} · {done} of {total} page{total === 1 ? "" : "s"}
          {share !== null && <span className="ml-1 tabular-nums text-sub">{share}%</span>}
        </span>
        {aside.length > 0 && <span className="text-sub">{aside.join(" · ")}</span>}
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-panel2">
        {share === null ? (
          <div className="h-full w-1/5 rounded-full bg-accent animate-crawl-sweep" />
        ) : (
          <div
            className="h-full rounded-full bg-accent transition-[width] duration-500 ease-out"
            style={{ width: `${Math.max(share, 2)}%` }}
          />
        )}
      </div>
    </div>
  );
}
