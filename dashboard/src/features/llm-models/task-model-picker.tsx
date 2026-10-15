"use client";

import { useEffect, useState } from "react";
import {
  TIER_LABEL,
  defaultModel,
  listModels,
  listOwnModels,
  ownModelId,
  price,
  setTaskModel,
  useTaskModel,
  type LlmModel,
  type LlmTier,
  type OwnModels,
} from "./models";

const TIERS: LlmTier[] = ["featured", "well_known", "other"];

export function TaskModelPicker() {
  const bridge = typeof window !== "undefined" ? window.meeluAgent : undefined;
  const chosen = useTaskModel();
  const [models, setModels] = useState<LlmModel[] | null>(null);
  const [own, setOwn] = useState<OwnModels | null>(null);
  const [fallback, setFallback] = useState("");

  useEffect(() => {
    if (!bridge) return;
    let live = true;
    void Promise.all([listModels(), defaultModel(), listOwnModels().catch(() => null)])
      .then(([list, chosenDefault, ownList]) => {
        if (!live) return;
        setModels(list);
        setOwn(ownList);
        setFallback(ownList ? ownModelId(ownList.defaultModel) : chosenDefault);
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [bridge]);

  useEffect(() => {
    if (!chosen || !models) return;
    const listed =
      models.some((m) => m.id === chosen) || own?.models.some((m) => ownModelId(m.id) === chosen);
    if (!listed) setTaskModel(null);
  }, [chosen, models, own]);

  if (!models) return null;
  const nameOf = (id: string) =>
    models.find((m) => m.id === id)?.name ??
    own?.models.find((m) => ownModelId(m.id) === id)?.name ??
    id;

  return (
    <select
      value={chosen ?? ""}
      onChange={(e) => setTaskModel(e.target.value || null)}
      aria-label="Model for new tasks"
      title="The model a task uses is fixed when the task starts."
      className="max-w-[11rem] shrink-0 cursor-pointer truncate rounded-full border border-edge2 bg-transparent px-2.5 py-1.5 text-xs text-sub transition-colors hover:border-accent focus:border-accent focus:outline-none"
    >
      <option value="">Default · {nameOf(fallback)}</option>
      {own && own.models.length > 0 && (
        <optgroup label="Your Anthropic key">
          {own.models.map((m) => (
            <option key={m.id} value={ownModelId(m.id)}>
              {m.name} · your key
            </option>
          ))}
        </optgroup>
      )}
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
