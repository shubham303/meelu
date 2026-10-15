"use client";

import { useSyncExternalStore } from "react";
import { api } from "@demo/lib/use-api";
import type { OwnModel } from "@/app/demo/dashboard/agent-tasks";

export type LlmTier = "featured" | "well_known" | "other";

export interface LlmModel {
  id: string;
  name: string;
  provider: string;
  tier: LlmTier;
  inputUsdPerMillion: number;
  outputUsdPerMillion: number;
  contextLength: number;
}

export const TIER_LABEL: Record<LlmTier, string> = {
  featured: "Recommended",
  well_known: "Well-known providers",
  other: "Other models",
};

const LIST_MS = 6 * 60 * 60 * 1000;
let listed: { at: number; models: Promise<LlmModel[]> } | null = null;

export function listModels(): Promise<LlmModel[]> {
  if (!listed || Date.now() - listed.at > LIST_MS) {
    const models = api<LlmModel[]>("/api/v1/llm/models");
    listed = { at: Date.now(), models };
    models.catch(() => {
      listed = null;
    });
  }
  return listed.models;
}

export async function defaultModel(): Promise<string> {
  return (await api<{ defaultModel: string }>("/api/v1/llm/preference")).defaultModel;
}

export async function setDefaultModel(id: string): Promise<string> {
  const res = await api<{ defaultModel: string }>("/api/v1/llm/preference", {
    method: "PUT",
    body: { defaultModel: id },
  });
  return res.defaultModel;
}

const OWN_ANTHROPIC_PREFIX = "own:anthropic/";

export function ownModelId(id: string): string {
  return `${OWN_ANTHROPIC_PREFIX}${id}`;
}

export interface OwnModels {
  models: OwnModel[];
  defaultModel: string;
}

export async function listOwnModels(): Promise<OwnModels | null> {
  const bridge = typeof window !== "undefined" ? window.meeluAgent : undefined;
  if (!bridge?.getOwnKeys || !bridge.ownModels) return null;
  const keys = await bridge.getOwnKeys();
  if ("error" in keys || !keys.anthropic.saved) return null;
  const listed = await bridge.ownModels();
  if ("error" in listed) return null;
  return { models: listed.models, defaultModel: keys.anthropic.defaultModel };
}

export function price(usdPerMillion: number): string {
  if (usdPerMillion === 0) return "free";
  return `$${usdPerMillion < 1 ? usdPerMillion.toFixed(3).replace(/0$/, "") : usdPerMillion.toFixed(2)}`;
}

export function contextLabel(tokens: number): string {
  if (tokens >= 1_000_000) return `${+(tokens / 1_000_000).toFixed(2)}M`;
  if (tokens >= 1000) return `${Math.round(tokens / 1000)}K`;
  return String(tokens);
}

let taskModelId: string | null = null;
const listeners = new Set<() => void>();

export function taskModel(): string | null {
  return taskModelId;
}

export function setTaskModel(id: string | null): void {
  taskModelId = id;
  for (const listener of listeners) listener();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useTaskModel(): string | null {
  return useSyncExternalStore(subscribe, taskModel, () => null);
}
