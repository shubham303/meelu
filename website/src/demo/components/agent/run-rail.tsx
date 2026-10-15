"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import Link from "next/link";
import { AlertCircle, Check, ExternalLink, Loader2, Square, X } from "lucide-react";
import { Drawer } from "@demo/components/ui";
import { activeSiteId, GLOBAL } from "@demo/lib/current-site";
import { useCurrentSite } from "@demo/lib/use-api";
import { useIsApp } from "@demo/lib/use-app-mode";
import { cn } from "@demo/lib/utils";
import { agentEnabled, bridge, type AgentEvent, type AskLink } from "./bridge";
import { ChatMarkdown } from "./chat-markdown";
import { linkHref } from "./desk-scope";

export type RunStatus = "running" | "waiting" | "done" | "failed" | "stopped";

export interface RunUnit {
  done: number;
  total: number;
  noun: string;
}

export interface AgentRun {
  id: string;
  label: string;
  siteId: string | null;
  desk?: string;
  status: RunStatus;
  startedAt: number;
  unit?: RunUnit;
  onStop?: () => void;
  onOpen?: () => void;
  error?: string;
  answer?: { text: string; links: AskLink[] };
}

export interface PendingYes {
  id: string;
  kind: "send" | "publish" | "pr" | "spend" | "step" | "write";
  label: string;
  runId?: string;
  mode: "permission" | "local";
  requestId?: string;
  onAnswer?: (yes: boolean) => void | Promise<void>;
}

export interface AgentRunsApi {
  runs: AgentRun[];
  needsYes: PendingYes[];
  startRun: (init: {
    id?: string;
    label: string;
    siteId?: string | null;
    desk?: string;
    unit?: RunUnit;
    onStop?: () => void;
    onOpen?: () => void;
  }) => string;
  updateRun: (id: string, patch: Partial<Omit<AgentRun, "id">>) => void;
  endRun: (id: string, status?: RunStatus, error?: string, answer?: AgentRun["answer"]) => void;
  askYes: (y: Omit<PendingYes, "id"> & { id?: string }) => string;
  answerYes: (id: string, yes: boolean) => Promise<void>;
  dismiss: (id: string) => void;
}

const RunsContext = createContext<AgentRunsApi | null>(null);

export function useAgentRuns(): AgentRunsApi {
  const ctx = useContext(RunsContext);
  if (!ctx) throw new Error("useAgentRuns needs <AgentRunsProvider> in the dashboard layout");
  return ctx;
}

export function useAgentRunsOptional(): AgentRunsApi | null {
  return useContext(RunsContext);
}

const KEEP_FINISHED_MS = 20_000;

export function AgentRunsProvider({ children }: { children: ReactNode }) {
  const isApp = useIsApp();
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [needsYes, setNeedsYes] = useState<PendingYes[]>([]);

  const startRun = useCallback<AgentRunsApi["startRun"]>(
    (init) => {
      if (!agentEnabled()) return "";
      const id = init.id ?? crypto.randomUUID();
      setRuns((prev) => [
        ...prev.filter((r) => r.id !== id),
        {
          ...init,
          id,
          siteId: init.siteId === undefined ? activeSiteId() : init.siteId,
          status: "running",
          startedAt: Date.now(),
        },
      ]);
      return id;
    },
    [],
  );

  const updateRun = useCallback<AgentRunsApi["updateRun"]>((id, patch) => {
    setRuns((prev) => prev.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  }, []);

  const endRun = useCallback<AgentRunsApi["endRun"]>((id, status = "done", error, answer) => {
    setRuns((prev) => prev.map((r) => (r.id === id ? { ...r, status, error, answer } : r)));
    window.setTimeout(
      () => setRuns((prev) => prev.filter((r) => r.id !== id || r.status === "running")),
      KEEP_FINISHED_MS,
    );
  }, []);

  const askYes = useCallback<AgentRunsApi["askYes"]>((y) => {
    const id = y.id ?? crypto.randomUUID();
    setNeedsYes((prev) => [...prev.filter((p) => p.id !== id), { ...y, id }]);
    return id;
  }, []);

  const answerYes = useCallback<AgentRunsApi["answerYes"]>(async (id, yes) => {
    let target: PendingYes | undefined;
    setNeedsYes((prev) => {
      target = prev.find((p) => p.id === id);
      return prev.filter((p) => p.id !== id);
    });
    if (!target) return;
    const b = bridge();
    if (target.mode === "permission" && target.requestId) {
      await b?.respondPermission?.(target.requestId, yes ? "allow" : "deny");
    }
    await target.onAnswer?.(yes);
  }, []);

  const dismiss = useCallback<AgentRunsApi["dismiss"]>((id) => {
    setRuns((prev) => prev.filter((r) => r.id !== id));
    setNeedsYes((prev) => prev.filter((p) => p.id !== id));
  }, []);

  const runsRef = useRef<AgentRun[]>([]);
  useEffect(() => {
    runsRef.current = runs;
  }, [runs]);

  useEffect(() => {
    if (!isApp) return;
    const b = bridge();
    if (!b) return;
    return b.onEvent((m: AgentEvent) => {
      const unit = readUnit(m.data);
      if (unit) {
        setRuns((prev) =>
          prev.map((r) => (r.id === m.turnId ? { ...r, unit, status: "running" } : r)),
        );
      }
      if (
        m.event === "permission" &&
        typeof m.data.requestId === "string" &&
        runsRef.current.some((r) => r.id === m.turnId)
      ) {
        askYes({
          id: m.data.requestId,
          kind: guessKind(String(m.data.tool ?? "")),
          label: String(m.data.tool ?? "a write"),
          runId: m.turnId,
          mode: "permission",
          requestId: m.data.requestId,
        });
      }
      if (m.event === "done") {
        const ok = m.data.ok !== false;
        setRuns((prev) =>
          prev.map((r) =>
            r.id === m.turnId && r.status === "running"
              ? {
                  ...r,
                  status: ok ? "done" : "failed",
                  error: typeof m.data.error === "string" ? m.data.error : undefined,
                }
              : r,
          ),
        );
      }
    });
  }, [isApp, askYes]);

  const site = useCurrentSite();
  const here = site === GLOBAL ? null : site;
  const visibleRuns = useMemo(
    () => runs.filter((r) => r.siteId === null || r.siteId === here),
    [runs, here],
  );
  const visibleYes = useMemo(
    () =>
      needsYes.filter((y) => {
        if (!y.runId) return true;
        const run = runs.find((r) => r.id === y.runId);
        return !run || run.siteId === null || run.siteId === here;
      }),
    [needsYes, runs, here],
  );

  const api = useMemo<AgentRunsApi>(
    () => ({
      runs: visibleRuns,
      needsYes: visibleYes,
      startRun,
      updateRun,
      endRun,
      askYes,
      answerYes,
      dismiss,
    }),
    [visibleRuns, visibleYes, startRun, updateRun, endRun, askYes, answerYes, dismiss],
  );

  return <RunsContext.Provider value={api}>{children}</RunsContext.Provider>;
}

function readUnit(data: Record<string, unknown>): RunUnit | null {
  if (!data || typeof data !== "object") return null;
  const num = (v: unknown) => (typeof v === "number" && Number.isFinite(v) ? v : null);
  const done = num(data.done) ?? num(data.completed) ?? num(data.index) ?? num(data.page);
  const total = num(data.total) ?? num(data.count) ?? num(data.pages) ?? num(data.steps);
  if (done === null || total === null || total <= 0) return null;
  const noun = typeof data.noun === "string" ? data.noun : data.pages !== undefined ? "page" : "step";
  return { done, total, noun };
}

function guessKind(text: string): PendingYes["kind"] {
  const t = text.toLowerCase();
  if (/pull|pr\b|branch/.test(t)) return "pr";
  if (/send|mail|reply/.test(t)) return "send";
  if (/publish|schedule|post/.test(t)) return "publish";
  if (/spend|credit|budget/.test(t)) return "spend";
  if (/step/.test(t)) return "step";
  return "write";
}

const KIND_WORD: Record<PendingYes["kind"], string> = {
  send: "send",
  publish: "publish",
  pr: "PR",
  spend: "spend",
  step: "step",
  write: "write",
};

export function RunRail({
  className,
  onNavigate,
}: {
  className?: string;
  onNavigate?: () => void;
}) {
  const isApp = useIsApp();
  const ctx = useContext(RunsContext);
  const [openRun, setOpenRun] = useState<AgentRun | null>(null);

  useEffect(() => {
    if (isApp && !ctx && process.env.NODE_ENV !== "production") {
      console.warn(
        "[agent] <RunRail> rendered without <AgentRunsProvider>. Mount the provider in the " +
          "dashboard layout — a rail below the route forgets the run you navigated away from.",
      );
    }
  }, [isApp, ctx]);

  if (!isApp || !ctx) return null;
  const { runs, needsYes, answerYes, dismiss } = ctx;
  const live = runs.filter((r) => r.status === "running" || r.status === "waiting");
  const recent = runs.filter((r) => r.status !== "running" && r.status !== "waiting");
  if (live.length === 0 && recent.length === 0 && needsYes.length === 0 && !openRun) return null;

  return (
    <>
      <div className={cn("px-3 py-3 space-y-3", className)}>
        {live.map((r) => (
          <RunLine key={r.id} run={r} onNavigate={onNavigate} />
        ))}

        {recent.map((r) => (
          <div
            key={r.id}
            className="flex items-center gap-3 rounded-lg border border-edge bg-panel2/50 px-3 py-2.5"
          >
            <button
              type="button"
              onClick={() => {
                if (r.answer) {
                  onNavigate?.();
                  setOpenRun(r);
                } else {
                  dismiss(r.id);
                }
              }}
              className="flex min-w-0 flex-1 items-center gap-3 text-left cursor-pointer"
            >
              {r.status === "failed" ? (
                <AlertCircle size={14} className="text-bad shrink-0" />
              ) : (
                <Check size={14} className="text-good shrink-0" />
              )}
              <span className="min-w-0 flex-1 truncate text-sm text-ink">{r.label}</span>
              <span className="text-[11px] text-sub shrink-0">
                {r.status === "failed" ? (r.error ?? "failed") : "done"}
              </span>
            </button>
            <button
              type="button"
              aria-label="Dismiss"
              onClick={() => dismiss(r.id)}
              className="text-faint hover:text-bad transition-colors cursor-pointer shrink-0"
            >
              <X size={14} />
            </button>
          </div>
        ))}

        {needsYes.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-[11px] font-medium text-warn">
              {needsYes.length} need{needsYes.length === 1 ? "s" : ""} your yes
            </p>
            <p className="text-[11px] text-faint">{summarise(needsYes)}</p>
            {needsYes.map((y) => (
              <div key={y.id} className="rounded-lg border border-warn/30 bg-warn/10 px-2 py-1.5">
                <p className="text-[11px] text-ink truncate" title={y.label}>
                  {y.label}
                </p>
                <div className="mt-1 flex gap-1">
                  <button
                    type="button"
                    onClick={() => void answerYes(y.id, true)}
                    className="rounded border border-accent/40 bg-accent-soft px-1.5 py-0.5 text-[11px] text-accent hover:border-accent transition-colors cursor-pointer"
                  >
                    Yes
                  </button>
                  <button
                    type="button"
                    onClick={() => void answerYes(y.id, false)}
                    className="rounded border border-edge2 px-1.5 py-0.5 text-[11px] text-sub hover:text-ink transition-colors cursor-pointer"
                  >
                    No
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <Drawer
        open={!!openRun}
        onClose={() => setOpenRun(null)}
        title={<p className="font-display text-lg text-ink">{openRun?.label}</p>}
      >
        <div className="text-sm leading-relaxed text-ink">
          <ChatMarkdown text={openRun?.answer?.text ?? ""} />
        </div>
        {openRun?.answer && openRun.answer.links.length > 0 && (
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            {openRun.answer.links.map((l, j) => (
              <Link
                key={j}
                href={linkHref(l)}
                onClick={() => setOpenRun(null)}
                className="inline-flex items-center gap-1 rounded-full border border-edge2 bg-panel2 px-2.5 py-1 text-xs text-accent hover:border-accent transition-colors"
              >
                <ExternalLink size={11} />
                {l.label}
              </Link>
            ))}
          </div>
        )}
      </Drawer>
    </>
  );
}

function RunLine({ run, onNavigate }: { run: AgentRun; onNavigate?: () => void }) {
  const u = run.unit;
  const pct = u && u.total > 0 ? Math.min(100, Math.round((u.done / u.total) * 100)) : null;
  const open = run.onOpen
    ? () => {
        onNavigate?.();
        run.onOpen!();
      }
    : undefined;
  return (
    <div className="rounded-lg border border-edge bg-panel2/50 px-3 py-2.5">
      <div
        role={open ? "button" : undefined}
        tabIndex={open ? 0 : undefined}
        onClick={open}
        onKeyDown={(e) => {
          if (open && (e.key === "Enter" || e.key === " ")) {
            e.preventDefault();
            open();
          }
        }}
        className={cn("flex items-center gap-3", open && "cursor-pointer")}
      >
        <Loader2 size={14} className="animate-spin text-accent shrink-0" />
        <span className="min-w-0 flex-1">
          <span className="block text-sm text-ink truncate">
            {u ? `${run.label} ${u.noun} ${u.done + 1} of ${u.total}` : run.label}
          </span>
          <span className="block text-[11px] text-sub mt-0.5 truncate">
            running{run.desk && <span className="capitalize"> · {run.desk}</span>}
          </span>
        </span>
        {run.onStop && (
          <button
            type="button"
            aria-label="Stop"
            onClick={(e) => {
              e.stopPropagation();
              run.onStop!();
            }}
            className="text-faint hover:text-bad transition-colors cursor-pointer shrink-0"
          >
            <Square size={13} />
          </button>
        )}
      </div>
      {pct !== null && (
        <>
          <div className="mt-2 h-1 rounded-full bg-panel2 overflow-hidden">
            <span
              className="block h-full rounded-full bg-accent transition-[width] duration-500"
              style={{ width: `${pct}%` }}
            />
          </div>
          <p className="mt-1 text-[10px] text-faint leading-snug">
            {u!.done} {u!.noun}
            {u!.done === 1 ? "" : "s"} finished · stopping keeps them, resuming starts at{" "}
            {u!.done + 1}
          </p>
        </>
      )}
    </div>
  );
}

function summarise(items: PendingYes[]): string {
  const counts = new Map<string, number>();
  for (const y of items) {
    const w = KIND_WORD[y.kind];
    counts.set(w, (counts.get(w) ?? 0) + 1);
  }
  return Array.from(counts.entries())
    .map(([w, n]) => `${n} ${w}${n === 1 ? "" : "s"}`)
    .join(" · ");
}
