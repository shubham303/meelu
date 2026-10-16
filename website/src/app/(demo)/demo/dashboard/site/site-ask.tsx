"use client";

import { Sparkles } from "lucide-react";
import { IconButton } from "@demo/components/ui";
import { useIsApp } from "@demo/lib/use-app-mode";
import { useAgentTasks } from "../agent-tasks";
import type { PromptChip } from "@demo/features/prompt-chips/lib";
import type { UserPromptSurface } from "@demo/features/user-prompts/api";

export function SiteAskButton({
  title,
  hint,
  suggestions,
  draft,
  onRan,
  endpoint = "/api/agent/ask-site",
  promptSurface,
}: {
  title: string;
  hint: string;
  suggestions?: PromptChip[];
  draft?: Record<string, string | undefined>;
  onRan?: () => void;
  endpoint?: string;
  promptSurface?: UserPromptSurface;
}) {
  const isApp = useIsApp();
  const { launchTask } = useAgentTasks();
  if (!isApp) return null;

  return (
    <IconButton
      title="Ask Meelu"
      aria-label="Ask Meelu"
      className="border border-accent/30 bg-accent-soft text-accent hover:bg-accent-soft hover:text-accent"
      onClick={() =>
        launchTask({
          title,
          endpoint,
          emptyHint: hint,
          suggestions,
          draft: draft ?? {},
          promptSurface,
          onCreated: onRan,
        })
      }
    >
      <Sparkles size={16} />
    </IconButton>
  );
}
