"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export interface GaProperty {
  property: string;
  propertyId: string;
  name: string;
  kind: string | null;
}

export interface GaAccount {
  account: string;
  name: string;
  properties: GaProperty[];
}

interface TrafficBridge {
  trafficSync?: (payload: { siteId: string | null }) => Promise<{
    syncId?: string | null;
    started?: boolean;
    reason?: string;
    error?: string;
  }>;
  stopTrafficSync?: (syncId: string) => Promise<{ stopping?: boolean; error?: string }>;
  gaProperties?: () => Promise<{
    connected?: boolean;
    accounts?: GaAccount[];
    error?: string;
  }>;
  connectGa4?: () => Promise<Record<string, unknown> | { error: string }>;
  getConnectors?: () => Promise<Record<string, unknown> | { error: string }>;
  onCrawlEvent?: (
    cb: (m: { event: string; data: Record<string, unknown> }) => void,
  ) => () => void;
}

function bridge(): TrafficBridge | undefined {
  if (typeof window === "undefined") return undefined;
  return (window as Window & { meeluAgent?: TrafficBridge }).meeluAgent;
}

export interface TrafficSyncProgress {
  daysDone?: number;
  daysTotal?: number;
  rowsStored?: number;
  day?: string;
  report?: string;
}

export function useGaConnected() {
  const [connected, setConnected] = useState<boolean | null>(null);
  useEffect(() => {
    void bridge()
      ?.getConnectors?.()
      .then((res) => {
        if (res && !("error" in res)) setConnected("ga4" in res);
      });
  }, []);
  return { connected, markConnected: () => setConnected(true) };
}

export function useTrafficSync(
  siteId: string | null,
  onSettled: () => void,
  activeSyncId: string | null = null,
) {
  const [syncId, setSyncId] = useState<string | null>(null);
  const [progress, setProgress] = useState<TrafficSyncProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<GaAccount[] | null>(null);
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
      if (!m.event.startsWith("traffic:")) return;
      const eventSyncId = typeof m.data.syncId === "string" ? m.data.syncId : null;
      const eventSiteId = typeof m.data.siteId === "string" ? m.data.siteId : null;
      if (eventSiteId && siteId && eventSiteId !== siteId) {
        if (m.event === "traffic:done" && eventSyncId) {
          setEndedIds((prev) => new Set(prev).add(eventSyncId));
        }
        return;
      }
      if (m.event === "traffic:started") {
        setError(null);
        setCandidates(null);
        if (eventSyncId) setSyncId(eventSyncId);
        setProgress({ daysDone: 0, daysTotal: Number(m.data.daysTotal) || 0 });
      }
      if (m.event === "traffic:progress") {
        if (eventSyncId) setSyncId(eventSyncId);
        setProgress(m.data as unknown as TrafficSyncProgress);
      }
      if (m.event === "traffic:done") {
        if (eventSyncId) setEndedIds((prev) => new Set(prev).add(eventSyncId));
        setSyncId(null);
        setProgress(null);
        setStopping(false);
        if (m.data.ok !== true) {
          setError(typeof m.data.error === "string" ? m.data.error : "The sync failed.");
          if (m.data.needsProperty === true && Array.isArray(m.data.candidates)) {
            setCandidates(m.data.candidates as GaAccount[]);
          }
        }
        settled.current();
      }
    });
    return off;
  }, [siteId]);

  const start = useCallback(async () => {
    setError(null);
    const res = await bridge()?.trafficSync?.({ siteId });
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
    await bridge()?.stopTrafficSync?.(currentSyncId);
  }, [currentSyncId]);

  const canSync = !!bridge()?.trafficSync;

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
    connectGa4: () => bridge()?.connectGa4?.(),
    listProperties: () => bridge()?.gaProperties?.(),
  };
}
