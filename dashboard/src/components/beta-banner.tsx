"use client";

import { useSyncExternalStore } from "react";
import { FlaskConical, X } from "lucide-react";

const DISMISSED_KEY = "meelu.beta.dismissed";
const listeners = new Set<() => void>();

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function dismissed(): boolean {
  try {
    return localStorage.getItem(DISMISSED_KEY) === "1";
  } catch {
    return false;
  }
}

function dismiss() {
  try {
    localStorage.setItem(DISMISSED_KEY, "1");
  } catch {}
  listeners.forEach((listener) => listener());
}

export function BetaBanner() {
  const hidden = useSyncExternalStore(subscribe, dismissed, () => true);
  if (hidden) return null;

  return (
    <div role="note" className="border-b border-warn/30 bg-warn/10 px-8 py-1.5 text-xs text-sub">
      <div className="mx-auto flex w-full max-w-6xl items-center gap-2">
        <FlaskConical size={13} className="shrink-0 text-warn" />
        <p className="min-w-0 flex-1">
          <span className="font-medium text-ink">Beta</span> · Meelu is updated often and you may run into bugs. The app is
          not yet verified by Apple, Microsoft or Google, so security warnings when you install or update it are expected.
        </p>
        <button
          type="button"
          onClick={dismiss}
          aria-label="Dismiss"
          className="shrink-0 rounded p-1 text-sub hover:bg-warn/20 hover:text-ink cursor-pointer"
        >
          <X size={13} />
        </button>
      </div>
    </div>
  );
}
