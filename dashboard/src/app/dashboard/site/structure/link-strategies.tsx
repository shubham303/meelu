"use client";

import { ArrowRight, Sparkles } from "lucide-react";
import { useIsApp } from "@/lib/use-app-mode";
import { useAgentTasks } from "../../agent-tasks";
import type { PromptChip } from "@/features/prompt-chips/lib";

export function LinkStrategies({
  title,
  strategies,
  onRan,
}: {
  title: string;
  strategies: PromptChip[];
  onRan?: () => void;
}) {
  const isApp = useIsApp();
  const { launchTask } = useAgentTasks();
  if (!isApp) return null;

  return (
    <div className="mb-6">
      <div className="mb-2 flex items-center justify-between gap-3">
        <h2 className="text-xs uppercase tracking-wide text-sub">{title}</h2>
        <span className="text-xs text-faint">
          Pick a strategy. The agent runs it and the results land below.
        </span>
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {strategies.map((s) => (
          <button
            key={s.label}
            type="button"
            onClick={() =>
              launchTask({
                title: `${title} — ${s.label}`,
                endpoint: "/api/agent/ask-site",
                emptyHint: s.blurb ?? s.label,
                suggestions: strategies,
                draft: {},
                autoStart: s.prompt,
                promptSurface: "structure",
                onCreated: onRan,
              })
            }
            className="group flex items-start gap-3 rounded-lg border border-edge bg-panel p-3 text-left transition hover:border-accent/40 hover:bg-accent-soft/40"
          >
            <span className="mt-0.5 rounded-md bg-accent-soft p-1.5 text-accent">
              <Sparkles size={14} />
            </span>
            <span className="min-w-0 flex-1">
              <span className="flex items-center gap-1 text-sm font-medium text-ink">
                {s.label}
                <ArrowRight
                  size={12}
                  className="opacity-0 transition group-hover:translate-x-0.5 group-hover:opacity-100"
                />
              </span>
              <span className="mt-0.5 block text-xs text-sub">{s.blurb}</span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
