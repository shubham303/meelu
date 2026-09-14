"use client";

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";
import { api } from "@/lib/use-api";

interface AnalysisBridge {
  analyzeSite?: (payload: { siteId: string | null }) => Promise<{
    jobId?: string | null;
    started?: boolean;
    reason?: string;
    error?: string;
  }>;
  stopAnalysis?: (jobId: string) => Promise<{ stopping?: boolean; error?: string }>;
  onAnalysisEvent?: (
    cb: (m: { event: string; data: Record<string, unknown> }) => void,
  ) => () => void;
}

function bridge(): AnalysisBridge | undefined {
  if (typeof window === "undefined") return undefined;
  return (window as Window & { meeluAgent?: AnalysisBridge }).meeluAgent;
}

const subscribeToBridge = () => () => {};

function useCanAnalyse(): boolean {
  return useSyncExternalStore(
    subscribeToBridge,
    () => !!bridge()?.analyzeSite,
    () => false,
  );
}

interface AnalysisView {
  jobId: string | null;
  active: boolean;
  total: number;
  processed: number;
  skippedUnchanged: number;
  skippedSimilar: number;
  failed: number;
  analyzedPages: number;
  eligiblePages: number;
}

const IDLE: AnalysisView = {
  jobId: null,
  active: false,
  total: 0,
  processed: 0,
  skippedUnchanged: 0,
  skippedSimilar: 0,
  failed: 0,
  analyzedPages: 0,
  eligiblePages: 0,
};

export function useAnalysis(siteId: string | null) {
  const [status, setStatus] = useState<AnalysisView | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [stopping, setStopping] = useState(false);

  const running = status?.active === true;
  const canAnalyse = useCanAnalyse();

  const poll = useCallback(async () => {
    if (!siteId) return;
    try {
      const res = await api<{ status: AnalysisView }>("/api/v1/site/analysis-jobs");
      setStatus(res.status);
      return res.status;
    } catch {
      return undefined;
    }
  }, [siteId]);

  useEffect(() => {
    void poll();
  }, [poll]);

  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => void poll(), 5000);
    return () => clearInterval(id);
  }, [running, poll]);

  useEffect(() => {
    if (!siteId) return;
    const off = bridge()?.onAnalysisEvent?.((m) => {
      const d = m.data as {
        siteId?: string;
        jobId?: string;
        total?: number;
        processed?: number;
        skippedUnchanged?: number;
        skippedSimilar?: number;
        failed?: number;
        ok?: boolean;
        stopped?: boolean;
        error?: string;
      };
      if (d.siteId !== siteId) return;

      if (m.event === "analysis:started" || m.event === "analysis:progress") {
        setStatus((s) => ({
          ...(s ?? IDLE),
          active: true,
          jobId: d.jobId ?? s?.jobId ?? null,
          total: d.total ?? s?.total ?? 0,
          processed: d.processed ?? s?.processed ?? 0,
          skippedUnchanged: d.skippedUnchanged ?? s?.skippedUnchanged ?? 0,
          skippedSimilar: d.skippedSimilar ?? s?.skippedSimilar ?? 0,
          failed: d.failed ?? s?.failed ?? 0,
        }));
      }
      if (m.event === "analysis:done") {
        setStopping(false);
        setNote(
          d.ok
            ? `${d.stopped ? "Stopped after analysing" : "Analysed"} ${d.processed ?? 0} page(s)` +
                ((d.skippedUnchanged ?? 0) + (d.skippedSimilar ?? 0) > 0
                  ? `; ${(d.skippedUnchanged ?? 0) + (d.skippedSimilar ?? 0)} unchanged, left alone.`
                  : ".") +
                (d.failed ? ` ${d.failed} failed.` : "")
            : (d.error ?? "The analysis failed."),
        );
        setStatus((s) => (s ? { ...s, active: false } : s));
        void poll();
      }
    });
    return off;
  }, [poll, siteId]);

  const start = useCallback(async () => {
    setNote(null);
    const run = bridge()?.analyzeSite;
    if (!run) {
      setNote("Analysis happens in the Meelu app — it runs on your own machine.");
      return false;
    }
    const res = await run({ siteId });
    if (res.error || res.started === false) {
      setNote(res.error ?? res.reason ?? "An analysis is already running.");
      return false;
    }
    setStatus((s) => ({ ...(s ?? IDLE), active: true, jobId: res.jobId ?? null }));
    return true;
  }, [siteId]);

  const jobId = status?.jobId ?? null;
  const stop = useCallback(async () => {
    if (!jobId) return;
    setStopping(true);
    try {
      await bridge()?.stopAnalysis?.(jobId);
      await api(`/api/v1/site/analysis-jobs/${jobId}`, {
        method: "PATCH",
        body: { status: "cancelling", reason: "stopped by the user" },
      });
      setNote("Stopping — the pages already analysed are kept.");
    } catch (e) {
      setStopping(false);
      setNote(e instanceof Error ? e.message : "Could not stop the analysis.");
    }
  }, [jobId]);

  return { status, note, running, stopping, canAnalyse, start, stop };
}

export type Analysis = ReturnType<typeof useAnalysis>;