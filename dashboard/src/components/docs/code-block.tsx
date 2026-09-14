"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { cn } from "@/lib/utils";

export function CodeBlock({
  code,
  label,
  className,
}: {
  code: string;
  label?: string;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
    }
  }

  return (
    <div className={cn("relative", className)}>
      {label && (
        <div className="flex items-center justify-between rounded-t-xl border border-b-0 border-edge bg-panel px-3 py-1.5">
          <span className="font-mono text-[11px] text-faint">{label}</span>
        </div>
      )}
      <pre
        className={cn(
          "overflow-x-auto border border-edge bg-panel2 p-4 text-xs leading-relaxed text-sub",
          label ? "rounded-b-xl" : "rounded-xl",
        )}
      >
        <code className="font-mono whitespace-pre">{code}</code>
      </pre>
      <button
        onClick={copy}
        aria-label="Copy to clipboard"
        className={cn(
          "absolute right-2 rounded-md p-1.5 text-sub transition-colors hover:bg-panel hover:text-ink",
          label ? "top-1" : "top-2",
        )}
      >
        {copied ? <Check size={14} className="text-good" /> : <Copy size={14} />}
      </button>
    </div>
  );
}
