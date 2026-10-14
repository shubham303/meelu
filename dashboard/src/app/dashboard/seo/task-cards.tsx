"use client";

import { Sparkles } from "lucide-react";
import { useIsApp } from "@/lib/use-app-mode";
import type { PromptChip } from "@/features/prompt-chips/lib";
import { useAgentTasks } from "../agent-tasks";

export const SEO_ASK = "/api/agent/ask-seo";

export function TaskCards({
  title,
  chips,
  onRan,
}: {
  title: string;
  chips: PromptChip[];
  onRan?: () => void;
}) {
  const isApp = useIsApp();
  const { launchTask } = useAgentTasks();
  if (!isApp) return null;

  return (
    <section className="mb-6">
      <h2 className="mb-2 text-xs font-medium uppercase tracking-wide text-sub">
        {title}
      </h2>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {chips.map((chip) => (
          <button
            key={chip.label}
            type="button"
            onClick={() =>
              launchTask({
                title: `SEO — ${chip.label}`,
                endpoint: SEO_ASK,
                emptyHint: chip.blurb ?? chip.label,
                suggestions: chips,
                draft: {},
                autoStart: chip.prompt,
                promptSurface: "seo",
                onCreated: onRan,
              })
            }
            className="group flex min-h-24 flex-col gap-1.5 rounded-2xl border border-edge bg-panel p-4 text-left transition hover:border-accent/40 hover:bg-accent-soft/40"
          >
            <span className="flex items-center gap-2 text-sm font-medium text-ink">
              <Sparkles size={14} className="text-accent" />
              {chip.label}
            </span>
            {chip.blurb && (
              <span className="text-xs leading-relaxed text-sub">
                {chip.blurb}
              </span>
            )}
          </button>
        ))}
      </div>
    </section>
  );
}
