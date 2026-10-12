"use client";

import { useState } from "react";
import { ArrowRight, Check, Copy } from "lucide-react";
import { cn } from "@demo/lib/utils";
import type { GuidePrompt } from "@demo/lib/agents";

function withPlaceholders(say: string) {
  return say.split(/(\[[^\]]+\])/g).map((part, i) =>
    part.startsWith("[") && part.endsWith("]") ? (
      <span key={i} className="text-accent">
        {part}
      </span>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

export function PromptCard({ prompt }: { prompt: GuidePrompt }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(prompt.say);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
    }
  }

  return (
    <div className="stagger-item group relative rounded-2xl border border-edge bg-panel p-4 pr-11 transition-colors hover:border-edge2">
      <p className="text-sm leading-relaxed text-ink">
        &ldquo;{withPlaceholders(prompt.say)}&rdquo;
      </p>
      <p className="mt-2 flex items-start gap-1.5 text-xs leading-relaxed text-sub">
        <ArrowRight size={12} className="mt-0.5 shrink-0 text-faint" />
        {prompt.then}
      </p>
      <button
        onClick={copy}
        aria-label="Copy this prompt"
        className={cn(
          "absolute right-2 top-2 cursor-pointer rounded-md p-1.5 transition-colors",
          "text-faint hover:bg-panel2 hover:text-ink",
        )}
      >
        {copied ? <Check size={14} className="text-good" /> : <Copy size={14} />}
      </button>
    </div>
  );
}
