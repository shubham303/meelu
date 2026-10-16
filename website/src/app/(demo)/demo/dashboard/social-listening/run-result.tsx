"use client";

import { X } from "lucide-react";
import { cn } from "@demo/lib/utils";

export interface RunOutcome {
  stopped: boolean;
  fetched: number;
  inserted: number;
  kept: number;
  platforms: Record<string, { error?: string | null }>;
}

function listOf(names: string[]) {
  if (names.length <= 1) return names.join("");
  return `${names.slice(0, -1).join(", ")} and ${names.at(-1)}`;
}

export function RunResult({
  outcome,
  platformLabel,
  onDismiss,
}: {
  outcome: RunOutcome;
  platformLabel: (id: string) => string;
  onDismiss: () => void;
}) {
  const failed = Object.entries(outcome.platforms).filter(([, s]) => s.error);
  const searched = listOf(Object.keys(outcome.platforms).map(platformLabel));
  const good = !outcome.stopped && outcome.kept > 0;

  let title: string;
  let hint: string | null = null;
  if (outcome.stopped) {
    title = "Run stopped.";
    hint = outcome.kept > 0 ? `${outcome.kept} posts it had already checked are in To reply.` : null;
  } else if (outcome.kept > 0) {
    title = `Run finished: ${outcome.kept} new ${outcome.kept === 1 ? "post" : "posts"} to reply to.`;
  } else if (outcome.fetched === 0) {
    title = "Run finished with no posts.";
    hint = `${searched || "The platforms"} returned nothing new for your lines since the last run (a run looks back at most 7 days). Turn on more platforms, or describe the conversation more broadly.`;
  } else if (outcome.inserted === 0) {
    title = "Run finished with no new posts.";
    hint = `All ${outcome.fetched} posts it found were ones Meelu has already shown you or set aside.`;
  } else {
    title = "Run finished: nothing fit closely enough.";
    hint = `${outcome.inserted} new posts were checked and none matched your lines. Try a looser setting, or reword a line to say who is posting and what they want.`;
  }

  return (
    <div
      role="status"
      className={cn(
        "flex items-start gap-3 rounded-[14px] border px-4 py-3",
        good ? "border-good/30 bg-good/5" : "border-edge bg-panel",
      )}
    >
      <div className="min-w-0 flex-1 space-y-1">
        <p className={cn("text-sm font-medium", good ? "text-good" : "text-ink")}>{title}</p>
        {hint && <p className="text-[13px] text-sub">{hint}</p>}
        {failed.map(([id, s]) => (
          <p key={id} className="text-[13px] text-bad">
            {platformLabel(id)} failed: {s.error}
          </p>
        ))}
      </div>
      <button
        type="button"
        aria-label="Dismiss"
        onClick={onDismiss}
        className="cursor-pointer rounded-md p-1 text-faint hover:text-ink"
      >
        <X size={14} />
      </button>
    </div>
  );
}
