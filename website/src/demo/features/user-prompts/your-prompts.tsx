"use client";

import { useState } from "react";
import { Pencil, Plus, Sparkles, Trash2 } from "lucide-react";
import { ConfirmDelete, IconButton } from "@demo/components/ui";
import { useIsApp } from "@demo/lib/use-app-mode";
import type { PromptChip } from "@demo/features/prompt-chips/lib";
import { useAgentTasks } from "@/app/demo/dashboard/agent-tasks";
import { deleteUserPrompt, useUserPrompts, type UserPrompt, type UserPromptSurface } from "./api";
import { UserPromptEditor } from "./prompt-editor";

function firstLine(text: string): string {
  return text.split("\n").find((line) => line.trim())?.trim() ?? "";
}

export function YourPrompts({
  surface,
  endpoint,
  titlePrefix,
  suggestions,
  onRan,
}: {
  surface: UserPromptSurface;
  endpoint: string;
  titlePrefix: string;
  suggestions?: PromptChip[];
  onRan?: () => void;
}) {
  const isApp = useIsApp();
  const { launchTask } = useAgentTasks();
  const { prompts, error } = useUserPrompts(surface);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<UserPrompt | null>(null);
  const [deleting, setDeleting] = useState<UserPrompt | null>(null);
  if (!isApp) return null;

  const openEditor = (prompt: UserPrompt | null) => {
    setEditing(prompt);
    setEditorOpen(true);
  };

  return (
    <section className="mb-6">
      <div className="mb-2 flex items-center justify-between gap-3">
        <h2 className="text-xs font-medium uppercase tracking-wide text-sub">Your prompts</h2>
        <span className="text-xs text-faint">Saved for this website.</span>
      </div>
      {error && <p className="mb-2 text-sm text-bad">{error}</p>}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {(prompts ?? []).map((p) => (
          <div key={p.id} className="group relative">
            <button
              type="button"
              onClick={() =>
                launchTask({
                  title: `${titlePrefix} — ${p.label}`,
                  endpoint,
                  emptyHint: p.label,
                  suggestions,
                  draft: {},
                  autoStart: p.prompt,
                  promptSurface: surface,
                  onCreated: onRan,
                })
              }
              className="flex h-full min-h-24 w-full flex-col gap-1.5 rounded-2xl border border-edge bg-panel p-4 pr-16 text-left transition hover:border-accent/40 hover:bg-accent-soft/40"
            >
              <span className="flex items-center gap-2 text-sm font-medium text-ink">
                <Sparkles size={14} className="shrink-0 text-accent" />
                <span className="truncate">{p.label}</span>
              </span>
              <span className="line-clamp-2 text-xs leading-relaxed text-sub">
                {firstLine(p.prompt)}
              </span>
            </button>
            <div className="absolute right-2 top-2 flex gap-0.5 opacity-0 transition group-focus-within:opacity-100 group-hover:opacity-100">
              <IconButton aria-label={`Edit ${p.label}`} title="Edit" onClick={() => openEditor(p)}>
                <Pencil size={13} />
              </IconButton>
              <IconButton
                aria-label={`Delete ${p.label}`}
                title="Delete"
                className="hover:text-bad"
                onClick={() => setDeleting(p)}
              >
                <Trash2 size={13} />
              </IconButton>
            </div>
          </div>
        ))}
        <button
          type="button"
          onClick={() => openEditor(null)}
          className="flex min-h-24 items-center justify-center gap-2 rounded-2xl border border-dashed border-edge2 p-4 text-sm text-sub transition hover:border-accent/50 hover:text-accent"
        >
          <Plus size={14} />
          New prompt
        </button>
      </div>

      <UserPromptEditor
        open={editorOpen}
        onClose={() => setEditorOpen(false)}
        surface={surface}
        editing={editing}
      />
      <ConfirmDelete
        open={deleting !== null}
        onClose={() => setDeleting(null)}
        what={deleting ? `"${deleting.label}"` : "prompt"}
        onConfirm={async () => {
          if (deleting) await deleteUserPrompt(deleting.id);
        }}
      />
    </section>
  );
}
