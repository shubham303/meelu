"use client";

export interface SessionUsage {
  tokens: number;
  inputTokens: number;
  outputTokens: number;
  costUsd: number;
  turns: number;
  startedAt: number;
  busy: boolean;
}

let current: SessionUsage | null = null;
let wired = false;
let detach: (() => void) | undefined;
const listeners = new Set<() => void>();

function emit() {
  for (const l of listeners) l();
}

function set(next: SessionUsage | null) {
  if (
    current &&
    next &&
    current.tokens === next.tokens &&
    current.inputTokens === next.inputTokens &&
    current.outputTokens === next.outputTokens &&
    current.costUsd === next.costUsd &&
    current.turns === next.turns &&
    current.busy === next.busy
  ) {
    return;
  }
  current = next;
  emit();
}

async function refresh(busy: boolean) {
  const bridge = typeof window !== "undefined" ? window.meeluAgent : undefined;
  if (!bridge?.sessionUsage) return;
  try {
    const usage = await bridge.sessionUsage();
    set({ ...usage, busy });
  } catch {
  }
}

function wire() {
  if (wired) return;
  wired = true;
  const bridge = typeof window !== "undefined" ? window.meeluAgent : undefined;
  if (!bridge?.sessionUsage) return;

  void refresh(false);
  detach = bridge.onEvent?.((m) => {
    if (m.event === "done") {
      void refresh(false);
    } else if (m.event === "session" || m.event === "tool" || m.event === "text") {
      if (current) set({ ...current, busy: true });
    }
  });
}

export function subscribeToUsage(listener: () => void): () => void {
  wire();
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0) {
      detach?.();
      detach = undefined;
      wired = false;
    }
  };
}

export function usageSnapshot(): SessionUsage | null {
  return current;
}

export function usageServerSnapshot(): SessionUsage | null {
  return null;
}
