"use client";

import { useEffect, useState, useSyncExternalStore } from "react";
import { api, apiPaged, useCurrentSite } from "@/lib/use-api";

export type UserPromptSurface = "seo" | "structure";

export interface UserPrompt {
  id: string;
  siteId: string;
  surface: UserPromptSurface;
  label: string;
  prompt: string;
  createdAt: string;
  updatedAt: string;
}

export interface UserPromptInput {
  label: string;
  prompt: string;
}

let version = 0;
const listeners = new Set<() => void>();

function changed(): void {
  version += 1;
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export async function createUserPrompt(
  surface: UserPromptSurface,
  input: UserPromptInput,
): Promise<UserPrompt> {
  const created = await api<UserPrompt>("/api/v1/user-prompts", {
    method: "POST",
    body: { surface, ...input },
  });
  changed();
  return created;
}

export async function updateUserPrompt(id: string, input: UserPromptInput): Promise<UserPrompt> {
  const updated = await api<UserPrompt>(`/api/v1/user-prompts/${id}`, {
    method: "PATCH",
    body: input,
  });
  changed();
  return updated;
}

export async function deleteUserPrompt(id: string): Promise<void> {
  await api(`/api/v1/user-prompts/${id}`, { method: "DELETE" });
  changed();
}

export function useUserPrompts(surface: UserPromptSurface) {
  const site = useCurrentSite();
  const seen = useSyncExternalStore(subscribe, () => version, () => 0);
  const [prompts, setPrompts] = useState<UserPrompt[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let live = true;
    apiPaged<UserPrompt>(`/api/v1/user-prompts?surface=${surface}&page_size=100`)
      .then((page) => {
        if (!live) return;
        setPrompts(page.data);
        setError(null);
      })
      .catch((e: unknown) => {
        if (live) setError(e instanceof Error ? e.message : "Could not load your prompts.");
      });
    return () => {
      live = false;
    };
  }, [surface, site, seen]);

  return { prompts, error };
}
