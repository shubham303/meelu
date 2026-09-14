"use client";

import { useMemo, useState } from "react";
import { Check, Sparkles, X } from "lucide-react";
import { Button, IconButton } from "@/components/ui";
import { cn } from "@/lib/utils";
import { toolLabel, type PieceIssue } from "../types";

export function CheckIcon({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 11l3 3L22 4" />
      <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
    </svg>
  );
}

export function ChecksPanel({
  issues,
  activeId,
  running,
  canRun,
  runError,
  agentBusy,
  onClose,
  onRun,
  onSelect,
  onEdit,
  onFix,
  onState,
}: {
  issues: PieceIssue[];
  activeId: string | null;
  running: boolean;
  canRun: boolean;
  runError: string | null;
  agentBusy: boolean;
  onClose: () => void;
  onRun: () => void;
  onSelect: (issue: PieceIssue) => void;
  onEdit: (issue: PieceIssue) => void;
  onFix: (issue: PieceIssue) => void;
  onState: (issue: PieceIssue, state: PieceIssue["state"]) => void;
}) {
  const [tool, setTool] = useState<string | null>(null);
  const tools = useMemo(() => {
    const counts = new Map<string, number>();
    for (const i of issues) if (i.state === "open") counts.set(i.tool, (counts.get(i.tool) ?? 0) + 1);
    return Array.from(counts.entries());
  }, [issues]);
  const open = issues.filter((i) => i.state === "open").length;
  const shown = issues.filter((i) => (tool ? i.tool === tool : true));

  return (
    <aside className="flex w-[360px] shrink-0 flex-col border-l border-edge bg-bg">
      <div className="flex items-center justify-between border-b border-edge bg-panel px-5 py-3.5">
        <div className="flex items-center gap-2 text-[13px] font-medium text-ink">
          <CheckIcon /> Checks
          <span className="font-normal text-faint">· {open} open</span>
        </div>
        <div className="flex items-center gap-1">
          {canRun && (
            <Button variant="ghost" size="sm" onClick={onRun} disabled={running}>
              {running ? "Running…" : issues.length ? "Run again" : "Run checks"}
            </Button>
          )}
          <IconButton onClick={onClose} aria-label="Close">
            <X size={14} />
          </IconButton>
        </div>
      </div>

      {tools.length > 1 && (
        <div className="flex flex-wrap gap-1.5 px-5 pt-3">
          <Chip active={tool === null} onClick={() => setTool(null)}>
            All {open}
          </Chip>
          {tools.map(([t, n]) => (
            <Chip key={t} active={tool === t} onClick={() => setTool(t)}>
              {toolLabel(t)} {n}
            </Chip>
          ))}
        </div>
      )}

      <div className="flex-1 space-y-2.5 overflow-y-auto px-5 pb-5 pt-3">
        {runError && <p className="text-xs text-bad">{runError}</p>}
        {!canRun && issues.length === 0 && (
          <p className="text-xs leading-relaxed text-faint">
            Checks run on your device — open this piece in the Meelu app to run them.
          </p>
        )}
        {canRun && issues.length === 0 && !running && (
          <p className="text-xs leading-relaxed text-faint">
            Checks run on your device: readability reads the text, similarity compares each paragraph against the crawled pages of this site, and the AI detector scores it with a local classifier (a one-time 150 MB download on the first run). Click an issue to see the passage; fix it yourself or hand it to the agent.
          </p>
        )}
        {shown.map((issue) => {
          const active = issue.id === activeId;
          const done = issue.state !== "open";
          return (
            <div
              key={issue.id}
              onClick={() => onSelect(issue)}
              className={cn(
                "flex cursor-pointer flex-col gap-1.5 rounded-xl border bg-panel px-3.5 py-3 transition-colors",
                active ? "border-accent shadow-[0_0_0_3px_#2563eb14]" : "border-edge hover:border-edge2",
                done && "opacity-60",
              )}
            >
              <span className="text-[11px] font-medium uppercase tracking-wide text-faint">
                {toolLabel(issue.tool)}
              </span>
              <span className="text-sm font-medium leading-snug text-ink">{issue.title}</span>
              {issue.detail && <span className="text-[13px] leading-relaxed text-sub">{issue.detail}</span>}
              {issue.suggestion && (
                <span className="rounded-md bg-good/10 px-2 py-1 text-[13px] leading-relaxed text-good">
                  {issue.suggestion}
                </span>
              )}
              {done ? (
                <span className="mt-0.5 inline-flex items-center gap-1 text-xs text-good">
                  <Check size={12} /> {issue.state === "fixed" ? "Fixed" : "Dismissed"}
                </span>
              ) : (
                <div className="mt-1 flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                  {issue.anchorText && (
                    <Button variant="outline" size="sm" onClick={() => onEdit(issue)}>
                      Edit
                    </Button>
                  )}
                  {issue.anchorText && onFix && (
                    <Button
                      size="sm"
                      className="bg-accent-soft text-accent hover:bg-accent/20"
                      disabled={agentBusy}
                      onClick={() => onFix(issue)}
                    >
                      <Sparkles size={12} /> Fix with agent
                    </Button>
                  )}
                  <button
                    type="button"
                    onClick={() => onState(issue, issue.anchorText ? "dismissed" : "fixed")}
                    className="ml-auto text-xs text-faint transition-colors hover:text-ink cursor-pointer"
                  >
                    {issue.anchorText ? "Dismiss" : "Done"}
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </aside>
  );
}

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full border px-2.5 py-1 text-xs transition-colors cursor-pointer",
        active ? "border-ink bg-ink text-white" : "border-edge2 bg-panel text-sub hover:text-ink",
      )}
    >
      {children}
    </button>
  );
}
