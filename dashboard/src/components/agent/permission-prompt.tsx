"use client";

import { Wrench } from "lucide-react";
import { Button } from "@/components/ui";

export function PermissionPrompt({
  item,
  onAnswer,
}: {
  item: { tool: string; input: Record<string, unknown>; answered?: string };
  onAnswer: (decision: "allow" | "always" | "full" | "deny") => void;
}) {
  const summary = Object.entries(item.input)
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .slice(0, 4)
    .map(([k, v]) => `${k}: ${typeof v === "string" ? v : JSON.stringify(v)}`)
    .join(" · ");

  if (item.answered) {
    return (
      <p className="flex items-center gap-1.5 text-[11px] text-faint font-mono">
        <Wrench size={10} className="shrink-0" />
        {item.tool} — {item.answered === "deny" ? "declined" : "allowed"}
      </p>
    );
  }

  return (
    <div className="rounded-lg border border-accent/30 bg-accent-soft px-3 py-2.5 space-y-2">
      <div>
        <p className="text-sm text-ink font-medium">
          Meelu wants to run <span className="font-mono">{item.tool}</span>
        </p>
        {summary && (
          <p className="text-xs text-sub mt-0.5 line-clamp-3 break-words">{summary}</p>
        )}
      </div>
      <div className="flex flex-wrap gap-1.5">
        <Button size="sm" onClick={() => onAnswer("allow")}>
          Allow
        </Button>
        <Button size="sm" variant="outline" onClick={() => onAnswer("always")}>
          Always allow this action
        </Button>
        <Button size="sm" variant="outline" onClick={() => onAnswer("full")}>
          Full access
        </Button>
        <Button size="sm" variant="outline" onClick={() => onAnswer("deny")}>
          No
        </Button>
      </div>
      <p className="text-[11px] text-faint">
        “Always” and “full access” last until you quit the app.
      </p>
    </div>
  );
}
