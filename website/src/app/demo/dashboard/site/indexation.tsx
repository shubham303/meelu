"use client";

import { useEffect, useRef, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { Button, Card } from "@demo/components/ui";

interface IndexCheckBridge {
  indexCheck?: (payload: { siteId: string | null }) => Promise<{
    started?: boolean;
    total?: number;
    inspected?: number;
    error?: string;
  }>;
  onCrawlEvent?: (
    cb: (m: { event: string; data: Record<string, unknown> }) => void,
  ) => () => void;
}

function bridge(): IndexCheckBridge | undefined {
  if (typeof window === "undefined") return undefined;
  return (window as Window & { meeluAgent?: IndexCheckBridge }).meeluAgent;
}

function useIndexCheck(siteId: string | null, onSettled: () => void) {
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<{ inspected: number; total: number } | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const settled = useRef(onSettled);
  useEffect(() => {
    settled.current = onSettled;
  }, [onSettled]);

  useEffect(() => {
    const off = bridge()?.onCrawlEvent?.((m) => {
      if (m.event === "index:progress") {
        setProgress({
          inspected: Number(m.data.inspected) || 0,
          total: Number(m.data.total) || 0,
        });
      }
      if (m.event === "index:done") {
        setRunning(false);
        setProgress(null);
        setNote(
          m.data.ok === true
            ? `Checked ${m.data.inspected ?? 0} page(s).${m.data.note ? ` ${m.data.note}` : ""}`
            : String(m.data.error ?? "The index check failed."),
        );
        settled.current();
      }
    });
    return off;
  }, []);

  const start = async () => {
    setNote(null);
    const res = await bridge()?.indexCheck?.({ siteId });
    if (res?.error) setNote(res.error);
    else if (res?.started) setRunning(true);
    else setNote("Every page already has an index state.");
  };

  return { canRun: !!bridge()?.indexCheck, running, progress, note, start };
}

const BANDS: { key: string; label: string; className: string }[] = [
  { key: "indexed", label: "Indexed", className: "bg-good" },
  { key: "discovered", label: "Discovered, not crawled", className: "bg-faint" },
  { key: "crawled-not-indexed", label: "Crawled, not indexed", className: "bg-warn" },
  { key: "excluded", label: "Excluded", className: "bg-edge2" },
  { key: "blocked", label: "Blocked", className: "bg-bad" },
  { key: "unknown-to-google", label: "Unknown to Google", className: "bg-sub" },
  { key: "unknown", label: "Unknown", className: "bg-edge" },
  { key: "unchecked", label: "Not checked yet", className: "bg-panel2" },
];

export interface GooglePrefers {
  url: string;
  googleCanonical: string;
  coverageState: string | null;
}

function host(url: string): string {
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}

export function IndexationSection({
  siteId,
  counts,
  neverChecked,
  googlePrefers,
  verdict,
  onChanged,
}: {
  siteId: string | null;
  counts: Record<string, number>;
  neverChecked: number;
  googlePrefers: GooglePrefers[];
  verdict: string | null;
  onChanged: () => void;
}) {
  const check = useIndexCheck(siteId, onChanged);
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  if (total === 0) return null;
  return (
    <Card>
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="font-display text-lg text-ink">Indexation</h2>
        <div className="flex items-center gap-3">
          <span className="text-xs text-faint">
            {neverChecked > 0
              ? `${neverChecked} of ${total} pages not inspected yet`
              : `Search Console's verdict on ${total} crawled page${total === 1 ? "" : "s"}`}
          </span>
          {check.canRun && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => void check.start()}
              disabled={check.running}
            >
              {check.running
                ? check.progress
                  ? `Checking ${check.progress.inspected} of ${check.progress.total}…`
                  : "Checking…"
                : "Check index status"}
            </Button>
          )}
        </div>
      </div>
      <div className="flex h-3.5 overflow-hidden rounded-full border border-edge">
        {BANDS.filter((b) => (counts[b.key] ?? 0) > 0).map((b) => (
          <span
            key={b.key}
            className={b.className}
            style={{ width: `${((counts[b.key] ?? 0) / total) * 100}%` }}
            title={`${b.label}: ${counts[b.key]}`}
          />
        ))}
      </div>
      <div className="mt-2.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-sub">
        {BANDS.filter((b) => (counts[b.key] ?? 0) > 0).map((b) => (
          <span key={b.key} className="inline-flex items-center gap-1.5">
            <span className={`h-2 w-2 rounded-full ${b.className}`} />
            {b.label} {counts[b.key]}
          </span>
        ))}
      </div>
      <p className="mt-2 text-xs text-faint">
        Only pages this crawl read are inspected. Search Console has no API that lists everything
        Google holds, so URLs from an older version of the site — ones nothing links to any more —
        will not appear here even while Google still has them indexed.
      </p>
      {googlePrefers.length > 0 && (
        <div className="mt-3 rounded-lg border border-edge bg-panel2 p-3">
          <p className="text-xs font-medium text-ink">
            Google indexed a different URL for {googlePrefers.length} page
            {googlePrefers.length === 1 ? "" : "s"}
          </p>
          <p className="mt-1 text-xs text-sub">
            Google picked its own canonical instead of the address the crawl read. When the two are
            on different hosts, the site is being indexed under an address you are not maintaining.
          </p>
          <div className="mt-2 space-y-1">
            {googlePrefers.map((p) => (
              <div key={p.url} className="text-xs">
                <span className="text-sub">{p.url}</span>
                <span className="text-faint"> → </span>
                <span className={host(p.url) === host(p.googleCanonical) ? "text-sub" : "text-bad"}>
                  {p.googleCanonical}
                </span>
                {p.coverageState && <span className="text-faint"> · {p.coverageState}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
      {check.note && <p className="mt-2.5 text-xs text-sub">{check.note}</p>}
      {verdict && (
        <div className="mt-3 flex gap-2 rounded-lg border border-warn/40 bg-warn/5 p-3 text-sm text-ink">
          <AlertTriangle className="h-4 w-4 shrink-0 text-warn" />
          <span>{verdict}</span>
        </div>
      )}
    </Card>
  );
}
