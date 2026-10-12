"use client";

import { useEffect, useMemo, useRef, useSyncExternalStore, type ReactNode } from "react";
import { isAppUserAgent } from "@demo/lib/app-mode";
import { activeSiteId } from "@demo/lib/current-site";
import { useApi } from "@demo/lib/use-api";
import { cn } from "@demo/lib/utils";

export interface AgentEvent {
  turnId: string;
  event: string;
  data: Record<string, unknown>;
}

export interface AgentScopeInfo {
  action: string;
  readOnly: boolean;
  writes: string[];
  servers: string[];
  notices: string[];
}

export interface AskLink {
  label: string;
  desk: string;
  id?: string | null;
}

export interface TurnPayload {
  action: string;
  siteId: string | null;
  message: string;
  sessionId?: string;
  form?: Record<string, string | undefined>;
  params?: Record<string, string>;
}

export interface AgentBridge {
  runTurn: (payload: TurnPayload) => Promise<{ turnId?: string; error?: string }>;
  onEvent: (cb: (m: AgentEvent) => void) => () => void;
  abort: (turnId: string) => void;
  crawlToken?: (domain: string) => Promise<{ token?: string | null; error?: string }>;
  respondPermission?: (
    requestId: string,
    decision: "allow" | "always" | "full" | "deny",
  ) => Promise<{ ok?: boolean; error?: string }>;
}

declare global {
  interface Window {
    meelu?: AgentBridge;
  }
}

export function agentEnabled(): boolean {
  if (typeof window === "undefined") return false;
  if (!isAppUserAgent(navigator.userAgent)) return false;
  return !!bridge();
}

export function bridge(): AgentBridge | null {
  if (typeof window === "undefined") return null;
  const w = window as Window & { meeluAgent?: AgentBridge };
  return w.meelu ?? w.meeluAgent ?? null;
}

const noSubscribe = () => () => {};

export function useAgentEnabled(): boolean {
  return useSyncExternalStore(noSubscribe, agentEnabled, () => false);
}

export function refuseOnWeb(what: string): boolean {
  if (agentEnabled()) return false;
  if (process.env.NODE_ENV !== "production") {
    console.warn(
      `[agent] ${what} was called without the local harness. The web frontend has no ` +
        "agent harness by design — gate the affordance that called this on useIsApp().",
    );
  }
  return true;
}

export interface TurnResult {
  ok: boolean;
  text: string;
  links: AskLink[];
  scope: AgentScopeInfo | null;
  sessionId: string | null;
  tools: string[];
  error?: string;
}

export interface StreamOptions extends Omit<TurnPayload, "siteId"> {
  siteId?: string | null;
  onText?: (chunk: string, full: string) => void;
  onScope?: (scope: AgentScopeInfo) => void;
  onTool?: (name: string) => void;
  onEvent?: (e: AgentEvent) => void;
}

export interface RunningTurn {
  result: Promise<TurnResult>;
  abort: () => void;
}

export function streamTurn(opts: StreamOptions): RunningTurn {
  const b = bridge();
  if (!agentEnabled() || !b) {
    refuseOnWeb(`streamTurn(${opts.action})`);
    return {
      abort: () => {},
      result: Promise.resolve({
        ok: false,
        text: "",
        links: [],
        scope: null,
        sessionId: null,
        tools: [],
        error: "Agent tasks run on your device — open this in the Meelu app.",
      }),
    };
  }

  const siteId = opts.siteId === undefined ? activeSiteId() : opts.siteId;
  let turnId: string | null = null;
  let raw = "";
  let scope: AgentScopeInfo | null = null;
  let sessionId: string | null = opts.sessionId ?? null;
  const tools: string[] = [];
  let failure: string | null = null;
  let aborted = false;
  const pending: AgentEvent[] = [];

  let finish: (r: TurnResult) => void = () => {};
  const result = new Promise<TurnResult>((resolve) => {
    finish = resolve;
  });

  const settle = () => {
    off();
    const parsed = parseLinks(raw);
    finish({
      ok: !failure,
      text: parsed.text,
      links: parsed.links,
      scope,
      sessionId,
      tools,
      error: failure ?? undefined,
    });
  };

  const handle = (m: AgentEvent) => {
    opts.onEvent?.(m);
    if (m.event === "session" && typeof m.data.sessionId === "string") {
      sessionId = m.data.sessionId;
    } else if (m.event === "scope") {
      scope = readScope(m.data);
      if (scope) opts.onScope?.(scope);
    } else if (m.event === "text" && typeof m.data.text === "string") {
      raw += m.data.text;
      opts.onText?.(m.data.text, raw);
    } else if (m.event === "tool" && typeof m.data.name === "string") {
      tools.push(m.data.name);
      opts.onTool?.(m.data.name);
    } else if (m.event === "done") {
      if (!m.data.ok && typeof m.data.error === "string") failure = m.data.error;
      settle();
    }
  };

  const off = b.onEvent((m) => {
    if (turnId === null) {
      pending.push(m);
      return;
    }
    if (m.turnId !== turnId) return;
    handle(m);
  });

  const start = b.runTurn({
    action: opts.action,
    siteId,
    message: opts.message,
    sessionId: opts.sessionId,
    form: opts.form ?? {},
    params: opts.params,
  });

  void start
    .then((res) => {
      if (aborted) return;
      if (res.error || !res.turnId) {
        failure = res.error ?? "The app could not start the task.";
        settle();
        return;
      }
      turnId = res.turnId;
      const queued = pending.splice(0, pending.length);
      for (const m of queued) if (m.turnId === turnId) handle(m);
    })
    .catch((e: unknown) => {
      failure = e instanceof Error ? e.message : String(e);
      settle();
    });

  return {
    result,
    abort: () => {
      aborted = true;
      if (turnId) b.abort(turnId);
      settle();
    },
  };
}

export function runAgentTurn(opts: StreamOptions): Promise<TurnResult> {
  return streamTurn(opts).result;
}

export function useAbortOnUnmount(): {
  hold: (t: RunningTurn) => RunningTurn;
  abort: () => void;
} {
  const ref = useRef<RunningTurn | null>(null);
  useEffect(() => () => ref.current?.abort(), []);
  return {
    hold: (t) => {
      ref.current = t;
      return t;
    },
    abort: () => {
      ref.current?.abort();
      ref.current = null;
    },
  };
}

function readScope(data: Record<string, unknown>): AgentScopeInfo | null {
  if (!data || typeof data !== "object") return null;
  const strings = (v: unknown): string[] =>
    Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
  const writes = strings(data.writes);
  return {
    action: typeof data.action === "string" ? data.action : "",
    readOnly: data.readOnly === true || writes.length === 0,
    writes,
    servers: strings(data.servers),
    notices: strings(data.notices),
  };
}

export function parseFencedBlock<T>(text: string, name: string): { text: string; value: T | null } {
  const raw = String(text ?? "");
  const fence = new RegExp("```" + name + "\\s*([\\s\\S]*?)```");
  const m = raw.match(fence);
  if (!m) return { text: raw.trim(), value: null };
  let value: T | null = null;
  try {
    value = JSON.parse(m[1]) as T;
  } catch {
  }
  return { text: raw.replace(m[0], "").trim(), value };
}

export function parseLinks(text: string): { text: string; links: AskLink[] } {
  const { text: rest, value } = parseFencedBlock<unknown>(text, "links");
  const rows = Array.isArray(value) ? value : [];
  const links: AskLink[] = [];
  for (const row of rows) {
    if (!row || typeof row !== "object") continue;
    const r = row as Record<string, unknown>;
    if (typeof r.label !== "string" || typeof r.desk !== "string") continue;
    links.push({ label: r.label, desk: r.desk, id: typeof r.id === "string" ? r.id : null });
  }
  return { text: rest, links };
}

interface ScopeResponse {
  action: string;
  writes: string[];
  mcpServers?: Record<string, unknown>;
  global?: boolean;
}

export function useScopeInfo(
  action: string | null,
  forAction?: string | null,
): AgentScopeInfo | null {
  const qs = action
    ? `/api/v1/agent/scope?action=${encodeURIComponent(action)}` +
      (forAction ? `&for=${encodeURIComponent(forAction)}` : "")
    : null;
  const { data } = useApi<ScopeResponse>(qs);
  return useMemo(() => {
    if (!data) return null;
    const writes = Array.isArray(data.writes) ? data.writes : [];
    return {
      action: data.action ?? action ?? "",
      readOnly: writes.length === 0,
      writes,
      servers: data.mcpServers ? Object.keys(data.mcpServers) : [],
      notices: [],
    };
  }, [data, action]);
}

export function ScopeSummary({
  scope,
  fallback,
  className,
}: {
  scope: AgentScopeInfo | null;
  fallback?: ReactNode;
  className?: string;
}) {
  if (!scope) {
    return fallback ? (
      <span className={cn("text-xs text-sub", className)}>{fallback}</span>
    ) : null;
  }
  return (
    <span className={cn("text-xs text-sub", className)}>
      reads everything
      {scope.readOnly ? (
        <> · {"writes nothing at all"}</>
      ) : (
        <> · may write with {namesOrCount(scope.writes)}</>
      )}
      {scope.servers.length > 0 && <> · using {scope.servers.join(", ")}</>}
      {scope.notices.map((n) => (
        <span key={n} className="text-warn">
          {" "}
          · {n}
        </span>
      ))}
    </span>
  );
}

function namesOrCount(writes: string[]): string {
  if (writes.length <= 2) return writes.join(" and ");
  return `${writes.length} tools`;
}

export function ScopeWrites({ scope }: { scope: AgentScopeInfo | null }) {
  if (!scope) return null;
  if (scope.readOnly) {
    return (
      <p className="text-xs text-faint">
        Zero writes. {"It cannot change anything — not even the thing it is describing."}
      </p>
    );
  }
  return (
    <p className="text-xs text-faint">
      Writes with{" "}
      <span className="font-mono text-sub">{scope.writes.join(", ")}</span>
    </p>
  );
}
