"use client";

import type { Crawl } from "./tracked";

export function CrawlProgress({ crawl }: { crawl: Crawl }) {
  const { status, running, stopping } = crawl;
  if (!running) return null;

  const fetched = status?.fetched ?? 0;
  const queued = status?.queued ?? 0;
  const skipped = status?.skipped ?? 0;
  const discovered = status?.discovered ?? 0;
  const total = fetched + queued;
  const share = total > 0 ? Math.min(99, Math.round((fetched / total) * 100)) : null;

  const scheduled = status?.trigger === "schedule";

  const stage = stopping
    ? "Stopping — the pages already read are kept"
    : status?.phase === "links"
      ? "Following links the sitemap did not list"
      : status?.phase === "sitemap"
        ? "Reading the pages the sitemap lists"
        : "Reading the sitemap and robots.txt";

  const aside = [
    scheduled && "started on its daily schedule",
    queued > 0 && `${queued} still queued`,
    discovered > fetched && `${discovered} found so far`,
    skipped > 0 && `${skipped} still fresh, left alone`,
  ].filter(Boolean) as string[];

  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1 text-xs">
        <span className="text-ink">
          {stage} · {fetched} page{fetched === 1 ? "" : "s"} read
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
