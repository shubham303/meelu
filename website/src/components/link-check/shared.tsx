"use client";

import { useState, type MouseEvent as ReactMouseEvent } from "react";
import { Check, Copy, X } from "lucide-react";
import type { LinkState } from "@/lib/link-check/types";

export const STATE_LABEL: Record<LinkState, string> = {
  broken: "Broken",
  "no-answer": "No answer",
  blocked: "Unverified",
  redirect: "Redirect",
  ok: "OK",
  unchecked: "Not checked",
};

export const STATE_CLASS: Record<LinkState, string> = {
  broken: "border-bad/25 bg-bad/10 text-bad",
  "no-answer": "border-warn/25 bg-warn/10 text-warn",
  blocked: "border-edge2 bg-panel2 text-sub",
  redirect: "border-accent/25 bg-accent/10 text-accent",
  ok: "border-good/25 bg-good/10 text-good",
  unchecked: "border-edge2 bg-panel2 text-faint",
};

export const STATE_DOT: Record<LinkState, string> = {
  broken: "bg-bad",
  "no-answer": "bg-warn",
  blocked: "bg-faint",
  redirect: "bg-accent",
  ok: "bg-good",
  unchecked: "bg-faint",
};

export function StatePill({ state }: { state: LinkState }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 font-mono text-[11px] font-medium whitespace-nowrap ${STATE_CLASS[state]}`}
    >
      <span className={`size-1.5 rounded-full ${STATE_DOT[state]}`} />
      {STATE_LABEL[state]}
    </span>
  );
}

export function shortUrl(url: string, origin: string): string {
  if (url.startsWith(origin)) {
    const rest = url.slice(origin.length);
    return rest === "" ? "/" : rest;
  }
  return url.replace(/^https?:\/\//, "");
}

/**
 * Copy `text` to the clipboard. Falls back to a hidden textarea when the
 * async Clipboard API is missing or refused (older browsers, insecure origin).
 */
export async function copyText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // fall through to the textarea fallback
  }
  try {
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.top = "0";
    area.style.left = "-9999px";
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand("copy");
    area.remove();
    return ok;
  } catch {
    return false;
  }
}

/**
 * Small clipboard button. Stops propagation so it stays usable inside rows
 * that carry their own click behaviour.
 */
export function CopyButton({
  value,
  label,
  className = "",
}: {
  value: string;
  label: string;
  className?: string;
}) {
  const [status, setStatus] = useState<"idle" | "copied" | "failed">("idle");

  async function onCopy(event: ReactMouseEvent<HTMLButtonElement>) {
    event.preventDefault();
    event.stopPropagation();
    const ok = await copyText(value);
    setStatus(ok ? "copied" : "failed");
    window.setTimeout(() => setStatus("idle"), 2000);
  }

  const Icon = status === "copied" ? Check : status === "failed" ? X : Copy;

  return (
    <>
      <button
        type="button"
        onClick={onCopy}
        title={status === "copied" ? "Copied" : label}
        aria-label={label}
        className={`inline-flex shrink-0 items-center justify-center rounded-md border border-edge2 bg-panel p-1.5 transition-colors hover:bg-panel2 ${
          status === "copied"
            ? "text-good"
            : status === "failed"
              ? "text-bad"
              : "text-faint hover:text-ink"
        } ${className}`}
      >
        <Icon size={13} />
      </button>
      <span className="sr-only" aria-live="polite">
        {status === "copied"
          ? "Copied to clipboard"
          : status === "failed"
            ? "Copy failed. Select the text and copy it by hand."
            : ""}
      </span>
    </>
  );
}
