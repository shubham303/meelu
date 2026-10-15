"use client";

import { useState } from "react";
import { Button, Field, Input, Modal, Textarea } from "@demo/components/ui";
import {
  createUserPrompt,
  updateUserPrompt,
  type UserPrompt,
  type UserPromptSurface,
} from "./api";

export function UserPromptEditor({
  open,
  onClose,
  surface,
  editing,
  initialPrompt,
  elevated,
}: {
  open: boolean;
  onClose: () => void;
  surface: UserPromptSurface;
  editing?: UserPrompt | null;
  initialPrompt?: string;
  elevated?: boolean;
}) {
  return (
    <Modal
      open={open}
      onClose={onClose}
      title={editing ? "Edit prompt" : "Save a prompt"}
      elevated={elevated}
    >
      <PromptForm
        key={`${open}-${editing?.id ?? ""}-${initialPrompt ?? ""}`}
        onClose={onClose}
        surface={surface}
        editing={editing}
        initialPrompt={initialPrompt}
      />
    </Modal>
  );
}

function PromptForm({
  onClose,
  surface,
  editing,
  initialPrompt,
}: {
  onClose: () => void;
  surface: UserPromptSurface;
  editing?: UserPrompt | null;
  initialPrompt?: string;
}) {
  const [label, setLabel] = useState(editing?.label ?? "");
  const [prompt, setPrompt] = useState(editing?.prompt ?? initialPrompt ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSave = !busy && label.trim().length > 0 && prompt.trim().length > 0;

  async function save() {
    if (!canSave) return;
    setBusy(true);
    try {
      const input = { label: label.trim(), prompt: prompt.trim() };
      if (editing) await updateUserPrompt(editing.id, input);
      else await createUserPrompt(surface, input);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save the prompt.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        void save();
      }}
    >
      <Field label="Name" hint="Shown on the card. Saved for this website only.">
        <Input
          value={label}
          maxLength={80}
          autoFocus
          placeholder="Weekly keyword check"
          onChange={(e) => setLabel(e.target.value)}
        />
      </Field>
      <Field label="Prompt" hint="Sent to Meelu as is when you click the card.">
        <Textarea
          value={prompt}
          maxLength={8000}
          className="min-h-48"
          placeholder="Tell Meelu what to do…"
          onChange={(e) => setPrompt(e.target.value)}
        />
      </Field>
      {error && <p className="text-sm text-bad">{error}</p>}
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" disabled={!canSave}>
          {editing ? "Save changes" : "Save prompt"}
        </Button>
      </div>
    </form>
  );
}
