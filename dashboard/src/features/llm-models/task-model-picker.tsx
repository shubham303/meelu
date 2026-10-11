"use client";

import { useEffect, useState } from "react";
import {
  TIER_LABEL,
  defaultModel,
  listModels,
  price,
  setTaskModel,
  useTaskModel,
  type LlmModel,
  type LlmTier,
} from "./models";

const TIERS: LlmTier[] = ["featured", "well_known", "other"];

export function TaskModelPicker() {
  const bridge = typeof window !== "undefined" ? window.meeluAgent : undefined;
  const chosen = useTaskModel();
  const [models, setModels] = useState<LlmModel[] | null>(null);
  const [fallback, setFallback] = useState("");

  useEffect(() => {
    if (!bridge?.getLlmConfig) return;
    let live = true;
    void bridge
      .getLlmConfig()
      .then(async (cfg) => {
        if ("error" in cfg || cfg.provider !== "meelu") return;
        const [list, chosenDefault] = await Promise.all([listModels(), defaultModel()]);
        if (!live) return;
        setModels(list);
        setFallback(chosenDefault);
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [bridge]);

  if (!models) return null;
  const nameOf = (id: string) => models.find((m) => m.id === id)?.name ?? id;

  return (
    <select
      value={chosen ?? ""}
      onChange={(e) => setTaskModel(e.target.value || null)}
      aria-label="Model for new tasks"
      title="The model a task uses is fixed when the task starts."
      className="max-w-[11rem] shrink-0 cursor-pointer truncate rounded-full border border-edge2 bg-transparent px-2.5 py-1.5 text-xs text-sub transition-colors hover:border-accent focus:border-accent focus:outline-none"
    >
      <option value="">Default · {nameOf(fallback)}</option>
      {TIERS.map((tier) => {
        const group = models.filter((m) => m.tier === tier);
        if (!group.length) return null;
        return (
          <optgroup key={tier} label={TIER_LABEL[tier]}>
            {group.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name} · {price(m.inputUsdPerMillion)} in / {price(m.outputUsdPerMillion)} out
              </option>
            ))}
          </optgroup>
        );
      })}
    </select>
  );
}
