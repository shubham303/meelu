"use client";

import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";
import { api } from "@demo/lib/use-api";
import type { SiteRenderDevice, SiteRenderJobStatus, SiteRenderScope } from "@demo/lib/types";

interface RenderBridge {
  renderSite?: (payload: {
    siteId: string | null;
    device: SiteRenderDevice;
    scope?: SiteRenderScope;
    limit?: number;
    url?: string;
  }) => Promise<{ jobId?: string | null; started?: boolean; reason?: string; error?: string }>;
  stopRender?: (jobId: string) => Promise<{ stopping?: boolean; error?: string }>;
  onRenderEvent?: (
    cb: (m: { event: string; data: Record<string, unknown> }) => void,
  ) => () => void;
}

function bridge(): RenderBridge | undefined {
  if (typeof window === "undefined") return undefined;
  return (window as Window & { meeluAgent?: RenderBridge }).meeluAgent;
}

const subscribeToBridge = () => () => {};

export interface RenderView {
  jobId: string | null;
  device: SiteRenderDevice;
  state: string;
  active: boolean;
  scope: SiteRenderScope | null;
  total: number;
  rendered: number;
  skipped: number;
  failed: number;
  current: string | null;
  error: string | null;
  stopReason: string | null;
  finishedAt: string | null;
  lastRenderedAt: string | null;
  renderedPages: number;
  eligiblePages: number;
  pendingPages: number;
}

function idle(device: SiteRenderDevice): RenderView {
  return {
    jobId: null,
    device,
    state: "idle",
    active: false,
    scope: null,
    total: 0,
    rendered: 0,
    skipped: 0,
    failed: 0,
    current: null,
    error: null,
    stopReason: null,
    finishedAt: null,
    lastRenderedAt: null,
    renderedPages: 0,
    eligiblePages: 0,
    pendingPages: 0,
  };
}

function fromApi(
  s: SiteRenderJobStatus,
  prev: RenderView | null,
  device: SiteRenderDevice,
): RenderView {
  const sameJob = prev?.jobId === (s.jobId ?? null);
  return {
    ...idle(device),
    jobId: s.jobId ?? null,
    state: s.state,
    active: s.active,
    scope: s.scope ?? null,
    total: s.total ?? 0,
    rendered: s.rendered ?? 0,
    skipped: sameJob ? (prev?.skipped ?? 0) : 0,
    failed: s.failed ?? 0,
    current: s.active && sameJob ? (prev?.current ?? null) : null,
    error: s.error ?? null,
    stopReason: s.stopReason ?? null,
    finishedAt: s.finishedAt ?? null,
    lastRenderedAt: s.lastRenderedAt ?? null,
    renderedPages: s.renderedPages,
    eligiblePages: s.eligiblePages,
    pendingPages: s.pendingPages ?? 0,
  };
}

export function useRender(
  siteId: string | null,
  device: SiteRenderDevice,
  onSettled: () => void,
) {
  const [status, setStatus] = useState<RenderView | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [stopping, setStopping] = useState(false);
  const settled = useRef(onSettled);
  useEffect(() => {
    settled.current = onSettled;
  }, [onSettled]);

  const canRender = useSyncExternalStore(
    subscribeToBridge,
    () => !!bridge()?.renderSite,
    () => false,
  );

  const poll = useCallback(async () => {
    if (!siteId) return null;
    try {
      const res = await api<{ status: SiteRenderJobStatus }>(
        `/api/v1/site/render-jobs?device=${device}`,
      );
      let next: RenderView | null = null;
      setStatus((prev) => {
        next = fromApi(res.status, prev, device);
        return next;
      });
      return next as RenderView | null;
    } catch {
      return null;
    }
  }, [siteId, device]);

  const running = status?.active ?? false;

  useEffect(() => {
    const id = setTimeout(() => void poll(), 0);
    return () => clearTimeout(id);
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
    }, 5000);
    return () => clearInterval(id);
  }, [running, poll]);

  useEffect(() => {
    if (!siteId) return;
    const off = bridge()?.onRenderEvent?.((m) => {
      const d = m.data as Partial<RenderView> & {
        siteId?: string;
        device?: string;
        ok?: boolean;
        stopped?: boolean;
        error?: string;
      };
      if (d.siteId !== siteId || d.device !== device) return;
      if (m.event === "render:started" || m.event === "render:progress") {
        setStatus((s) => ({
          ...(s ?? idle(device)),
          jobId: d.jobId ?? s?.jobId ?? null,
          state: "running",
          active: true,
          total: d.total ?? s?.total ?? 0,
          rendered: d.rendered ?? s?.rendered ?? 0,
          skipped: d.skipped ?? s?.skipped ?? 0,
          failed: d.failed ?? s?.failed ?? 0,
          current: d.current ?? null,
        }));
      }
      if (m.event === "render:done") {
        setStopping(false);
        setStatus((s) => (s ? { ...s, active: false, current: null } : s));
        const verb = d.stopped ? "Stopped after rendering" : "Rendered";
        const skipped = d.skipped ? `, ${d.skipped} unchanged since last time` : "";
        const failed = d.failed ? `, ${d.failed} could not be rendered.` : ".";
        setNote(
          d.ok
            ? `${verb} ${d.rendered ?? 0} of ${d.total ?? 0} page(s)${skipped}${failed}`
            : (d.error ?? "The render failed."),
        );
        void poll();
        settled.current();
      }
    });
    return off;
  }, [poll, siteId, device]);

  const start = useCallback(
    async (opts: { scope?: SiteRenderScope; limit?: number; url?: string } = {}) => {
      setNote(null);
      const run = bridge()?.renderSite;
      if (!run) {
        setNote("Rendering happens in the Meelu app — it loads each page in a real browser on your machine.");
        return false;
      }
      const res = await run({ siteId, device, ...opts });
      if (res.error || res.started === false) {
        setNote(res.error ?? res.reason ?? "A render is already running.");
        return false;
      }
      setStatus((s) => ({
        ...(s ?? idle(device)),
        active: true,
        jobId: res.jobId ?? null,
        state: "running",
        scope: opts.scope ?? "sample",
        total: 0,
        rendered: 0,
        skipped: 0,
        failed: 0,
        current: null,
        error: null,
        stopReason: null,
      }));
      return true;
    },
    [siteId, device],
  );

  const jobId = status?.jobId ?? null;
  const stop = useCallback(async () => {
    if (!jobId) return;
    setStopping(true);
    try {
      await bridge()?.stopRender?.(jobId);
      await api(`/api/v1/site/render-jobs/${jobId}`, {
        method: "PATCH",
        body: { status: "cancelling", reason: "stopped by the user" },
      });
      setNote("Stopping — the pages already rendered are kept.");
    } catch (e) {
      setStopping(false);
      setNote(e instanceof Error ? e.message : "Could not stop the render.");
    }
  }, [jobId]);

  return { status, note, running, stopping, canRender, device, start, stop, refresh: poll };
}

export type Render = ReturnType<typeof useRender>;
