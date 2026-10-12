"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface GscProperty {
  siteUrl: string;
  permissionLevel: string;
}

interface SearchBridge {
  searchSync?: (payload: { siteId: string | null }) => Promise<{
    syncId?: string | null;
    started?: boolean;
    reason?: string;
    error?: string;
  }>;
  stopSearchSync?: (syncId: string) => Promise<{ stopping?: boolean; error?: string }>;
  gscProperties?: (domain: string) => Promise<{
    connected?: boolean;
    properties?: GscProperty[];
    matching?: GscProperty[];
    error?: string;
  }>;
  connectGsc?: () => Promise<Record<string, unknown> | { error: string }>;
  getConnectors?: () => Promise<Record<string, unknown> | { error: string }>;
  inspectPageUrl?: (payload: { siteId: string | null; url: string }) => Promise<{
    inspection?: Record<string, unknown>;
    error?: string;
  }>;
  onCrawlEvent?: (
    cb: (m: { event: string; data: Record<string, unknown> }) => void,
  ) => () => void;
}

function bridge(): SearchBridge | undefined {
  if (typeof window === "undefined") return undefined;
  return (window as Window & { meeluAgent?: SearchBridge }).meeluAgent;
}

export interface SyncProgress {
  phase: "days" | "inspect";
  daysDone?: number;
  daysTotal?: number;
  rowsStored?: number;
  day?: string;
  pagesInspected?: number;
  pagesTotal?: number;
}

export function canInspectUrls(): boolean {
  return !!bridge()?.inspectPageUrl;
}

export function inspectPageUrl(siteId: string | null, url: string) {
  const fn = bridge()?.inspectPageUrl;
  if (!fn) return Promise.resolve({ error: "URL inspection runs in the Meelu app." });
  return fn({ siteId, url });
}

export function useGscConnected() {
  const [connected, setConnected] = useState<boolean | null>(null);
  useEffect(() => {
    void bridge()
      ?.getConnectors?.()
      .then((res) => {
        if (res && !("error" in res)) setConnected("gsc" in res);
      });
  }, []);
  return { connected, markConnected: () => setConnected(true) };
}

export function useSearchSync(
  siteId: string | null,
  onSettled: () => void,
  activeSyncId: string | null = null,
) {
  const [syncId, setSyncId] = useState<string | null>(null);
  const [progress, setProgress] = useState<SyncProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<GscProperty[] | null>(null);
  const [stopping, setStopping] = useState(false);
  const [endedIds, setEndedIds] = useState<ReadonlySet<string>>(new Set());
  const [shownSiteId, setShownSiteId] = useState(siteId);
  const settled = useRef(onSettled);
  useEffect(() => {
    settled.current = onSettled;
  }, [onSettled]);

  if (shownSiteId !== siteId) {
    setShownSiteId(siteId);
    setSyncId(null);
    setProgress(null);
    setError(null);
    setCandidates(null);
    setStopping(false);
  }

  useEffect(() => {
    const off = bridge()?.onCrawlEvent?.((m) => {
      if (!m.event.startsWith("search:")) return;
      const eventSyncId = typeof m.data.syncId === "string" ? m.data.syncId : null;
      const eventSiteId = typeof m.data.siteId === "string" ? m.data.siteId : null;
      if (eventSiteId && siteId && eventSiteId !== siteId) {
        if (m.event === "search:done" && eventSyncId) {
          setEndedIds((prev) => new Set(prev).add(eventSyncId));
        }
        return;
      }
      if (m.event === "search:started") {
        setError(null);
        setCandidates(null);
        if (eventSyncId) setSyncId(eventSyncId);
        setProgress({ phase: "days", daysDone: 0, daysTotal: Number(m.data.daysTotal) || 0 });
      }
      if (m.event === "search:progress") {
        if (eventSyncId) setSyncId(eventSyncId);
        setProgress(m.data as unknown as SyncProgress);
      }
      if (m.event === "search:done") {
        if (eventSyncId) setEndedIds((prev) => new Set(prev).add(eventSyncId));
        setSyncId(null);
        setProgress(null);
        setStopping(false);
        if (m.data.ok !== true) {
          setError(typeof m.data.error === "string" ? m.data.error : "The sync failed.");
          if (m.data.needsProperty === true && Array.isArray(m.data.candidates)) {
            setCandidates(m.data.candidates as GscProperty[]);
          }
        }
        settled.current();
      }
    });
    return off;
  }, [siteId]);

  const start = useCallback(async () => {
    setError(null);
    const res = await bridge()?.searchSync?.({ siteId });
    if (res?.error) setError(res.error);
    else if (res?.started === false && !res.syncId) {
      setError(res.reason ?? "A sync is already running.");
    } else if (res?.syncId) setSyncId(res.syncId);
  }, [siteId]);

  const adopted = activeSyncId && !endedIds.has(activeSyncId) ? activeSyncId : null;
  const currentSyncId = syncId ?? adopted;

  const stop = useCallback(async () => {
    if (!currentSyncId) return;
    setStopping(true);
    await bridge()?.stopSearchSync?.(currentSyncId);
  }, [currentSyncId]);

  const canSync = !!bridge()?.searchSync;

  return {
    canSync,
    running: currentSyncId !== null,
    progress,
    error,
    candidates,
    stopping,
    start,
    stop,
    clearCandidates: () => setCandidates(null),
    connectGsc: () => bridge()?.connectGsc?.(),
    listProperties: (domain: string) => bridge()?.gscProperties?.(domain),
  };
}
