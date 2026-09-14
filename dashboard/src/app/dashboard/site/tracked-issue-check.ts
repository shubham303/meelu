"use client";

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";

interface IssueCheckBridge {
  checkIssues?: (payload: { siteId: string | null }) => Promise<{
    started?: boolean;
    reason?: string;
    error?: string;
  }>;
  stopIssueCheck?: (siteId: string) => Promise<{ stopping?: boolean; error?: string }>;
  onIssueCheckEvent?: (
    cb: (m: { event: string; data: Record<string, unknown> }) => void,
  ) => () => void;
}

function bridge(): IssueCheckBridge | undefined {
  if (typeof window === "undefined") return undefined;
  return (window as Window & { meeluAgent?: IssueCheckBridge }).meeluAgent;
}

const subscribeToBridge = () => () => {};

export interface IssueCheckView {
  active: boolean;
  total: number;
  checked: number;
  kept: number;
  updated: number;
  deleted: number;
  failed: number;
}

const IDLE: IssueCheckView = {
  active: false,
  total: 0,
  checked: 0,
  kept: 0,
  updated: 0,
  deleted: 0,
  failed: 0,
};

export function useIssueCheck(siteId: string | null, onDone?: () => void) {
  const [status, setStatus] = useState<IssueCheckView>(IDLE);
  const [note, setNote] = useState<string | null>(null);
  const [stopping, setStopping] = useState(false);

  const canCheck = useSyncExternalStore(
    subscribeToBridge,
    () => !!bridge()?.checkIssues,
    () => false,
  );

  useEffect(() => {
    if (!siteId) return;
    const off = bridge()?.onIssueCheckEvent?.((m) => {
      const d = m.data as Partial<IssueCheckView> & {
        siteId?: string;
        ok?: boolean;
        stopped?: boolean;
        error?: string;
      };
      if (d.siteId !== siteId) return;
      if (m.event === "issue-check:started" || m.event === "issue-check:progress") {
        setStatus((s) => ({ ...s, ...d, active: true }));
      }
      if (m.event === "issue-check:done") {
        setStopping(false);
        setStatus((s) => ({ ...s, ...d, active: false }));
        setNote(
          d.ok
            ? `${d.stopped ? "Stopped after verifying" : "Verified"} ${d.checked ?? 0} of ${d.total ?? 0} finding(s): ` +
                `${d.kept ?? 0} kept, ${d.updated ?? 0} reworded, ${d.deleted ?? 0} dropped` +
                (d.failed ? `, ${d.failed} could not be checked.` : ".")
            : (d.error ?? "The verification failed."),
        );
        onDone?.();
      }
    });
    return off;
  }, [siteId, onDone]);

  const start = useCallback(async () => {
    setNote(null);
    const run = bridge()?.checkIssues;
    if (!run) return false;
    const res = await run({ siteId });
    if (res.error || res.started === false) {
      setNote(res.error ?? res.reason ?? "A verification is already running.");
      return false;
    }
    setStatus({ ...IDLE, active: true });
    return true;
  }, [siteId]);

  const stop = useCallback(async () => {
    if (!siteId) return;
    setStopping(true);
    await bridge()?.stopIssueCheck?.(siteId);
  }, [siteId]);

  return { status, note, running: status.active, stopping, canCheck, start, stop };
}

export type IssueCheck = ReturnType<typeof useIssueCheck>;
