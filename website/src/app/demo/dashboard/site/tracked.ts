"use client";

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { api, apiPaged } from "@demo/lib/use-api";

export interface CrawlBridge {
  crawlSite?: (payload: {
    siteId: string | null;
    freshDays?: number;
    sitemapUrls?: string[];
  }) => Promise<{
    jobId?: string | null;
    started?: boolean;
    reason?: string;
    error?: string;
  }>;
  stopCrawl?: (jobId: string) => Promise<{ stopping?: boolean; error?: string }>;
  onCrawlEvent?: (
    cb: (m: { event: string; data: Record<string, unknown> }) => void,
  ) => () => void;
}

function bridge(): CrawlBridge | undefined {
  if (typeof window === "undefined") return undefined;
  return (window as Window & { meeluAgent?: CrawlBridge }).meeluAgent;
}

const subscribeToBridge = () => () => {};

function useCanCrawl(): boolean {
  return useSyncExternalStore(
    subscribeToBridge,
    () => !!bridge()?.crawlSite,
    () => false,
  );
}

export type CrawlPhase = "sitemap" | "links" | null;

export interface CrawlView {
  jobId: string | null;
  state: string;
  active: boolean;
  trigger?: string | null;
  phase?: CrawlPhase;
  fetched: number;
  queued: number;
  skipped: number;
  discovered: number;
  error: string | null;
  stopReason: string | null;
  cutoffDays: number | null;
  lastCrawledAt: string | null;
  pages: number;
}

export type Crawl = ReturnType<typeof useCrawl>;

export function useCrawl(siteId: string | null, onSettled: () => void) {
  const [status, setStatus] = useState<CrawlView | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [stopping, setStopping] = useState(false);
  const [needsSitemap, setNeedsSitemap] = useState(false);
  const settled = useRef(onSettled);
  useEffect(() => {
    settled.current = onSettled;
  }, [onSettled]);

  const running = status?.active === true;
  const canCrawl = useCanCrawl();

  const poll = useCallback(async () => {
    if (!siteId) return;
    try {
      const res = await apiPaged<unknown, { status: CrawlView }>("/api/v1/site/crawl-jobs?page_size=1");
      setStatus(res.status);
      return res.status;
    } catch {
      return undefined;
    }
  }, [siteId]);

  const [shownFor, setShownFor] = useState(siteId);
  if (shownFor !== siteId) {
    setShownFor(siteId);
    setStatus(null);
    setNote(null);
    setStopping(false);
    setNeedsSitemap(false);
  }

  useEffect(() => {
    void poll();
  }, [poll]);

  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => {
      void poll().then((s) => {
        if (s && !s.active) {
          setStopping(false);
          settled.current();
        }
      });
    }, 4000);
    return () => clearInterval(id);
  }, [running, poll]);

  useEffect(() => {
    if (!siteId) return;
    const off = bridge()?.onCrawlEvent?.((m) => {
      const d = m.data as {
        siteId?: string;
        jobId?: string;
        phase?: CrawlPhase;
        fetched?: number;
        queued?: number;
        skipped?: number;
        seen?: number;
        ok?: boolean;
        error?: string;
        pagesStored?: number;
        needsSitemap?: boolean;
        unreachableHost?: boolean;
        stopped?: boolean;
      };
      if (d.siteId !== siteId) return;

      if (m.event === "crawl:started") {
        setStatus((s) => ({
          ...(s ?? IDLE),
          active: true,
          state: "running",
          phase: null,
          fetched: 0,
          queued: 0,
          skipped: 0,
          discovered: 0,
          error: null,
          jobId: d.jobId ?? null,
        }));
      }
      if (m.event === "crawl:progress") {
        setStatus((s) => ({
          ...(s ?? IDLE),
          active: true,
          state: "running",
          jobId: d.jobId ?? s?.jobId ?? null,
          phase: d.phase ?? s?.phase ?? null,
          fetched: d.fetched ?? s?.fetched ?? 0,
          queued: d.queued ?? s?.queued ?? 0,
          skipped: d.skipped ?? s?.skipped ?? 0,
          discovered: d.seen ?? s?.discovered ?? 0,
        }));
      }
      if (m.event === "crawl:done") {
        setStopping(false);
        setNeedsSitemap(d.needsSitemap === true);
        setNote(
          d.ok
            ? `${d.stopped ? "Stopped after reading" : "Read"} ${d.pagesStored ?? 0} page(s)` +
                (d.skipped ? `; ${d.skipped} were still fresh and were left alone.` : ".")
            : (d.error ?? "The crawl failed."),
        );
        setStatus((s) => (s ? { ...s, active: false, phase: null, state: "idle" } : s));
        void poll();
        settled.current();
      }
    });
    return off;
  }, [poll, siteId]);

  const start = useCallback(
    async (opts: { sitemapUrls?: string[]; freshDays?: number } = {}) => {
      setNote(null);
      setNeedsSitemap(false);
      const run = bridge()?.crawlSite;
      if (!run) {
        setNote("Crawling happens in the Meelu app — it reads the site from your own machine.");
        return false;
      }
      const res = await run({
        siteId,
        ...(opts.sitemapUrls?.length ? { sitemapUrls: opts.sitemapUrls } : {}),
        ...(opts.freshDays === undefined ? {} : { freshDays: opts.freshDays }),
      });
      if (res.error || res.started === false) {
        setNote(res.error ?? res.reason ?? "A crawl is already running.");
        return false;
      }
      setStatus((s) => ({
        ...IDLE,
        lastCrawledAt: s?.lastCrawledAt ?? null,
        pages: s?.pages ?? 0,
        active: true,
        jobId: res.jobId ?? null,
        state: "running",
      }));
      void poll();
      return true;
    },
    [siteId, poll],
  );

  const jobId = status?.jobId ?? null;
  const stop = useCallback(async () => {
    if (!jobId) return;
    setStopping(true);
    try {
      await bridge()?.stopCrawl?.(jobId);
      await api(`/api/v1/site/crawl-jobs/${jobId}`, {
        method: "PATCH",
        body: { status: "cancelling", reason: "stopped by the user" },
      });
      setNote("Stopping — the pages already fetched are kept.");
    } catch (e) {
      setStopping(false);
      setNote(e instanceof Error ? e.message : "Could not stop the crawl.");
    }
  }, [jobId]);

  return { status, note, running, stopping, canCrawl, needsSitemap, start, stop, refresh: poll };
}

const IDLE: CrawlView = {
  jobId: null,
  state: "idle",
  active: false,
  trigger: null,
  phase: null,
  fetched: 0,
  queued: 0,
  skipped: 0,
  discovered: 0,
  error: null,
  stopReason: null,
  cutoffDays: null,
  lastCrawledAt: null,
  pages: 0,
};
